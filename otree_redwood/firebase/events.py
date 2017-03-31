"""
Sends subpage events to Firebase.

Want to start an emitter when the first subject connects to a page.
Then let the experiment configure events that get emitted until the
timeout runs out (timeout_seconds in the Page view object).

Problems:
Subjects will start pages at different times - we want 1 emitter per
set of subjects on the same page.
Subjects might be on different pages - need 1 emitter per page type.
"""
from firebase import firebase
import logging
import threading
import time

from otree.models import Decision


logger = logging.getLogger(__name__)

_FIREBASE_URL = 'https://otree.firebaseio.com'
_FIREBASE_SECRET = 'uXop5iUjKkGfH20sFmdCMenX7QnUWmnWDde76WQR'


_emitters = {}


class DuplicatePathError(ValueError):

    def __init__(self, path, *args):
        self.message = 'Already emitting events on {}'.format(path)
        super(DuplicatePathError, self).__init__(self.message, *args)


class SubperiodEmitter(object):

    def __init__(self, session, subsession, roundno, group,
                 period_length, num_subperiods):
        self.path = (
            '/session/%s' +
            '/app/%s' +
            '/subsession/%s' +
            '/round/%s' +
            '/group/%s' +
            '/subperiods') % (
            session.code,
            subsession.app_name,
            subsession.id,
            roundno,
            group.id_in_subsession)
        if self.path in _emitters:
            raise DuplicatePathError(path)
        _emitters[self.path] = self
        self.session = session
        self.subsession = subsession
        self.roundno = roundno
        self.group = group
        self.period_length = period_length
        self.num_subperiods = num_subperiods
        self.subperiod_length = period_length / num_subperiods
        self.current_subperiod = 0
        self.firebase = firebase.FirebaseApplication(_FIREBASE_URL)
        self.timer = threading.Timer(
            self.subperiod_length, self.emit_subperiod_event)

    def start(self):
        self.timer.start()

    def emit_subperiod_event(self):
        if self.current_subperiod + 1 < self.num_subperiods:
            self.timer = threading.Timer(
                self.subperiod_length, self.emit_subperiod_event)
            self.timer.start()
        # TODO: Filter by component?
        group_decisions = Decision.objects.filter(
            session=self.session,
            subsession=self.subsession.id,
            round=self.roundno,
            group=self.group.id_in_subsession).exclude(value=None)
        decisions = {}
        for player in self.group.get_players():
            last_decision = group_decisions.filter(
                participant=player.participant)[0]
            decisions[player.participant.code] = last_decision.value
        event = {
            'decisions': decisions
        }
        self.firebase.post(self.path, event)
        self.current_subperiod += 1
        if self.current_subperiod >= self.num_subperiods:
            del(_emitters[self.path])
