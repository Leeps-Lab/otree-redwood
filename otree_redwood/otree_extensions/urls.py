from django.conf import urls
from django.views.decorators.gzip import gzip_page

from otree_redwood.views import DebugView, EventsJsonAPI


urlpatterns = [
	urls.url(DebugView.url_pattern, DebugView.as_view(), name=DebugView.url_name),
	urls.url(EventsJsonAPI.url_pattern, gzip_page(EventsJsonAPI.as_view()), name=EventsJsonAPI.url_name),
]