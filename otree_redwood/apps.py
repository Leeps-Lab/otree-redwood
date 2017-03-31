from django.apps import AppConfig
from otree_redwood.firebase import watch


class Config(AppConfig):
    name = 'otree_redwood'
    verbose_name = 'oTree Redwood Extension'

    def ready(self):
    	watch.start()