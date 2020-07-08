from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save
import django.dispatch
import importlib
import json
from otree.models.participant import Participant

from otree_redwood.models import Event, Connection
from otree_redwood import stats


def get_group(app_name, group_pk):
    with stats.track('fetch group') as obs:
        models_module = importlib.import_module('{}.models'.format(app_name))
        return models_module.Group.objects.get(pk=group_pk)

class EventConsumer(JsonWebsocketConsumer):
    
    url_pattern = (
        r'^redwood' +
        '/app-name/(?P<app_name>[^/]+)'
        '/group/(?P<group>[0-9]+)' +
        '/participant/(?P<participant_code>[a-zA-Z0-9_-]+)' +
        '/$')

    def connect(self):
        self.accept()
        self.url_params = self.scope['url_route']['kwargs']

        group = get_group(self.url_params['app_name'], self.url_params['group'])
        async_to_sync(self.channel_layer.group_add)(
            str(group.pk),
            self.channel_name
        )

        participant = Participant.objects.get(code=self.url_params['participant_code'])
        try:
            last_state = group.events.filter(channel='state').latest('timestamp')
            self.send_json({
                'channel': 'state',
                'payload': last_state.value
            })
        except Event.DoesNotExist:
            pass
        Connection.objects.get_or_create(participant=participant)
        group._on_connect(participant)

    def disconnect(self, close_code):
        group = get_group(self.url_params['app_name'], self.url_params['group'])
        async_to_sync(self.channel_layer.group_discard)(
            str(group.pk),
            self.channel_name
        )

        participant = Participant.objects.get(code=self.url_params['participant_code'])
        try:
            # TODO: Clean out stale connections if not terminated cleanly.
            Connection.objects.get(participant=participant).delete()
        except Connection.DoesNotExist:
            pass
        group._on_disconnect(participant)

    def receive_json(self, content):
        if content['channel'] == 'ping':
            with stats.track('recv_channel=ping'):
                if content['avg_ping_time']:
                    stats.update('avg_ping_time', content['avg_ping_time'])
                self.send_json({
                    'channel': 'ping',
                    'timestamp': content['timestamp'],
                })
                return

        with stats.track('recv_channel=' + content['channel']):
            group = get_group(self.url_params['app_name'], self.url_params['group'])
            participant = Participant.objects.get(code=self.url_params['participant_code'])
            with stats.track('saving event object to database'):
                event = group.events.create(
                    participant=participant,
                    channel=content['channel'],
                    value=content['payload'])

            with stats.track('handing event to group'):
                try:
                    event_handler = getattr(group, '_on_{}_event'.format(content['channel']))
                except AttributeError:
                    pass
                else:
                    event_handler(event)
    
    def redwood_send_to_group(self, event):
        msg = event['text']
        self.send_json(msg)


class EventWatcher(JsonWebsocketConsumer):

    url_pattern = r'^redwood/events/session/(?P<session_code>[a-zA-Z0-9_-]+)/$'

    def connect(self):
        self.session_code = self.scope['url_route']['kwargs']['session_code']
        self.events_group_name = 'redwood_events-{}'.format(self.session_code)
        async_to_sync(self.channel_layer.group_add)(
            self.events_group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.events_group_name,
            self.channel_name
        )

    def redwood_send_to_watcher(self, event):
        msg = event['text']
        self.send_json(msg)


@django.dispatch.receiver(post_save, sender=Event)
def on_event_save(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'redwood_events-{}'.format(instance.group.session.code),
        {
            'type': 'redwood.send_to_watcher',
            'text': json.dumps(instance.message)
        }
    )
