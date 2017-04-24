from django.utils import timezone
from django.db.models import Manager
from otree.db import models


class Event(models.Model):

    class Meta:
        app_label = "otree"
        # Default to queries returning most recent Event first.
        ordering = ['-timestamp']

    timestamp = models.DateTimeField(null=False)
    session = models.ForeignKey(
        'otree.Session',
        null=False,
        related_name='+')
    subsession = models.IntegerField(null=True)
    round = models.IntegerField(null=False)
    group = models.IntegerField(null=False)
    channel = models.CharField(max_length=100, null=False)
    participant = models.ForeignKey(
        'otree.Participant',
        related_name='+')
    value = models._JSONField()

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
        app_label = "otree"
        unique_together = ['page_index', 'session', 'id_in_subsession']
        index_together = ['page_index', 'session', 'id_in_subsession']

    page_index = models.PositiveIntegerField()
    session = models.ForeignKey('otree.Session')
    id_in_subsession = models.PositiveIntegerField(default=0)
    ran = models.BooleanField(default=False)