from channels.routing import route, route_class
from otree_redwood.consumers import consume_event, EventConsumer

# NOTE: otree_extensions is part of
# otree-core's private API, which may change at any time.
channel_routing = [
    route_class(EventConsumer, path=(
    	r'^/otree/redwood' +
    	'/session/(?P<session_code>[a-zA-Z0-9_-]+)' +
    	'/subsession/(?P<subsession_number>[0-9]+)' +
    	'/round/(?P<round_number>[0-9]+)' +
    	'/group/(?P<group_number>[0-9]+)' +
    	'/participant/(?P<participant_code>[a-zA-Z0-9_-]+)' +
    	'/$')),
    route('otree.redwood.events', consume_event),
]