import csv
import datetime
import functools
from importlib import import_module
import math
import operator
import vanilla

from django.http import HttpResponse
from django.core import serializers

from otree.models import Session
from otree.session import SESSION_CONFIGS_DICT
from otree_redwood import consumers, stats
from otree_redwood.models import Event, Connection
from otree_redwood.abstract_views import output_functions

class ExportEvents(vanilla.View):

    url_name = 'otree_redwood_export_events'
    url_pattern = '^{}/$'.format(url_name)
    display_name = 'All oTree-Redwood extension events'

    def get(request, *args, **kwargs):

        apps = []
        for f, app in output_functions:
            sessions = []
            for session in Session.objects.all():
                if app in session.config['app_sequence']:
                    sessions.append(session)
            for session in sessions:
                apps.append({
                    'session': session.code,
                    'app': app,
                    'table': f(Event.objects.filter(session=session)),
                })

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            'Redwood Events (accessed {}).csv'.format(
                datetime.date.today().isoformat()
            )
        )

        w = csv.writer(response)
        for app in apps:
            w.writerow(['app', 'session'])
            w.writerow([app['app'], app['session']])
            header = set()
            for row in app['table']:
                header.add(row.keys())
            for row in app['table']:
                w.writerow([row[col] for col in header])

        return response


def AppSpecificExportCSV(app_name, display_name, get_output_table):

    class ExportCSV(vanilla.View):

        url_name = 'otree_redwood_export_{}'.format(app_name)
        url_pattern = '^{}/$'.format(url_name)
        app_name = app_name
        display_name = display_name

        def get(request, *args, **kwargs):

            sessions = Session.objects.filter(**{'{}_player__isnull'.format(app_name): False}).distinct()
            session_tables = []
            for session in sessions:
                events = Event.objects.filter(session=session)
                session_tables.append(get_output_table(events))

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(
                '{} Events (accessed {}).csv'.format(
                    display_name,
                    datetime.date.today().isoformat()
                )
            )

            w = csv.writer(response)
            for header, rows in session_tables:
                w.writerow(header)
                w.writerows(rows)

            return response

    return ExportCSV


class DebugView(vanilla.TemplateView):

    url_name = 'otree_redwood_export_events'
    url_pattern = r"^redwood-debug/$"
    template_name = 'otree_redwood/Debug.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contexts'] = {}
        for key, values in stats.observations.items():
            mean = sum(values) / len(values)
            context['contexts'][key] = mean
        context['connected_participants'] = Connection.objects.all()
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
