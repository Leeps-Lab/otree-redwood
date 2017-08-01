from channels.routing import route, route_class
from otree_redwood.consumers import DebugEventWatcher, EventConsumer

# NOTE: otree_extensions is part of
# otree-core's private API, which may change at any time.
channel_routing = [
    route_class(EventConsumer, path=(
    	r'^/otree/redwood' +
    	'/app-name/(?P<app_name>[^/]+)'
    	'/group/(?P<group>[0-9]+)' +
    	'/participant/(?P<participant_code>[a-zA-Z0-9_-]+)' +
    	'/$')),
    route_class(DebugEventWatcher, path=r'^/otree/redwood/debug/$'),
]