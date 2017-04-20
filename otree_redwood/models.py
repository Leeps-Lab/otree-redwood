from channels import Group
from django.utils import timezone
from django.db.models import Manager
import json
from otree.db import models


def group_key(session_code, subsession_number, round_number, group_number):
    # Get a group key suitable for use with a Django channel Group.
    return 'session-{}-subsession-{}-round-{}-group-{}'.format(
        session_code,
        subsession_number,
        round_number,
        group_number)


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

        create = False
        if not self.pk:
            create = True
        if self.timestamp is None:
            self.timestamp = timezone.now()

        super().save(*args, **kwargs)

        if create:
            Group(group_key(
                self.session.code,
                self.subsession,
                self.round,
                self.group)).send(
                    {'text': json.dumps(self.message)},
                    immediately=True)