from channels import Group
from channels.generic.websockets import WebsocketConsumer
from django.contrib.contenttypes.models import ContentType
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

        group = get_group(kwargs['app_name'], kwargs['group'])
        participant = Participant.objects.get(code=kwargs['participant_code'])
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
        Connection.objects.get_or_create(participant=participant)
        group._on_connect(participant)

    def disconnect(self, message, **kwargs):
        group = get_group(kwargs['app_name'], kwargs['group'])
        participant = Participant.objects.get(code=kwargs['participant_code'])
        try:
            # TODO: Clean out stale connections if not terminated cleanly.
            Connection.objects.get(participant=participant).delete()
        except Connection.DoesNotExist:
            pass
        group._on_disconnect(participant)

    def raw_receive(self, message, **kwargs):
        content = json.loads(message['text'])
        for (key, value) in kwargs.items():
            content[key] = value

        if content['channel'] == 'ping':
            with stats.track('recv_channel=ping'):
                if content['avg_ping_time']:
                    stats.update('avg_ping_time', content['avg_ping_time'])
                self.send({
                    'channel': 'ping',
                    'timestamp': content['timestamp'],
                })
                return

        with stats.track('recv_channel=' + content['channel']):
            group = get_group(kwargs['app_name'], kwargs['group'])
            participant = Participant.objects.get(code=kwargs['participant_code'])
            with stats.track('saving event object to database'):
                event = Event.objects.create(
                    group=group,
                    participant=participant,
                    channel=content['channel'],
                    value=content['payload'])

            with stats.track('handing event to group'):
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
