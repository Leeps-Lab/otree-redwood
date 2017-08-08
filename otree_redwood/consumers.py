from channels import Channel, Group
from channels.generic.websockets import WebsocketConsumer
from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models.signals import post_save
import django.dispatch
import importlib
import json
from otree.models.participant import Participant

from otree_redwood.models import Event, Connection
from otree_redwood.stats import track 


connection_signal = django.dispatch.Signal(providing_args=['group', 'participant', 'state'])
events_signals = defaultdict(lambda: django.dispatch.Signal(providing_args=['event']))


def connect(group, channel, receiver):
    group_key = '{}-{}'.format(group.pk, channel)
    if group_key not in events_signals:
        events_signals[group_key].connect(receiver, weak=False)
        return (group_key, receiver)
    return None


def disconnect(watcher):
    if watcher:
        group_key, receiver = watcher
        events_signals[group_key].disconnect(receiver)


def get_cached_group(app_name, group_pk):
    with track('trying to fetch group from cache') as obs:
        group = cache.get(group_pk)
        if not group:
            models_module = importlib.import_module('{}.models'.format(app_name))
            group = models_module.Group.objects.get(pk=group_pk)
            cache.set(group_pk, group)
    return group


def get_cached_participant(participant_code):
    with track('trying to fetch participant from cache') as obs:
        participant = cache.get(participant_code)
        if not participant:
            participant = Participant.objects.get(code=participant_code)
            cache.set(participant_code, participant)
    return participant


class EventConsumer(WebsocketConsumer):
    
    url_pattern = (
        r'^/redwood' +
        '/app-name/(?P<app_name>[^/]+)'
        '/group/(?P<group>[0-9]+)' +
        '/participant/(?P<participant_code>[a-zA-Z0-9_-]+)' +
        '/$')

    def connection_groups(self, **kwargs):
        """
        Called to return the list of groups to automatically add/remove
        this connection to/from.
        """
        return [str(kwargs['group'])]

    def connect(self, message, **kwargs):
        self.message.reply_channel.send({'accept': True})

        group = get_cached_group(kwargs['app_name'], kwargs['group'])
        participant = get_cached_participant(kwargs['participant_code'])
        try:
            last_state = Event.objects.filter(
                    channel='state',
                    content_type=ContentType.objects.get_for_model(group),
                    group_pk=group.pk).order_by('timestamp')[0]
            self.send({
                'channel': 'state',
                'payload': last_state.value
            })
        except IndexError:
            pass
        Connection.objects.get_or_create(participant_code=kwargs['participant_code'])
        group._on_connect(participant)

    def disconnect(self, message, **kwargs):
        group = get_cached_group(kwargs['app_name'], kwargs['group'])
        participant = get_cached_participant(kwargs['participant_code'])
        try:
            # TODO: Clean out stale connections if not terminated cleanly.
            Connection.objects.get(participant_code=participant.code).delete()
        except Connection.DoesNotExist:
            pass
        group._on_disconnect(participant)

    def raw_receive(self, message, **kwargs):
        content = json.loads(message['text'])
        for (key, value) in kwargs.items():
            content[key] = value

        if content['channel'] == 'echo':
            with track('recv_channel=echo'):
                payload = None
                if 'payload' in content:
                    payload = content['payload']
                self.send({
                    'channel': 'echo',
                    'payload': payload
                })
                return

        with track('recv_channel=' + content['channel']):
            group = get_cached_group(kwargs['app_name'], kwargs['group'])
            participant = get_cached_participant(kwargs['participant_code'])
            # TODO: Look into saving events async in another thread.
            with track('saving event object to database'):
                event = Event.objects.create(
                    group=group,
                    participant=participant,
                    channel=content['channel'],
                    value=content['payload'])

            with track('handing event to group'):
                event_handler = getattr(group, '_on_{}_event'.format(content['channel']))
                event_handler(event)

    def send(self, content):
        self.message.reply_channel.send({'text': json.dumps(content)}, immediately=True)


class EventWatcher(WebsocketConsumer):

    url_pattern = r'^/redwood/events/session/(?P<session_code>[a-zA-Z0-9_-]+)/$'

    def connection_groups(self, **kwargs):
        """
        Called to return the list of groups to automatically add/remove
        this connection to/from.
        """
        return ['events-' + kwargs['session_code']]

    def connect(self, message, **kwargs):
        self.message.reply_channel.send({'accept': True})


@django.dispatch.receiver(post_save, sender=Event)
def on_event_save(sender, instance, **kwargs):
    Group('events-' + instance.group.session.code).send({'text': json.dumps(instance.message)})
