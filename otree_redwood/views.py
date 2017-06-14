import csv
import datetime
import functools
import math
import operator
import vanilla

from django.http import HttpResponse
from django.core import serializers

from otree_redwood import consumers, stats
from otree_redwood.models import Event


class ExportEvents(vanilla.View):

    url_name = 'otree_redwood_export_events'
    url_pattern = '^{}/$'.format(url_name)
    display_name = 'oTree-Redwood extension raw events file.'

    def get(request, *args, **kwargs):

        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            'Events (accessed {}).json'.format(
                datetime.date.today().isoformat()
            )
        )

        events = Event.objects.all()

        response.write(serializers.serialize('json', events).encode('utf-8'))

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
        context['connected_participants'] = consumers.get_connected_participants()
        return context
