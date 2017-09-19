.. otree-redwood documentation master file, created by
   sphinx-quickstart on Fri Sep 15 12:05:12 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to otree-redwood's documentation!
=========================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   source/modules
   README

otree-redwood is a library that enables oTree experiments to use websockets.
An oTree page might collect one decision per player in the order of 60 seconds.
With websockets, player decisions can be collected and broadcast to other
players in the group within tens of milliseconds without leaving the current
page.

otree-redwood includes two parts:

1. Server-side Python modules let the experimenter control how player input is
	 collected and broadcast amongst a group.
2. Client-side Javascript modules to integrate websocket events into existing
	 user interfaces.

otree-redwood is being developed on GitHub. The core branch is maintained by
the LEEPS Lab at https://github.com/Leeps-Lab/otree-redwood. The lab is
developing 3 experiments heavily using the library - these can be found at
https://github.com/Leeps-Lab/oTree.

Continuous Bimatrix
===================

Continuous Bimatrix is a re-implementation of the experiment used in "A
Continuous Dilemma", written in oTree using otree-redwood. The experiment
presents participants with a bimatrix game and lets them select a mixed
strategy. Their strategy is combined with that of a counterpart to calculate a
payoff. The continuous time implementation uses websockets to distribute a
players strategy to their counterpart on the order of 100 milliseconds. This
enables players to respond to strategy changes in real time, possibly dozens of
times over the course of a 2-3 minute period.

Stochastic Bimatrix
===================

Stochastic Bimatrix is similar to Continuous Bimatrix, but with a twist. The
bimatrix game being played can switch between 2 matrices over the course of a
2-3 minute period. Switching is controlled with a stochastic variable set by
the oTree server and varies based on the players current strategy. Regarding
otree-redwood, this shows off the ability of the oTree server to respond to
websocket events, as opposed to just simply rebroadcasting them to the group.

Imperfect Monitoring
====================

Imperfect Monitoring is another bimatrix game with a twist. First, participants
can only choose a pure strategy from the 2 alternatives. Second, players are
"locked in" to their strategy choice for a short period of time, on the order
of 5-10 seconds. This shows off more of the ability to send websocket events
and drive complex behavior using some features of the otree-redwood library.

How To Use
==========

Option 1 - Clone the Leeps-Lab oTree repository.
------------------------------------------------

.. code-block:: bash

 > git clone https://github.com/Leeps-Lab/oTree

Cloning the repository is the fastest way to get started. You can copy one of
the 3 existing experiments or even just modify them in-place.

Option 2 - Import otree-redwood into your existing oTree repository.
--------------------------------------------------------------------

1. Install the otree-redwood library using pip.

.. code-block:: bash

 > pip install otree-redwood

2. Add otree-redwood as a dependency in your requirements_base.txt file. pip
will tell you ther version that was installed.

.. code-block:: bash

 > otree-redwood=<Fill in version from pip here>

3. Use the otree-redwood classes in your experiment's models.py file.

Instead of extending BaseGroup, your Group class extends one of the
otree-redwood Groups - either ContinuousDecisionGroup or DiscreteDecisionGroup.
Your Group class needs a period_length function.  This is similar to oTree's
timeout_seconds variable. When the period timer expires players will be
automatically moved to the next page.

You still extend BasePlayer, but your Player class needs an initial_decision
function. This is the decision the player starts with. You can let the player
choose their initial decision with a normal oTree page before the page using
the DecisionGroup and websockets.

.. code-block:: python

 from otree_redwood.models import Event, ContinuousDecisionGroup

 class Group(ContinuousDecisionGroup):

   def period_length(self):
     return Constants.period_length

 class Player(BasePlayer):

   def initial_decision(self):
     return 0.5

4. Use the otree-redwood web components in one of your experiments HTML templates.

.. code-block:: html+django

 {% block scripts %}
   <script>
     // Boilerplate that lets you access useful oTree template variables from Javascript.
     var oTree = oTree || {};
     (function() {
       oTree.group = parseInt("{{ player.group.pk }}");
       oTree.group = isNaN(oTree.group) ? null : oTree.group;
       oTree.role = "{{ player.role }}";
       oTree.participantCode = "{{ player.participant.code }}";
       oTree.appName = "{{ subsession.app_name }}";
       oTree.idInGroup = "{{ player.id_in_group }}";
       oTree.csrfToken = "{{ csrf_token }}";
       {% if view.is_debug %}
       oTree.debug = true;
       {% else %}
       oTree.debug = false;
       {% endif %}
     })();
   				
     // Get the decision component and other-decision element.
     var decision = document.querySelector("otree-continuous-decision");
     var otherDecision = document.getElementById("other-decision");
   
     // When group decisions changes, update the text of the otherDecision element.
     decision.addEventListener('group-decisions-changed', function(event) {
       otherDecision.innerText = decision.otherDecision;
     });
   
     // Attach this to a button onclick event to set your decision when the button is clicked.
     function setDecision(d) {
       decision.myDecision = d;
     }
   </script>
   
   // Import the otree-continuous-decision and otree-period webcomponents.
   <link
     rel="import"
     href="/static/otree-redwood/webcomponents/otree-continuous-decision/otree-continuous-decision.html">
   <link
     rel="import"
     href="/static/otree-redwood/webcomponents/otree-period/otree-period.html">
   {% endblock %}
   
   {% block content %}
     <!-- Include the components on the page -->
     <otree-period></otree-period>
     <otree-continuous-decision></otree-continuous-decision>
   
     <p>Other Decision: <span id="other-decision"></span></p>
   
     <button onclick="setDecision(0)">Decision=0</button>
     <button onclick="setDecision(1)">Decision=1</button>
   
     <!-- The rest of your oTree template goes here -->
   {% endblock %}

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
