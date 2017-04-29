from django.conf import urls
from otree_redwood.views import DebugView


urlpatterns = [
	urls.url(DebugView.url_pattern, DebugView.as_view(), name=DebugView.url_name)
]