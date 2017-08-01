from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import models
from otree.db.serializedfields import JSONField


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
        participant_code = None
        if self.participant:
            participant_code = self.participant.code
        return {
            'participant_code': participant_code,
            'channel': self.channel,
            'payload': self.value
        }

    def save(self, *args, **kwargs):
        if self.timestamp is None:
            self.timestamp = timezone.now()

        super().save(*args, **kwargs)


class RanPlayersReadyFunction(models.Model):
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['page_index', 'group_pk']
        index_together = ['page_index', 'group_pk']

    timestamp = models.DateTimeField(null=False)
    page_index = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, related_name='content_type_ran_players_ready_functions')
    group_pk = models.PositiveIntegerField()
    group = GenericForeignKey('content_type', 'group_pk')
    ran = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.timestamp is None:
            self.timestamp = timezone.now()

        super().save(*args, **kwargs)


class Connection(models.Model):
    participant_code = models.CharField(max_length=10, null=False)