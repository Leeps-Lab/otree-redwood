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
from abc import ABCMeta, abstractmethod
from firebase import firebase
import logging
import threading
import time

from otree_redwood.models import Decision


logger = logging.getLogger(__name__)

_FIREBASE_URL = 'https://otree.firebaseio.com'
_FIREBASE_SECRET = 'uXop5iUjKkGfH20sFmdCMenX7QnUWmnWDde76WQR'


_emitters = {}


class DuplicatePathError(ValueError):

    def __init__(self, path, *args):
        self.message = 'Already emitting events on {}'.format(path)
        super(DuplicatePathError, self).__init__(self.message, *args)


class PeriodicEventEmitter(metaclass=ABCMeta):
    """PeriodicEventEmitter runs an abstract method to send out periodic events.

    Every interval seconds for some duration, PeriodicEventEmitter calls
    the emit_event method.

    emit_event should return a JSON-compatible dictionary that will be logged
    to the oTree SQL database and sent out to clients over Firebase.
    """

    def __init__(self, session, subsession, roundno, group,
                 component, duration, interval):
        self.path = (
            '/session/%s' +
            '/app/%s' +
            '/subsession/%s' +
            '/round/%s' +
            '/group/%s' +
            '/%s') % (
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
        self.duration = duration
        self.interval = interval
        self.total_periods = duration / interval
        self.period_number = 0
        self.firebase = firebase.FirebaseApplication(_FIREBASE_URL)
        self.timer = threading.Timer(
            self.interval, self._emit_event)

    def start(self):
        self.timer.start()

    def _emit_event(self):

        self.period_number += 1

        event = self.emit_event()
        self.firebase.post(self.path, event)

        if self.period_number < self.total_periods:
            self.timer = threading.Timer(
                self.interval, self._emit_event)
            self.timer.start()
        else:
            del(_emitters[self.path])

    @abstractmethod
    def emit_event(self):
        pass


class SubperiodEmitter(PeriodicEventEmitter):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

    def emit_event(self):
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
        return {
            'decisions': decisions
        }


