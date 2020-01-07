import math
from otree.common import _group_randomly
from django.db import models

class SubsessionSilosMixin(models.Model):
    """SubsessionSilosMixin adds the ability to group players into silos.
    
    Silos are groups of groups that allow you to organize your session into smaller sessions. When
    using silos, Players will only ever be matched with other players in their silo.
    To use, include SubsessionSilosMixin as a superclass for the Subsession class and GroupSilosMixin
    as a superclass for the Group class in your experiment's models.py. Then call `group_randomly_in_silos` in 
    `Subsession.before_session_starts` and pass it the desired number of silos:

    .. code-block:: python
    
        class Subsession(BaseSubsession, SubsessionSilosMixin):

            def before_session_starts:
                self.group_randomly_in_silos(2)
        
        class Group(BaseGroup, GroupSilosMixin):
            pass
    
    Each group's silo number is saved in `Group.silo_num` and can be accessed later for output purposes.
    """

    class Meta:
        abstract = True

    def group_randomly_in_silos(self, num_silos, fixed_id_in_group=False):

        groups = self.get_group_matrix()
        if num_silos > len(groups):
            raise ValueError('number of silos cannot be greater than number of groups')

        groups_per_silo = math.ceil(len(groups) / num_silos)
        silos = [groups[x:x+groups_per_silo] for x in range(0, num_silos * groups_per_silo, groups_per_silo)]
        randomized_groups = []
        for silo in silos:
            randomized_groups += _group_randomly(silo, fixed_id_in_group)
        self.set_group_matrix(randomized_groups)

        for i, group_arr in enumerate(randomized_groups):
            silo_num = i // groups_per_silo
            group_obj = group_arr[0].group
            group_obj.silo_num = silo_num
            group_obj.save(update_fields=['silo_num'])

class GroupSilosMixin(models.Model):

    class Meta:
        abstract = True

    silo_num = models.IntegerField(null=True)

