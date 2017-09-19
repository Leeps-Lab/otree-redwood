.. _groups:

Groups
======

Base Group
----------

.. code-block:: python

  from otree_redwood.models import Group as RedwoodGroup

  class Group(RedwoodGroup):

send(self, channel, payload)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``send`` broadcasts a ``payload`` on a given ``channel`` to all members
of the group.

period_length(self)
~~~~~~~~~~~~~~~~~~~

The ``period_length`` function must return a number of seconds. This
is analogous to the timeout_seconds_ in an oTree page. The difference is
that periods are synchronized with the players in the group - The period will
not start until all players have connected to the page.

.. _timeout_seconds: http://otree.readthedocs.io/en/latest/timeouts.html#timeouts

when_all_players_ready(self)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``when_all_players_ready`` is called when all players have connected to the page.
The period starts immediately after the function returns. You can override this
function to perform initialization and setup of the group.

when_player_disconnects(self, player)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``when_player_disconnects`` is called when a player disconnects before the period
has ended. Generally this means the player closed their browser window or
turned off their machine. You can override this function to implement behavior
like pausing the period and notifying group members.

ContinuousDecisionGroup
-----------------------

.. code-block:: python

  from otree_redwood.models import ContinuousDecisionGroup

  class Group(ContinuousDecisionGroup):

group_decisions
~~~~~~~~~~~~~~~

``group_decisions`` contains a dictionary mapping a participant code to their
current decision value.

DiscreteDecisionGroup
---------------------

.. code-block:: python

  from otree_redwood.models import DiscreteDecisionGroup

  class Group(DiscreteDecisionGroup):

seconds_per_tick(self)
~~~~~~~~~~~~~~~~~~~~~~

The ``seconds_per_tick`` function must return a number of seconds. The period
will be divided into ``period_length / seconds_per_tick`` sub-periods. Each
sub-period the current ``group_decisions`` gets copied into the
``subperiod_group_decisions``. Effectively this means the players can only make
decisions at the boundary of every sub-period. E.g. if there are 12 sub-periods,
players make 12 decisions during the course of the period.

subperiod_group_decisions
~~~~~~~~~~~~~~~~~~~~~~~~~

``subperiod_group_decisions`` contains a dictionary mapping a participant code
to their decision value in the most recent subperiod.