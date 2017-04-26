from channels import Channel, Group
from channels.generic.websockets import JsonWebsocketConsumer
import django.dispatch
import json
from otree.models.session import Session
from otree.models.participant import Participant

from otree_redwood.models import Event


def group_key(session_code, subsession_number, round_number, group_number):
    # Get a group key suitable for use with a Django channel Group.
    return 'session-{}-subsession-{}-round-{}-group-{}'.format(
        session_code,
        subsession_number,
        round_number,
        group_number)


# TODO: Track event consumption time by channel and display it on a debug page.
def consume_event(message):
    content = message.content

    # TODO: Cache session objects by code for fast lookup.
    session = Session.objects.get(code=content['session_code'])
    subsession_number = int(content['subsession_number'])
    round_number = int(content['round_number'])
    group_number = int(content['group_number'])
    channel = content['channel']
    # TODO: Cache participant objects by code for fast lookup.
    participant = Participant.objects.get(code=content['participant_code'])

    # TODO: Look into saving events async in another thread.
    event = Event.objects.create(
        session=session,
        subsession=subsession_number,
        round=round_number,
        group=group_number,
        participant=participant,
        channel=channel,
        value=content['payload'])

    channel_key = group_key(
        session.code,
        subsession_number,
        round_number,
        group_number) + '-' + channel
    
    if channel_key in _watchers:
        _watchers[channel_key](event)


connection_signal = django.dispatch.Signal(providing_args=[
    'session',
    'subsession',
    'round',
    'group'
])


connected_participants = set()


class EventConsumer(JsonWebsocketConsumer):

    # Set to True if you want it, else leave it out
    strict_ordering = True

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
        last_on_channel = {}
        for event in history:
            last_on_channel[event.channel] = event.message
        self.send(
            {'text': json.dumps(last_on_channel)})

    def disconnect(self, message, **kwargs):
        connected_participants.remove(kwargs['participant_code'])
        connection_signal.send(self, **kwargs)

    def receive(self, content, **kwargs):
        # Stick the message onto the processing queue
        for (key, value) in kwargs.items():
            content[key] = value
        Channel("otree.redwood.events").send(content)

try:
    _watchers
except:
    _watchers = {}
def watch(group, channel, callback):
    watcher = group_key(
        group.session.code,
        group.subsession.id,
        group.round_number,
        group.id_in_subsession)
    watcher += '-' + channel
    if watcher in _watchers:
        return None
    _watchers[watcher] = callback
    return watcher 

def unwatch(watcher):
    del _watchers[watcher]

def send(group, channel, payload):
    Group(group_key(
        group.session.code,
        group.subsession.id,
        group.round_number,
        group.id_in_subsession)).send(
            {'text': json.dumps({
                'channel': channel,
                'payload': payload
            })})
