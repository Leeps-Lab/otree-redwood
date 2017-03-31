from otree_redwood.firebase.events import SubperiodEmitter
from otree_redwood.models import Decision


class WaitPageMixin(object):
    """WaitPageMixin is designed to be mixed in to an otree WaitPage to provide
    Redwood-specific functions for coordinating inter-page communication for
    subjects in the next Page. The WaitPage should be immediately followed by
    the target Page to synchronize on.
    """

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