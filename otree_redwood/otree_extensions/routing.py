from django.conf.urls import url
from otree_redwood.consumers import EventWatcher, EventConsumer

# NOTE: otree_extensions is part of
# otree-core's private API, which may change at any time.
websocket_routes = [
    url(EventConsumer.url_pattern, EventConsumer),
    url(EventWatcher.url_pattern, EventWatcher),
]