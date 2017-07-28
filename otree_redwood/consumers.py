from channels import Channel, Group
from channels.generic.websockets import WebsocketConsumer
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
import django.dispatch
import importlib
import json
import time
from otree.models.participant import Participant

from otree_redwood.models import Event, Connection
from otree_redwood.stats import track 


def consume_event(message):
    content = message.content
    channel = content['channel']

    with track('recv_channel=' + channel):
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
                channel=channel,
                value=content['payload'])

        channel_key = '{}-{}'.format(group.pk, channel)
        
        if channel_key in _watchers:
            with track('calling watcher'):
                _watchers[channel_key](event)


connection_signal = django.dispatch.Signal(providing_args=['group'])


class EventConsumer(WebsocketConsumer):

    def connection_groups(self, **kwargs):
        """
        Called to return the list of groups to automatically add/remove
        this connection to/from.
        """
        return [str(kwargs['group'])]

    def connect(self, message, **kwargs):
        self.message.reply_channel.send({'accept': True})
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
        Channel('otree.redwood.events').send(content)

    def send(self, content):
        self.message.reply_channel.send({'text': json.dumps(content)}, immediately=True)


try:
    _watchers
except:
    _watchers = {}
def watch(group, channel, callback):
    watcher = ''.format('{}-{}', group.pk, channel)
    if watcher in _watchers:
        return None
    _watchers[watcher] = callback
    return watcher 


def unwatch(watcher):
    if watcher in _watchers:
        del _watchers[watcher]


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
