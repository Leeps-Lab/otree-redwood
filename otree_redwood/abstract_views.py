from channels import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.http.response import HttpResponseRedirect
from django.utils import timezone
from datetime import timedelta
import json
import logging
import otree.common_internal
from otree.api import Page as oTreePage
from otree.views.abstract import global_lock
import redis_lock
import threading
import time

from otree_redwood import consumers
from otree_redwood.models import Event, Connection, RanPlayersReadyFunction


logger = logging.getLogger('otree_redwood')


class Page(oTreePage):
    """Page is designed to be used instead of an oTree Page to provide
    Redwood-specific functions for coordinating inter-page communication for
    subjects in the Page.
    """

    def dispatch(self, request, *args, **kwargs):
        # Dispatch to super first so that variables are available.
        result = super().dispatch(request, *args, **kwargs)
        self._page_index = kwargs['page_index']
        consumers.connection_signal.connect(self._on_connection_change)
        return result

    def before_next_page(self):
        consumers.connection_signal.disconnect(self._on_connection_change)

    def period_length(self):
        """Implement this to set a timeout on the page. A message will be sent on
        the period_start when all players in the group have connected their websockets.
        Another message will be send on the period_end channel period_length seconds from
        the period_start message.
        """
        return None

    def when_all_players_ready(self):
        """Implement this to perform an action for the group once
        all players are ready.
        """
        pass

    def when_player_disconnects(self):
        """Implement this to perform an action when a player disconnects."""
        pass

    def _on_connection_change(self, group=None, participant=None, state=None, **kwargs):
        if group.pk != self.group.pk:
            return

        logger.debug('_on_connection_change: state={}, participant={}, group={}'.format(state, participant.code, group.pk))

        if state == 'disconnected' and participant.code == self.player.participant.code:
            self.when_player_disconnects()
            return

        if otree.common_internal.USE_REDIS:
            lock = redis_lock.Lock(
                otree.common_internal.get_redis_conn(),
                '{}-{}-{}'.format(self.session.pk, self._page_index, self.group.id_in_subsession),
                expire=60,
                auto_renewal=True)
        else:
            lock = global_lock()

        with lock:
            try:
                ready = RanPlayersReadyFunction.objects.get(
                    page_index=self._page_index,
                    content_type=ContentType.objects.get_for_model(self.group),
                    group_pk=self.group.pk)
            except RanPlayersReadyFunction.DoesNotExist:
                ready = RanPlayersReadyFunction.objects.create(
                    page_index=self._page_index,
                    group=self.group)

            if ready.ran:
                logger.debug('_on_connection_change: already ran ready function')
                return
            for player in self.group.get_players():
                if Connection.objects.filter(participant_code=player.participant.code).count() == 0:
                    logger.debug('_on_connection_change: not all players are connected, cannot run ready function yet')
                    return
                    
            logger.debug('_on_connection_change: all players connected, running ready function')
            self.when_all_players_ready()
            ready.ran = True
            ready.save()

            consumers.send(self.group, 'state', 'period_start')

            if self.period_length():
                self._timer = threading.Timer(
                    self.period_length(),
                    lambda: consumers.send(self.group, 'state', 'period_end'))
                self._timer.start()


class ContinuousDecisionPage(Page):

    def __init__(self, *args, **kwargs):
        #self.__class__.timeout_seconds = self.period_length() + 10
        super().__init__(*args, **kwargs)
        self._watcher = None

    def dispatch(self, request, *args, **kwargs):
        # Dispatch to super first so that variables are available.
        result = super().dispatch(request, *args, **kwargs)
        # All pages get visited twice - the second time to force a redirect.
        # in which case no attributes get set and the participant is moving
        # on to the next page.
        if isinstance(result, HttpResponseRedirect):
            return result

        self.group_decisions = {}
        for player in self.group.get_players():
            decisions = Event.objects.filter(
                group_pk=self.group.pk,
                channel='decisions',
                participant=player.participant)
            if len(decisions) > 0:
                self.group_decisions[player.participant.code] = decisions[0].value
            else:
                self.group_decisions[player.participant.code] = self.initial_decision()

        self._watcher = consumers.connect(self.group, 'decisions', self._on_decision_event)

        return result

    def when_all_players_ready(self):
        start_time = timezone.now()
        for player in self.group.get_players():
            d = Event()
            d.group = self.group
            d.channel = 'decisions'
            d.participant = player.participant

            d.timestamp = start_time
            d.value = self.initial_decision()
            self.group_decisions[d.participant.code] = d.value

            d.save()
        consumers.send(self.group, 'group_decisions', self.group_decisions)

    def initial_decision(self):
        """Implement this to give the players an initial decision.
        """
        return None

    def _on_decision_event(self, event=None, **kwargs):
        self.group_decisions[event.participant.code] = event.value
        consumers.send(self.group, 'group_decisions', self.group_decisions)

    def before_next_page(self):
        consumers.disconnect(self._watcher)


output_functions = []
def output_table(app=None):
    def _output_table(f):
        output_functions.append((f, app))
        return f
    return _output_table


_timers = {}
class DiscreteEventEmitter():

    def __init__(self, interval, period_length, group, callback):
        self.interval = float(interval)
        self.period_length = period_length
        self.group = group
        self.intervals = self.period_length / self.interval
        self.callback = callback
        self.current_interval = 0
        if self.group not in _timers:
            self.timer = threading.Timer(self.interval, self._tick)
            _timers[self.group] = self.timer
        else:
            self.timer = None

    def _tick(self):
        start = time.time()
        self.callback(self.current_interval, self.intervals, self.group)
        self.current_interval += 1
        if self.current_interval < self.intervals:
            self.timer = threading.Timer(self.interval, self._tick)
            _timers[self.group] = self.timer
            self.timer.start()

    def start(self):
        if self.timer:
            self.timer.start()

    def stop(self):
        del _timers[self.group]
