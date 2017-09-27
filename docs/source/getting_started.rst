.. _GettingStarted:

Getting Started
===============

Option 1 - Clone the Leeps-Lab oTree repository.
------------------------------------------------

.. code-block:: bash

 > git clone https://github.com/Leeps-Lab/oTree

Cloning the repository is the fastest way to get started. You can copy one of
the 3 existing experiments or modify them in-place.

Option 2 - Use otree-redwood in your existing oTree repository.
--------------------------------------------------------------------

1. Install the otree-redwood library using pip.

.. code-block:: bash

 > pip install otree-redwood

2. Add otree-redwood as a dependency in ``requirements_base.txt``. pip
will tell you the version that was installed.

.. code-block:: bash

 > otree-redwood=<Fill in version from pip here>

3. Use the otree-redwood classes in your experiment's models.py file.

Instead of extending otree.api.BaseGroup, your Group class extends one of the
otree-redwood Groups - :ref:`BaseGroup` or :ref:`DecisionGroup`.
Your Group class needs a ``period_length`` function.  This is similar to oTree's
``timeout_seconds`` variable. When the period timer expires players will be
automatically moved to the next page.

You still extend otree.api.BasePlayer, but your Player class needs an
``initial_decision`` function. This is the decision the player starts with.
You can let the player choose their initial decision with a normal oTree page.

.. code-block:: python

 from otree_redwood.models import Event, DecisionGroup

 class Group(DecisionGroup):

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
     var decision = document.querySelector("otree-decision");
     var otherDecision = document.getElementById("other-decision");

     // Log period start/end to the JavaScript console.
     document.querySelector("otree-period").addEventListener('period-start', function(event) {
       console.log('period started');
     });
     document.querySelector("otree-period").addEventListener('period-end', function(event) {
       console.log('period ended');
     });
   
     // When group decisions changes, update the text of the otherDecision element.
     decision.addEventListener('group-decisions-changed', function(event) {
       otherDecision.innerText = decision.otherDecision;
     });
   
     // Attach this to a button onclick event to set your decision when the button is clicked.
     function setDecision(d) {
       decision.myDecision = d;
     }
   </script>
   
   // Import the otree-decision and otree-period webcomponents.
   <link
     rel="import"
     href="/static/otree-redwood/webcomponents/otree-decision/otree-decision.html">
   <link
     rel="import"
     href="/static/otree-redwood/webcomponents/otree-period/otree-period.html">
   {% endblock %}
   
   {% block content %}
     <!-- Include the components on the page -->
     <otree-period></otree-period>
     <otree-decision></otree-decision>
   
     <p>Other Decision: <span id="other-decision"></span></p>
   
     <button onclick="setDecision(0)">Decision=0</button>
     <button onclick="setDecision(1)">Decision=1</button>
   
     <!-- The rest of your oTree template goes here -->
   {% endblock %}