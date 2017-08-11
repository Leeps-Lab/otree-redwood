from channels import Group as ChannelGroup
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import models
import json
from jsonfield import JSONField
import otree.common_internal
from otree.models import BaseGroup
from otree.views.abstract import global_lock
from otree_redwood.stats import track 
import redis_lock
import threading
import time


class Event(models.Model):

    class Meta:
        # Default to queries returning most recent Event first.
        ordering = ['timestamp']

    timestamp = models.DateTimeField(null=False)
    content_type = models.ForeignKey(ContentType, related_name='content_type_events')
    group_pk = models.PositiveIntegerField()
    group = GenericForeignKey('content_type', 'group_pk')
    channel = models.CharField(max_length=100, null=False)
    participant = models.ForeignKey(
        'otree.Participant',
        related_name='+',
        null=True)
    value = JSONField()

    @property
    def message(self):
        return {
            'timestamp': time.mktime(self.timestamp.timetuple())*1e3 + self.timestamp.microsecond/1e3,
            'group': self.group_pk,
            'participant': None if not self.participant else self.participant.code,
            'channel': self.channel,
            'value': self.value
        }

    def save(self, *args, **kwargs):
        if self.timestamp is None:
            self.timestamp = timezone.now()

        super().save(*args, **kwargs)


class Connection(models.Model):
    participant = models.ForeignKey(
        'otree.Participant',
        related_name='+',
        null=True)


class Group(BaseGroup):
    """Group is designed to be used instead of the oTree BaseGroup to provide
    Redwood-specific functions for coordinating inter-page communication for
    players in the Group.
    """
    class Meta:
        abstract = True

    ran_ready_function = models.DateTimeField(null=True)

    def period_length(self):
        """Implement this to set a timeout on the page. A message will be sent on
        the period_start when all players in the group have connected their websockets.
        Another message will be send on the period_end channel period_length seconds from
        the period_start message.
        """
        return None

    def when_all_players_ready(self):
        """Implement this to perform an action for the group once
        all players are ready.
        """

    def when_player_disconnects(self):
        """Implement this to perform an action when a player disconnects."""

    def _on_connect(self, participant):
        if otree.common_internal.USE_REDIS:
            lock = redis_lock.Lock(
                otree.common_internal.get_redis_conn(),
                '{}-{}'.format(self.session.pk, self.pk),
                expire=60,
                auto_renewal=True)
        else:
            lock = global_lock()

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
        self.when_player_disconnects()

    def send(self, channel, payload):
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


class ContinuousDecisionGroup(Group):

    class Meta:
        abstract = True

    group_decisions = JSONField(null=True)

    def when_all_players_ready(self):
        self.group_decisions = {}
        start_time = timezone.now()
        for player in self.get_players():
            d = Event()
            d.group = self
            d.channel = 'decisions'
            d.participant = player.participant

            d.timestamp = start_time
            d.value = self.initial_decision()
            self.group_decisions[d.participant.code] = d.value

            d.save()
        self.save()
        self.send('group_decisions', self.group_decisions)

    def initial_decision(self):
        """Implement this to give the players an initial decision."""
        return None

    def _on_decisions_event(self, event=None, **kwargs):
        if not self.group_decisions:
            return
        with track('_on_decisions_event'):
            self.group_decisions[event.participant.code] = event.value
            self.save()
            self.send('group_decisions', self.group_decisions)
