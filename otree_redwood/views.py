from collections import defaultdict
import csv
import datetime
from importlib import import_module
import vanilla

import channels
from django.http import HttpResponse, JsonResponse
from django.contrib.contenttypes.models import ContentType

from otree.models import Session
from otree.session import SESSION_CONFIGS_DICT
from otree_redwood import stats
from otree_redwood.models import Event, Connection


def AppSpecificExportCSV(app_name, display_name, get_output_table):

    class ExportCSV(vanilla.View):

        url_name = 'redwood_export_{}'.format(app_name)
        url_pattern = '^{}/$'.format(url_name)
        app_name = app_name
        display_name = display_name

        def get(request, *args, **kwargs):

            models_module = import_module('{}.models'.format(app_name))
            groups = models_module.Group.objects.all()

            tables = []
            for group in groups:
                events = Event.objects.filter(
                    content_type=ContentType.objects.get_for_model(group),
                    group_pk=group.pk)
                tables.append(get_output_table(list(events)))

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(
                '{} Events (accessed {}).csv'.format(
                    display_name,
                    datetime.date.today().isoformat()
                )
            )

            w = csv.writer(response)
            for i, (header, rows) in enumerate(tables):
                if i == 0:
                    w.writerow(header)
                w.writerows(rows)

            return response

    return ExportCSV


class EventsJsonAPI(vanilla.ListView):

    url_name = 'redwood_events_json_api'
    url_pattern = r'^redwood/api/events/session/(?P<session_code>[a-zA-Z0-9_-]+)/$'
    model = Event

    def render_to_response(self, context):
        session = Session.objects.get(code=self.kwargs['session_code'])
        events_by_app_name_then_group = defaultdict(lambda: {})
        for session_config in SESSION_CONFIGS_DICT.values():
            app_name = session_config['name']
            try:
                groups_query = getattr(session, app_name + '_group')
            except AttributeError:
                continue
            groups = list(groups_query.all())
            if groups:
                for group in groups:
                    events = Event.objects.filter(group_pk=group.pk)
                    events_by_app_name_then_group[app_name][group.pk] = [e.message for e in events]
        return JsonResponse(events_by_app_name_then_group, safe=False)


class DebugView(vanilla.TemplateView):

    url_name = 'redwood_debug'
    url_pattern = r'^redwood/debug/session/(?P<session_code>[a-zA-Z0-9_-]+)/$'
    template_name = 'otree_redwood/Debug.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = stats.items()
        channel_layer = channels.asgi.get_channel_layer()
        if 'statistics' in channel_layer.extensions:
            context['global_channel_stats'] = channel_layer.global_statistics()
        context['connected_participants'] = Connection.objects.all()
        context['session_code'] = self.kwargs['session_code']
        return context

 
app_specific_exports = []
for session_config in SESSION_CONFIGS_DICT.values():
    app_name = session_config['name']
    dotted_path = app_name + '.views'
    display_name = session_config['display_name']
    try:
        module = import_module(dotted_path)
    except ImportError:
        continue
    table_fn = getattr(module, 'get_output_table', None)
    if table_fn:
        app_specific_exports.append(AppSpecificExportCSV(app_name, display_name, table_fn))
