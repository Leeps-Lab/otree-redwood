from chan import Chan
import codecs
from collections import OrderedDict
import datetime
from django.db.migrations.loader import MigrationLoader
from django.db.utils import OperationalError
from django.conf import settings
import logging
import os
import otree.common_internal
from otree.constants_internal import AUTO_NAME_BOTS_EXPORT_FOLDER
import otree.export
import otree.session
from otree.bots.bot import ParticipantBot
from otree.views.abstract import global_lock
import pytest
import sys
import threading
import time
from unittest import mock

logger = logging.getLogger(__name__)


class SubmitThread(threading.Thread):

    def __init__(self, bot, results):
        super().__init__()
        self.bot = bot
        self.results = results

    def run(self):
        try:
            submission = next(self.bot.submits_generator)
            self.results.put((self.bot, submission))
        except StopIteration:
            self.results.put((self.bot, 'finished'))
        except Exception as ex:
            self.results.put((self.bot, ex))


class SessionBotRunner(object):

    def __init__(self, bots):
        self.bots = OrderedDict()

        for bot in bots:
            self.bots[bot.participant.id] = bot

    def play(self):
        '''round-robin'''
        self.open_start_urls()
        loops_without_progress = 0
        while True:
            import time
            start = time.time()
            if len(self.bots) == 0:
                return
            # bots got stuck if there's 2 wait pages in a row
            if loops_without_progress > 10:
                raise AssertionError('Bots got stuck')
            results = Chan(buflen=len(self.bots))
            threads = []
            for bot in self.bots.values():
                if bot.on_wait_page():
                    pass
                else:
                    thread = SubmitThread(bot, results)
                    threads.append(thread)
                    thread.start()

            for thread in threads:
                bot, status = results.get()
                if isinstance(status, Exception):
                    raise status
                elif status == 'finished':
                    del self.bots[bot.participant.id]
                else:
                    bot.submit(status)
            results.close()

            if not threads:
                loops_without_progress += 1

    def open_start_urls(self):
        for bot in self.bots.values():
            bot.open_start_url()


def session_bot_runner_factory(session):
    bots = []
    for participant in session.get_participants():
        bot = ParticipantBot(participant)
        bots.append(bot)

    return SessionBotRunner(bots)


@pytest.mark.django_db(transaction=True)
def test_bots_async(session_config_name, num_participants, run_export):
    config_name = session_config_name
    session_config = otree.session.SESSION_CONFIGS_DICT[config_name]

    # num_bots is deprecated, because the old default of 12 or 6 was too
    # much, and it doesn't make sense to
    if num_participants is None:
        num_participants = session_config['num_demo_participants']

    num_bot_cases = session_config.get_num_bot_cases()
    for case_number in range(num_bot_cases):
        if num_bot_cases > 1:
            logger.info("Creating '{}' session (test case {})".format(
                config_name, case_number))
        else:
            logger.info("Creating '{}' session".format(config_name))

        session = otree.session.create_session(
            session_config_name=config_name,
            num_participants=num_participants,
            use_cli_bots=True,
            bot_case_number=case_number)

        bot_runner = session_bot_runner_factory(session)
        bot_runner.play()
        logger.info('Bots completed session')
    if run_export:
        # bug: if the user tests multiple session configs,
        # the data will only be exported for the last session config.
        # this is because the DB is cleared after each test case.
        # fix later if this becomes high priority
        export_path = pytest.config.option.export_path

        now = datetime.datetime.now()

        if export_path == AUTO_NAME_BOTS_EXPORT_FOLDER:
            export_path = now.strftime('_bots_%b%d_%Hh%Mm%S.%f')[:-5] + 's'

        if os.path.isdir(export_path):
            msg = "Directory '{}' already exists".format(export_path)
            raise IOError(msg)

        os.makedirs(export_path)

        for app in settings.INSTALLED_OTREE_APPS:
            model_module = otree.common_internal.get_models_module(app)
            if model_module.Player.objects.exists():
                fname = "{}.csv".format(app)
                fpath = os.path.join(export_path, fname)
                with codecs.open(fpath, "w", encoding="utf8") as fp:
                    otree.export.export_app(app, fp, file_extension='csv')

        logger.info('Exported CSV to folder "{}"'.format(export_path))


def run_pytests(**kwargs):

    session_config_name = kwargs['session_config_name']
    num_participants = kwargs['num_participants']
    verbosity = kwargs['verbosity']

    this_module = sys.modules[__name__]

    # '-s' is to see print output
    # --tb=short is to show short tracebacks. I think this is
    # more expected and less verbose.
    # With the default pytest long tracebacks,
    # often the code that gets printed is in otree-core, which is not relevant.
    # also, this is better than using --tb=native, which loses line breaks
    # when a unicode char is contained in the output, and also doesn't get
    # color coded with colorama, the way short tracebacks do.
    argv = [
        this_module.__file__,
        '-s',
        '--tb', 'short'
    ]
    if verbosity == 0:
        argv.append('--quiet')
    if verbosity == 2:
        argv.append('--verbose')

    if session_config_name:
        argv.extend(['--session_config_name', session_config_name])
    if num_participants:
        argv.extend(['--num_participants', num_participants])
    if kwargs['preserve_data']:
        argv.append('--preserve_data')
    if kwargs['export_path']:
        argv.extend(['--export_path', kwargs['export_path']])

    # same hack as in resetdb code
    # because this method uses the serializer
    # it breaks if the app has migrations but they aren't up to date
    with mock.patch.object(
            MigrationLoader,
            'migrations_module',
            return_value='migrations nonexistent hack'):
        return pytest.main(argv)
