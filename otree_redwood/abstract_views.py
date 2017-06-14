from channels import Group
from django.db.models.signals import post_save
from django.http.response import HttpResponseRedirect
from django.utils import timezone
from datetime import timedelta
import json
import logging
from otree.api import Page as oTreePage
from otree.views.abstract import global_lock
import threading
import time

from otree_redwood import consumers
from otree_redwood.models import Event, Connection, RanPlayersReadyFunction


class Page(oTreePage):
    """Page is designed to be used instead of an oTree Page to provide
    Redwood-specific functions for coordinating inter-page communication for
    subjects in the Page.
    """

    def dispatch(self, request, *args, **kwargs):
        # Dispatch to super first so that variables are available.
        result = super().dispatch(request, *args, **kwargs)
        self._page_index = kwargs['page_index']
        consumers.connection_signal.connect(self._check_if_all_players_ready)
        return result

    def before_next_page(self):
        consumers.connection_signal.disconnect(self._check_if_all_players_ready)

    def when_all_players_ready(self):
        """Implement this to perform an action for the group once
        all players are ready.
        """
        pass

    def _check_if_all_players_ready(self, **kwargs):
        with global_lock():
            try:
                ready = RanPlayersReadyFunction.objects.get(
                    page_index=self._page_index,
                    id_in_subsession=self.group.id_in_subsession,
                    session=self.session
                )
            except RanPlayersReadyFunction.DoesNotExist:
                ready = RanPlayersReadyFunction.objects.create(
                    page_index=self._page_index,
                    id_in_subsession=self.group.id_in_subsession,
                    session=self.session
                )
            for player in self.group.get_players():
                try:
                    Connection.objects.get(participant_code=player.participant.code)
                except Connection.DoesNotExist:
                    return
                    
            self.when_all_players_ready()
            ready.ran = True
            ready.save()
            event = Event.objects.create(
                session=self.session,
                subsession=self.subsession.name(),
                round=self.round_number,
                group=self.group.id_in_subsession,
                channel='period_start',
                value=time.time())
            consumers.connection_signal.disconnect(self._check_if_all_players_ready)


class ContinuousDecisionPage(Page):
    period_length = 360

    def __init__(self, *args, **kwargs):
        self.__class__.timeout_seconds = self.period_length + 10
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
                session=self.session,
                subsession= self.subsession.name(),
                round=self.round_number,
                group=self.group.id_in_subsession,
                channel='decisions',
                participant=player.participant
            )
            if len(decisions) > 0:
                self.group_decisions[player.participant.code] = decisions[0].value
            else:
                self.group_decisions[player.participant.code] = self.initial_decision

        self._watcher = consumers.watch(self.group, 'decisions', self.handle_decision_event)

        return result

    def when_all_players_ready(self):
        # calculate start and end times for the period
        start_time = timezone.now()
        end_time = start_time + timedelta(seconds=self.period_length)

        self._log_decision_bookends(start_time, end_time)

    def handle_decision_event(self, event):
        # TODO: Probably want to ignore decisions that come in before the period_start signal is sent.
        if event.value != None:
            self.group_decisions[event.participant.code] = event.value
            consumers.send(self.group, 'group_decisions', self.group_decisions)

    def before_next_page(self):
        pass
        # TODO: Unwatch so that the dictionary doesn't leak
        # consumers.unwatch(self._watcher)

    def _log_decision_bookends(self, start_time, end_time):
        """Insert dummy decisions into the database.
        
        This should be done once per group.
        This bookends the start and end of the period.
        """
        for player in self.group.get_players():
            start_decision, end_decision = Event(), Event()
            for d in start_decision, end_decision:
                d.session = self.session
                d.subsession = self.subsession.name()
                d.round = self.round_number
                d.group = self.group.id_in_subsession
                d.channel = 'decisions'
                d.participant = player.participant

            start_decision.timestamp = start_time
            start_decision.value = self.initial_decision
            end_decision.timestamp = end_time
            end_decision.value = None

            start_decision.save()
            end_decision.save()


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

    def tick(self):
        pass

    def start(self):
        if self.timer:
            self.timer.start()

    def stop(self):
        del _timers[self.group]
