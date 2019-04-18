.. _GettingStarted:

Getting Started
===============

Gotchas
----------------------------

otree-redwood currently only works with python3 and Google Chrome. We have long term plans to add support for other browsers, but for now only google chrome will work correctly.

If you see an error that looks like `error: Python.h: No such file or directory`, you need to install the Python development libraries. These should be included on OS X. On Linux, you can install them with your package manager, for example:

.. code-block:: bash

 sudo apt-get install python3-dev

If your Redwood experiment generates a large number of messages, you may get warnings from oTree about sqlite running out of connections.
The solution to this problem is to use a fully featured database such as Postgres. Instructions for integrating Postgres with
oTree can be found in the `oTree docs <https://otree.readthedocs.io/en/latest/server/intro.html>`_.

Option 1 - Clone the Leeps-Lab oTree repository.
------------------------------------------------

.. code-block:: bash

 git clone https://github.com/Leeps-Lab/oTree
 cd oTree
 git submodule update --recursive --remote
 python3 -m venv venv
 source venv/bin/activate
 pip install -r requirements.txt
 otree resetdb
 otree runserver

Cloning the repository is the fastest way to get started. You can copy one of
the 3 existing experiments or modify them in-place.

Option 2 - Install otree-redwood from scratch
--------------------------------------------------------------------

1. Create and activate a python virtual environment to manage otree's python dependencies:

.. code-block:: bash

 python3 -m venv venv
 source venv/bin/activate

Virtual environments allow you to isolate your project's dependencies from your main python installation. Read more about virtual environments `here <https://docs.python.org/3/library/venv.html>`_.

2. Use pip to install the otree-redwood library and the LEEPS fork of otree-core:

.. code-block:: bash

 pip install otree-redwood git+https://github.com/leeps-lab/otree-core

3. Start a new oTree project:

.. code-block:: bash

 otree startproject oTree
 cd oTree

4. Save current versions of all dependencies in a requirements file so they can be quickly installed later:

.. code-block:: bash

  pip freeze > requirements_base.txt

Install dependencies later with

.. code-block:: bash

  pip install -r requirements_base.txt

5. Update INSTALLED_APPS and EXTENSION_APPS in your settings.py

.. code-block:: python

 ...
 INSTALLED_APPS = ['otree', 'django_extensions']
 EXTENSION_APPS = ['otree_redwood']
 ...

6. Create a new oTree experiment:

.. code-block:: bash
 
 otree startapp my_experiment

7. Use the otree-redwood classes in your experiment's models.py file:

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

8. Use the otree-redwood web components in one of your experiments HTML templates.

Make sure your template inherits from "otree_redwood/Page.html" instead of the usual
"global/Page.html". This is required for the otree-constants webcomponent to work correctly.

An example minimal otree_redwood template:

.. code-block:: html+django

 {% extends "otree_redwood/Page.html" %}

 {% block scripts %}
   <!-- Import the redwood-decision and redwood-period webcomponents. -->
   <link
     rel="import"
     href="/static/otree-redwood/webcomponents/redwood-decision/redwood-decision.html">
   <link
     rel="import"
     href="/static/otree-redwood/webcomponents/redwood-period/redwood-period.html">
   
   <script>
     // Get the decision component and other-decision element.
     var decision = document.querySelector("redwood-decision");
     var otherDecision = document.getElementById("other-decision");

     // Log period start/end to the JavaScript console.
     document.querySelector("redwood-period").addEventListener('period-start', function(event) {
       console.log('period started');
     });
     document.querySelector("redwood-period").addEventListener('period-end', function(event) {
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
 {% endblock %}
   
 {% block content %}
   <!-- Include the components on the page -->
   <redwood-period></redwood-period>
   <redwood-decision></redwood-decision>
   
   <p>Other Decision: <span id="other-decision"></span></p>
   
   <button type="button" onclick="setDecision(0)">Decision=0</button>
   <button type="button" onclick="setDecision(1)">Decision=1</button>
 {% endblock %}
