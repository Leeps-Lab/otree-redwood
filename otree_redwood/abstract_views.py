from channels import Group
from django.db.models.signals import post_save
from django.utils import timezone
from datetime import timedelta
import json
import logging
from otree.api import Page as oTreePage
from otree.views.abstract import global_lock

from otree_redwood import consumers
from otree_redwood.models import Event, RanPlayersReadyFunction


class Page(oTreePage):
    """Page is designed to be used instead of an oTree Page to provide
    Redwood-specific functions for coordinating inter-page communication for
    subjects in the Page.
    """

    def dispatch(self, *args, **kwargs):
        # Dispatch to super first so that variables are available.
        result = super().dispatch(*args, **kwargs)
        consumers.connection_signal.connect(self._check_if_all_players_ready)
        return result

    def before_next_page():
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
                    page_index=self._index_in_pages,
                    id_in_subsession=self.group.id_in_subsession,
                    session=self.session
                )
            except RanPlayersReadyFunction.DoesNotExist:
                ready = RanPlayersReadyFunction.objects.create(
                    page_index=self._index_in_pages,
                    id_in_subsession=self.group.id_in_subsession,
                    session=self.session
                )
            group_participants = set([player.participant.code for player in self.group.get_players()])
            if group_participants.issubset(consumers.connected_participants) and not ready.ran:
                self.when_all_players_ready()
                ready.ran = True
                ready.save()
                consumers.connection_signal.disconnect(self._check_if_all_players_ready)


class ContinuousDecisionPage(Page):

    def __init__(self, *args, **kwargs):
        self.__class__.timeout_seconds = self.period_length + 10
        super().__init__(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        # Dispatch to super first so that variables are available.
        result = super().dispatch(*args, **kwargs)
        self.group_decisions = {}
        for player in self.group.get_players():
            decisions = Event.objects.filter(
                session=self.session,
                subsession = self.subsession.name(),
                round = self.round_number,
                group = self.group.id_in_subsession,
                channel = 'decisions',
                participant = player.participant
            )
            if len(decisions) > 0:
                self.group_decisions[player.participant.code] = decisions[0].value
            else:
                self.group_decisions[player.participant.code] = 0.5

        self._watcher = consumers.watch(self.group, 'decisions', self._handle_decision_event)

        return result

    def when_all_players_ready(self):
        # calculate start and end times for the period
        start_time = timezone.now()
        end_time = start_time + timedelta(seconds=self.period_length)

        self._log_decision_bookends(start_time, end_time, 0.5)

    def _handle_decision_event(self, event):
        if event.value != None:
            self.group_decisions[event.participant.code] = event.value
            consumers.send(self.group, 'group_decisions', self.group_decisions)

    def before_next_page():
        consumers.unwatch(self._watcher)

    def _log_decision_bookends(self, start_time, end_time, initial_decision):
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
            start_decision.value = initial_decision
            end_decision.timestamp = end_time
            end_decision.value = None

            start_decision.save()
            end_decision.save()