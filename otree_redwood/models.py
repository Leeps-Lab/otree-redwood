from channels import Group as ChannelGroup
from contextlib import contextmanager
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import models
import json
from jsonfield import JSONField
import logging
import otree.common_internal
from otree import matching
from otree.models import BaseGroup
from otree.views.abstract import get_redis_lock
from otree_redwood.stats import track 
from otree_redwood.utils import DiscreteEventEmitter
import redis_lock
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
    content_type = models.ForeignKey(ContentType, related_name='content_type_events')
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
        null=True)
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
        null=True)
    """Each Participant should have only one connection."""


class Group(BaseGroup):
    """Group is designed to be used instead of the oTree BaseGroup to provide
    Redwood-specific functions for coordinating inter-page communication for
    players in the Group.
    """
    class Meta:
        abstract = True

    ran_ready_function = models.DateTimeField(null=True)
    """Set when the :meth:`when_all_players_ready` function has been run.
    Ensures run-only-once semantics.
    """

    def period_length(self):
        """Implement this to set a timeout on the page. A message will be sent
        on the period_start when all players in the group have connected their
        websockets. Another message will be send on the period_end channel
        period_length seconds from the period_start message.
        """
        return None

    def when_all_players_ready(self):
        """Implement this to perform an action for the group once all players are ready."""

    def when_player_disconnects(self, player):
        """Implement this to perform an action when a player disconnects."""

    def _on_connect(self, participant):
        """Called from the WebSocket consumer. Checks if all players in the group
        have connected; runs :meth:`when_all_players_ready` once all connections
        are established.
        """
        lock = get_redis_lock()
        if not lock:
            lock = fake_lock()

        with lock:
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
                self._timer = threading.Timer(
                    self.period_length(),
                    lambda: self.send('state', 'period_end'))
                self._timer.start()

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
            ChannelGroup(str(self.pk)).send(
                    {'text': json.dumps({
                        'channel': channel,
                        'payload': payload
                    })})

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


@contextmanager
def fake_lock():
    logger.warning('using fake lock - install redis in production')
    yield
    logger.warning('exiting fake lock - install redis in production')


class DecisionGroup(Group):
    """DecisionGroup receives Events on the ``decisions`` channel, then
    broadcasts them back to all members of the group on the ``group_decisions``
    channel.
    """

    class Meta:
        abstract = True

    group_decisions = JSONField(null=True)
    """:attr:`group_decisions` holds a map from participant code to their current decision."""
    subperiod_group_decisions = JSONField(null=True)
    """:attr:`subperiod_group_decisions` is a copy of the state of
    :attr:`group_decisions` at the end of each subperiod.
    """

    def num_subperiods(self):
        """Override to turn on sub-period behavior. None by default."""
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
            self.save(update_fields=['group_decisions'])
            if not self.num_subperiods():
                self.send('group_decisions', self.group_decisions)
