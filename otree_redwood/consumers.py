from channels import Channel
from channels.generic.websockets import JsonWebsocketConsumer
import django.dispatch
import json
from otree.models.session import Session
from otree.models.participant import Participant

from otree_redwood.models import Event, group_key


def consume_event(message):
    content = message.content

    session = Session.objects.get(code=content['session_code'])
    subsession = int(content['subsession_number'])
    round = int(content['round_number'])
    group = int(content['group_number'])
    channel = content['channel']
    participant = Participant.objects.get(code=content['participant_code'])

    Event.objects.create(
        session=session,
        subsession=subsession,
        round=round,
        group=group,
        participant=participant,
        channel=channel,
        value=content['payload'])


connection_signal = django.dispatch.Signal(providing_args=[
    'session',
    'subsession',
    'round',
    'group'
])


connected_participants = set()


class EventConsumer(JsonWebsocketConsumer):

    # Set to True if you want it, else leave it out
    strict_ordering = False

    def connection_groups(self, **kwargs):
        """
        Called to return the list of groups to automatically add/remove
        this connection to/from.
        """
        return [group_key(
            kwargs['session_code'],
            kwargs['subsession_number'],
            kwargs['round_number'],
            kwargs['group_number'])]

    def connect(self, message, **kwargs):
        connected_participants.add(kwargs['participant_code'])
        connection_signal.send(self, **kwargs)
        history = Event.objects.filter(
            session__code=kwargs['session_code'],
            subsession=kwargs['subsession_number'],
            round=kwargs['round_number'],
            group=kwargs['group_number'])
        self.send(
            {'text': json.dumps([event.message for event in history])})

    def disconnect(self, message, **kwargs):
        connected_participants.remove(kwargs['participant_code'])
        connection_signal.send(self, **kwargs)

    def receive(self, content, **kwargs):
        # Stick the message onto the processing queue
        for (key, value) in kwargs.items():
            content[key] = value
        Channel("otree.redwood.events").send(content)
