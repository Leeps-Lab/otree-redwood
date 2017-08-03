from channels.routing import route, route_class
from otree_redwood.consumers import EventWatcher, EventConsumer

# NOTE: otree_extensions is part of
# otree-core's private API, which may change at any time.
channel_routing = [
    route_class(EventConsumer, path=EventConsumer.url_pattern),
    route_class(EventWatcher, path=EventWatcher.url_pattern),
]