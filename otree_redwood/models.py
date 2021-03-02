from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import models
import json
from jsonfield import JSONField
import logging
from otree.models import BaseGroup
from otree_redwood.stats import track 
from otree_redwood.utils import DiscreteEventEmitter
import threading
import time


logger = logging.getLogger(__name__)


class Event(models.Model):
    """Event stores a single message going in or out across a WebSocket connection."""

    class Meta:
        # Default to queries returning most recent Event first.
        ordering = ['timestamp']

    timestamp = models.DateTimeField(null=False)
    """Time the event was received or sent by the server."""
    content_type = models.ForeignKey(ContentType, related_name='content_type_events', on_delete=models.CASCADE)
    """Used to relate this Event to an arbitrary Group."""
    group_pk = models.PositiveIntegerField()
    """Primary key of the Event's related Group."""
    group = GenericForeignKey('content_type', 'group_pk')
    """The Group the event was sent to/from."""
    channel = models.CharField(max_length=100, null=False)
    """Channels act as tags to route Events."""
    participant = models.ForeignKey(
        'otree.Participant',
        related_name='+',
        null=True,
        on_delete=models.CASCADE)
    """The Participant who sent the event - null for server-sent events."""
    value = JSONField()
    """Arbitrary Event payload."""

    @property
    def message(self):
        """Dictionary representation of the Event appropriate for JSON-encoding."""
        return {
            'timestamp': time.mktime(self.timestamp.timetuple())*1e3 + self.timestamp.microsecond/1e3,
            'group': self.group_pk,
            'participant': None if not self.participant else self.participant.code,
            'channel': self.channel,
            'value': self.value
        }

    def save(self, *args, **kwargs):
        """Saving an Event automatically sets the timestamp if not already set."""
        if self.timestamp is None:
            self.timestamp = timezone.now()

        super().save(*args, **kwargs)


class Connection(models.Model):
    """Connections are created and deleted as Participants connect to a WebSocket."""

    participant = models.ForeignKey(
        'otree.Participant',
        related_name='+',
        null=True,
        on_delete=models.CASCADE)
    """Each Participant should have only one connection."""


class Group(BaseGroup):
    """Group is designed to be used instead of the oTree BaseGroup to provide
    Redwood-specific functions for coordinating inter-page communication for
    players in the Group.
    """
    class Meta(BaseGroup.Meta):
        abstract = True

    ran_ready_function = models.DateTimeField(null=True)
    """Set when the :meth:`when_all_players_ready` function has been run.
    Ensures run-only-once semantics.
    """
    events = GenericRelation(Event, content_type_field='content_type', object_id_field='group_pk')
    """Allows Group to query all Event models associated with it.
    This effectively adds an 'events' related name to the Event.group GenericForeignKey.
    """

    def period_length(self):
        """Implement this to set a timeout on the page in seconds. A period_start message will be sent
        on the state channel when all players in the group have connected their
        websockets. A period_end message will be send on the state channel
        period_length seconds from the period_start message.
        """
        return None
    
    def post_round_delay(self):
        """Implement this to change the delay between when the period ends and the page is advanced.
        This delay should be provided in seconds. If :meth:`period_length` is not specified, this method does nothing.
        """
        return 1
    
    def get_start_time(self):
        """Returns a datetime.datetime object representing the time that this period started,
        or None if the period hasn't started yet.
        """
        try:
            return self.events.get(channel='state', value='period_start').timestamp
        except Event.DoesNotExist:
            return None

    def get_end_time(self):
        """Returns a datetime.datetime object representing the time that this period ended.
        Returns None if :meth:`period_length` is not set, or if the period hasn't ended yet.
        """
        try:
            return self.events.get(channel='state', value='period_end').timestamp
        except Event.DoesNotExist:
            return None

    def when_all_players_ready(self):
        """Implement this to perform an action for the group once all players are ready."""
        pass

    def when_player_disconnects(self, player):
        """Implement this to perform an action when a player disconnects."""
        pass

    def _on_connect(self, participant):
        """Called from the WebSocket consumer. Checks if all players in the group
        have connected; runs :meth:`when_all_players_ready` once all connections
        are established.
        """
        self.refresh_from_db()
        if self.ran_ready_function:
            return
        for player in self.get_players():
            if Connection.objects.filter(participant__code=player.participant.code).count() == 0:
                return
                
        self.when_all_players_ready()
        self.ran_ready_function = timezone.now()
        self.save()

        self.send('state', 'period_start')

        if self.period_length():
            # TODO: Should replace this with something like Huey/Celery so it'll survive a server restart.
            timer = threading.Timer(
                self.period_length(),
                lambda: self.send('state', 'period_end'))
            timer.start()

    def _on_disconnect(self, participant):
        """Trigger the :meth:`when_player_disconnects` callback."""
        player = None
        for p in self.get_players():
            if p.participant == participant:
                player = p
                break
        self.when_player_disconnects(player)

    def send(self, channel, payload):
        """Send a message with the given payload on the given channel.
        Messages are broadcast to all players in the group.
        """
        with track('send_channel=' + channel):
            with track('create event'):
                Event.objects.create(
                    group=self,
                    channel=channel,
                    value=payload)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                str(self.pk),
                {
                'type': 'redwood.send_to_group',
                'text': {
                    'channel': channel,
                    'payload': payload,
                    }
                }
            )

    def save(self, *args, **kwargs):
        """
        BUG: Django save-the-change, which all oTree models inherit from,
        doesn't recognize changes to JSONField properties. So saving the model
        won't trigger a database save. This is a hack, but fixes it so any
        JSONFields get updated every save. oTree uses a forked version of
        save-the-change so a good alternative might be to fix that to recognize
        JSONFields (diff them at save time, maybe?).
        """
        super().save(*args, **kwargs)
        if self.pk is not None:
            update_fields = kwargs.get('update_fields')
            json_fields = {}
            for field in self._meta.get_fields():
                if isinstance(field, JSONField) and (update_fields is None or field.attname in update_fields):
                    json_fields[field.attname] = getattr(self, field.attname)
            self.__class__._default_manager.filter(pk=self.pk).update(**json_fields)
    
    @property
    def app_name(self):
        return self.session.config['name']


class DecisionGroup(Group):
    """DecisionGroup receives Events on the ``decisions`` channel, then
    broadcasts them back to all members of the group on the ``group_decisions``
    channel.
    """

    class Meta(Group.Meta):
        abstract = True

    group_decisions = JSONField(null=True)
    """:attr:`group_decisions` holds a map from participant code to their current decision."""
    subperiod_group_decisions = JSONField(null=True)
    """:attr:`subperiod_group_decisions` is a copy of the state of
    :attr:`group_decisions` at the end of each subperiod."""
    _group_decisions_updated = models.BooleanField(default=False)
    """:attr:`_group_decisions_updated` is a private field used with rate limiting to determine
    whether group decisions need to be resent."""

    def get_group_decisions_events(self):
        """Returns a list of all Event objects sent on the ``group_decisions`` channel so far, ordered
        by timestamp. If the period has ended, this gives the complete decision history of this DecisionGroup
        in this period.
        """
        return list(self.events.filter(channel='group_decisions'))

    def num_subperiods(self):
        """Override to turn on sub-period behavior. None by default."""
        return None
    
    def rate_limit(self):
        """Override to turn on rate-limiting behavior. If used, the return value of rate_limit
        determines the minimum time between broadcasted ::attr::`group_decisions` updates."""
        return None

    def when_all_players_ready(self):
        """Initializes decisions based on ``player.initial_decision()``.
        If :attr:`num_subperiods` is set, starts a timed task to run the
        sub-periods.
        """
        self.group_decisions = {}
        self.subperiod_group_decisions = {}
        for player in self.get_players():
            self.group_decisions[player.participant.code] = player.initial_decision()
            self.subperiod_group_decisions[player.participant.code] = player.initial_decision()
        if self.num_subperiods():
            emitter = DiscreteEventEmitter(
                self.period_length() / self.num_subperiods(), 
                self.period_length(),
                self,
                self._subperiod_tick)
            emitter.start()
        elif self.rate_limit():
            def _tick(current_interval, intervals):
                self.refresh_from_db()
                if self._group_decisions_updated:
                    self.send('group_decisions', self.group_decisions)
                    self._group_decisions_updated = False
                    self.save(update_fields=['_group_decisions_updated'])

            update_period = self.rate_limit()
            emitter = DiscreteEventEmitter(
                update_period, 
                self.period_length(),
                self,
                _tick)
            emitter.start()
        self.save()

    def _subperiod_tick(self, current_interval, intervals):
        """Tick each sub-period, copying group_decisions to subperiod_group_decisions.""" 
        self.refresh_from_db()
        for key, value in self.group_decisions.items():
            self.subperiod_group_decisions[key] = value
        self.send('group_decisions', self.subperiod_group_decisions)
        self.save(update_fields=['subperiod_group_decisions'])

    def _on_decisions_event(self, event=None, **kwargs):
        """Called when an Event is received on the decisions channel. Saves
        the value in group_decisions. If num_subperiods is None, immediately
        broadcasts the event back out on the group_decisions channel.
        """
        if not self.ran_ready_function:
            logger.warning('ignoring decision from {} before when_all_players_ready: {}'.format(event.participant.code, event.value))
            return
        with track('_on_decisions_event'):
            self.group_decisions[event.participant.code] = event.value
            self._group_decisions_updated = True
            self.save(update_fields=['group_decisions', '_group_decisions_updated'])
            if not self.num_subperiods() and not self.rate_limit():
                self.send('group_decisions', self.group_decisions)