import math
from otree import matching

class SubsessionSilosMixin():
    """SubsessionSilosMixin adds the ability to group players into silos.
    
    Silos are groups of groups that allow you to organize your session into smaller sessions. When
    using silos, Players will only ever be matched with other players in their silo.
    To use, include it as a superclass for the Subsession class in your experiment's models.py then
    call `group_randomly_in_silos` in `Subsession.before_session_starts` and pass it the desired number
    of groups in each silo:

    .. code-block:: python
    
        class Subsession(BaseSubsession, SubsessionSilosMixin):

            def before_session_starts:
                self.group_randomly_in_silos(2)
    
    If the total number of groups is not a multiple of `groups_per_silo`, then one of the generated
    silos will have fewer than `groups_per_silo` groups in it.

    Each group's silo number is saved in `Group.silo_num` and can be accessed later for output purposes.
    """

    def group_randomly_in_silos(self, groups_per_silo, fixed_id_in_group=False):
        groups = self.get_group_matrix()
        num_silos = math.ceil(len(groups) / groups_per_silo)
        silos = [groups[x:x+groups_per_silo] for x in range(0, num_silos * groups_per_silo, groups_per_silo)]
        randomized_groups = []
        for silo in silos:
            randomized_groups += matching.randomly(silo, fixed_id_in_group)
        self.set_group_matrix(randomized_groups)

        for i, group_arr in enumerate(randomized_groups):
            silo_num = i // groups_per_silo
            group_obj = group_arr[0].group
            group_obj.silo_num = silo_num
            group_obj.save(update_fields=['silo_num'])