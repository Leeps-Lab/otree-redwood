from otree.api import Page as oTreePage
from otree.views.abstract import global_lock

from otree_redwood.firebase.events import SubperiodEmitter
from otree_redwood.firebase.watch import register_path 
from otree_redwood.models import Decision, RedwoodEvent


class Page(oTreePage):
    """Page is designed to be used instead of an oTree Page to provide
    Redwood-specific functions for coordinating inter-page communication for
    subjects in the Page.
    """

    def dispatch(self, *args, **kwargs):
        self._players_ready = set()
        register_path('/session/(?P<session>.*)' +
            '/app/(?P<app>.*)' +
            '/subsession/(?P<subsession>.*)' +
            '/round/(?P<round>.*)' +
            '/group/(?P<group>.*)' +
            '/ready/(?P<participant_code>.*)', self._player_ready)
        return super().dispatch(*args, **kwargs)

    def when_all_players_ready(self):
        """Implement this to perform an action for the group once
        all players are ready.
        """
        pass

    def _player_ready(self, match, data):
        with global_lock():
            self._players_ready.add(match.groupdict()['participant_code'])
            if self._players_ready == set([player.participant.code for player in self.group.get_players()]):
                if RedwoodEvent.objects.filter(
                        component='period_start',
                        session=self.session,
                        subsession=self.subsession.name(),
                        round=self.round_number,
                        group=self.group.id_in_subsession).count() == 0:
                    self.when_all_players_ready()
                    RedwoodEvent(
                        component='period_start',
                        session=self.session,
                        subsession=self.subsession.name(),
                        round=self.round_number,
                        group=self.group.id_in_subsession).save()


    def log_decision_bookends(self, start_time, end_time, app, component, initial_decision):
        """Insert dummy decisions into the database.
        
        This should be done once per group.
        This bookends the start and end of the period.
        """
        for player in self.group.get_players():
            start_decision, end_decision = Decision(), Decision()
            for d in start_decision, end_decision:
                d.app = app
                d.component = component
                d.session = self.session
                d.subsession = self.subsession.name()
                d.round = self.round_number
                d.group = self.group.id_in_subsession
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