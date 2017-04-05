import csv
import datetime
import functools
import operator
import vanilla

from django.http import HttpResponse
from django.core import serializers

from otree_redwood.models import Decision
from otree_redwood.firebase.ticks import collect_ticks


class ExportTicks(vanilla.View):

    url_name = 'otree_redwood_export_ticks'
    url_pattern = '^{}/$'.format(url_name)
    display_name = 'oTree-Redwood extension ticks file.'

    def get(request, *args, **kwargs):

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            'Ticks (accessed {}).csv'.format(
                datetime.date.today().isoformat()
            )
        )

        decisions = Decision.objects.order_by('timestamp').all()
        header, ticks = collect_ticks(decisions)
        w = csv.DictWriter(response, header)
        w.writeheader()
        w.writerows(ticks)

        return response


class ExportRawDecisions(vanilla.View):

    url_name = 'otree_redwood_export_decisions'
    url_pattern = '^{}/$'.format(url_name)
    display_name = 'oTree-Redwood extension raw decisions file.'

    def get(request, *args, **kwargs):

        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            'Decision (accessed {}).json'.format(
                datetime.date.today().isoformat()
            )
        )

        decisions = Decision.objects.order_by('timestamp').all()

        response.write(serializers.serialize('json', decisions).encode('utf-8'))

        return response
