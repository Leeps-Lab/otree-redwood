import logging
from otree.api import Page as oTreePage
from otree.views.abstract import global_lock

from otree_redwood.consumers import connection_signal, connected_participants
from otree_redwood.events import SubperiodEmitter
from otree_redwood.models import Event


class Page(oTreePage):
    """Page is designed to be used instead of an oTree Page to provide
    Redwood-specific functions for coordinating inter-page communication for
    subjects in the Page.
    """

    def dispatch(self, *args, **kwargs):
        # Dispatch to super first so that variables are available.
        result = super().dispatch(*args, **kwargs)
        connection_signal.connect(self._check_if_all_players_ready)

        return result

    def before_next_page():
        connection_signal.disconnect(self._check_if_all_players_ready)

    def when_all_players_ready(self):
        """Implement this to perform an action for the group once
        all players are ready.
        """
        logging.info('all players ready!')
        pass

    def _check_if_all_players_ready(self, **kwargs):
        group_participants = set([player.participant.code for player in self.group.get_players()])
        if connected_participants == group_participants:
            self.when_all_players_ready()
            connection_signal.disconnect(self._check_if_all_players_ready)

    def log_decision_bookends(self, start_time, end_time, initial_decision):
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

    def start_subperiod_emitter(self, period_length, num_subperiods):
        SubperiodEmitter(
            self.session,
            self.subsession,
            self.round_number,
            self.group,
            period_length, num_subperiods).start()

    def start_period_timer(self, period_length):
        pass