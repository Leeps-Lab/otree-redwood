import csv
import datetime
import functools
import math
import operator
import vanilla

from django.http import HttpResponse
from django.core import serializers

from otree.models import Session
from otree_redwood import consumers, stats
from otree_redwood.models import Event, Connection
from otree_redwood.abstract_views import output_functions


class ExportEvents(vanilla.View):

    url_name = 'otree_redwood_export_events'
    url_pattern = '^{}/$'.format(url_name)
    display_name = 'oTree-Redwood extension raw events file.'

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
        context['fields'] = dict(stats.fields)
        context['connected_participants'] = Connection.objects.all()
        return context
