from channels import Channel, Group
from channels.generic.websockets import WebsocketConsumer
from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
import django.dispatch
import importlib
import json
import time
from otree.models.participant import Participant

from otree_redwood.models import Event, Connection
from otree_redwood.stats import track 


connection_signal = django.dispatch.Signal(providing_args=['group'])
events_signals = defaultdict(lambda: django.dispatch.Signal(providing_args=['event']))


def connect(group, channel, receiver):
    group_key = '{}-{}'.format(group.pk, channel)
    events_signals[group_key].connect(receiver)
    return (group_key, receiver)


def disconnect(watcher):
    if watcher:
        group_key, receiver = watcher
        events_signals[group_key].disconnect(receiver)


class EventConsumer(WebsocketConsumer):

    def connection_groups(self, **kwargs):
        """
        Called to return the list of groups to automatically add/remove
        this connection to/from.
        """
        return [str(kwargs['group'])]

    def connect(self, message, **kwargs):
        self.message.reply_channel.send({'accept': True})
        with track('trying to fetch group from cache') as obs:
            group = cache.get(kwargs['group'])
            if not group:
                models_module = importlib.import_module('{}.models'.format(kwargs['app_name']))
                group = models_module.Group.objects.get(pk=kwargs['group'])
                cache.set(kwargs['group'], group)
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
        Connection.objects.create(participant_code=kwargs['participant_code'])
        connection_signal.send(self, **kwargs)

    def disconnect(self, message, **kwargs):
        try:
            # TODO: Clean out stale connections if not terminated cleanly.
            Connection.objects.get(participant_code=kwargs['participant_code']).delete()
        except Connection.DoesNotExist:
            pass
        connection_signal.send(self, **kwargs)

    def raw_receive(self, message, **kwargs):
        content = json.loads(message['text'])
        for (key, value) in kwargs.items():
            content[key] = value

        if content['channel'] == 'echo':
            payload = None
            if 'payload' in content:
                payload = content['payload']
            self.send({
                'channel': 'echo',
                'payload': payload
            })
            return

        with track('recv_channel=' + content['channel']):
            with track('trying to fetch group from cache') as obs:
                group = cache.get(content['group'])
                if not group:
                    models_module = importlib.import_module('{}.models'.format(content['app_name']))
                    group = models_module.Group.objects.get(pk=content['group'])
                    cache.set(content['group'], group)

            with track('trying to fetch participant from cache') as obs:
                participant = cache.get(content['participant_code'])
                if not participant:
                    participant = Participant.objects.get(code=content['participant_code'])
                    cache.set(content['participant_code'], participant)

            # TODO: Look into saving events async in another thread.
            with track('saving event object to database'):
                event = Event.objects.create(
                    group=group,
                    participant=participant,
                    channel=content['channel'],
                    value=content['payload'])

            with track('sending signal'):
                group_key = '{}-{}'.format(group.pk, content['channel'])
                events_signals[group_key].send(self, event=event)

    def send(self, content):
        self.message.reply_channel.send({'text': json.dumps(content)}, immediately=True)


class DebugEventWatcher(WebsocketConsumer):

    def connect(self, message, **kwargs):
        self.message.reply_channel.send({'accept': True})

    def send(self, content):
        self.message.reply_channel.send({'text': json.dumps(content)}, immediately=True)


def send(group, channel, payload):
    with track('send_channel=' + channel):
        Event.objects.create(
            group=group,
            channel=channel,
            value=payload)
        Group(str(group.pk)).send(
                {'text': json.dumps({
                    'channel': channel,
                    'payload': payload
                })})
