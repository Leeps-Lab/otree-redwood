#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import functools
import operator
import pytz
import random

from django.core.management import call_command
from django.db.models import Q

from otree.firebase.ticks import collect_ticks
from otree.models.decision import Decision
from otree.models.session import Session
from otree.session import SESSION_CONFIGS_DICT

from .base import TestCase


class TestCollectTicks(TestCase):

    def test_collect_ticks(self):
        for session in range(2):
            session_name = 'multi_player_game'
            session_conf = SESSION_CONFIGS_DICT[session_name]
            npar = session_conf["num_demo_participants"]
            call_command('create_session', session_name, str(npar))

        start_time = datetime.datetime(
            2017, 2, 22, 10, 0, 0, 0, pytz.timezone('US/Pacific'))
        for i, session in enumerate(Session.objects.all()):

            session_start_time = start_time + datetime.timedelta(hours=i)
            players = session.get_participants()

            round_start_time = session_start_time
            for roundno in range(2):
                round_end_time = (
                    round_start_time +
                    datetime.timedelta(seconds=10))
                # Save bookend decisions.
                for player in players:
                    start_decision, end_decision = Decision(), Decision()
                    for d in start_decision, end_decision:
                        d.component = 'otree-server'
                        d.session = session
                        d.round = roundno
                        d.group = 1
                        d.page = 'test-page'
                        d.app = 'test-app'
                        d.participant = player
                        d.value = 0.5

                    start_decision.timestamp = round_start_time
                    end_decision.timestamp = round_end_time

                    start_decision.save()
                    end_decision.save()

                curr_time = (
                    round_start_time +
                    datetime.timedelta(milliseconds=100))
                while curr_time < round_end_time:
                    d = Decision()
                    d.timestamp = curr_time
                    d.component = 'test-component'
                    d.session = session
                    d.subsession = 0
                    d.round = roundno
                    d.group = 0
                    d.participant = random.choice(players)
                    d.app = 'test-app'
                    d.page = 'test-page'
                    d.value = 0.5
                    d.save()
                    curr_time += datetime.timedelta(
                        milliseconds=random.randint(100, 1000))

                round_start_time = (
                    round_end_time +
                    datetime.timedelta(seconds=10))

        expected_ticks = []
        for session in Session.objects.all():
            for roundno in range(2):
                for tick in range(1, 11):
                    for player in players:
                        expected_ticks.append({
                            'tick': tick,
                            'participant': player.code,
                            'decision': 0.5,
                            'session': session.code,
                            'subsession': 0,
                            'round': roundno,
                            'group': 0
                        })

        session_query = [
            Q(session=session)
            for session in Session.objects.all()]
        decisions = Decision.objects.filter(
            functools.reduce(operator.or_, session_query)).order_by(
                'timestamp').all()

        actual_header, actual_ticks = collect_ticks(decisions)
        self.assertEqual(len(actual_ticks), len(expected_ticks))
