import csv
import datetime
import functools
from importlib import import_module
import json
import math
import operator
import vanilla

from django.http import HttpResponse, JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.core import serializers

from otree.models import Session
from otree.session import SESSION_CONFIGS_DICT
from otree_redwood import consumers, stats
from otree_redwood.models import Event, Connection
from otree_redwood.abstract_views import output_functions


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
            for header, rows in tables:
                w.writerow(header)
                w.writerows(rows)

            return response

    return ExportCSV


class EventsJsonAPI(vanilla.ListView):

    url_name = 'redwood_events'
    url_pattern = r'^redwood/api/events/session/(?P<session_code>[a-zA-Z0-9_-]+)$'
    model = Event

    def render_to_response(self, context):
        # TODO: This is broken because group is a GenericForeignKey
        return JsonResponse([
            e.message for e in Event.objects.filter(group__session__code=self.kwargs['session_code'])
        ], safe=False)


class DebugView(vanilla.TemplateView):

    url_name = 'redwood_debug'
    url_pattern = r'^redwood/debug/session/(?P<session_code>[a-zA-Z0-9_-]+)$'
    template_name = 'otree_redwood/Debug.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contexts'] = {}
        for key, values in stats.observations.items():
            mean = sum(values) / len(values)
            context['contexts'][key] = mean
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
