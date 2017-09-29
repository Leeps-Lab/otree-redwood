
Web Components
=============

https://www.webcomponents.org/introduction

Web components are bundles of HTML, JavaScript, and CSS, encapsulated in a
single spot so you can easily drop them into your page.

otree-redwood has several webcomponents focused around communicated with the
oTree server over a WebSocket.

To use a webcomponent, you first import it in your HTML page. Components are
packaged as HTML files in one of oTree's static folders. You can use the static
tag to reference the component from an oTree template.

Once imported, you can drop the component into your page like any other HTML
tag.

.. code-block:: html+django

  <head>
    <!-- Required for some browsers that don't fully support webcomponents -->
    <script
      src="{% static "bower_components/webcomponentsjs/webcomponents-lite.min.js" %}">
    </script>
    <!-- Import the component -->
    <link
      rel="import"
      href="{% static "webcomponents/redwood-period/redwood-period.html" %}">
  </head>

  <body>
    <!-- Use the component in your page -->
    <redwood-period></redwood-period>
  </body>

.. _otree-constants:

`otree-constants <https://leeps-lab.github.io/otree-redwood/otree_redwood/static/otree-redwood/webcomponents/otree-constants/>`_
-----------------------------

.. _redwood-events:

`redwood-events <https://leeps-lab.github.io/otree-redwood/otree_redwood/static/otree-redwood/webcomponents/redwood-events/>`_
------------

.. _redwood-channel:

`redwood-channel <https://leeps-lab.github.io/otree-redwood/otree_redwood/static/otree-redwood/webcomponents/redwood-channel>`_
-------------

.. _redwood-decision:

`redwood-decision <https://leeps-lab.github.io/otree-redwood/otree_redwood/static/otree-redwood/webcomponents/redwood-decision>`_
--------------

.. _redwood-decision-bot:

`redwood-decision-bot <https://leeps-lab.github.io/otree-redwood/otree_redwood/static/otree-redwood/webcomponents/redwood-decision-bot>`_
------------------

.. _redwood-period:

`redwood-period <https://leeps-lab.github.io/otree-redwood/otree_redwood/static/otree-redwood/webcomponents/redwood-period>`_
------------

.. _redwood-debug:

`redwood-debug <https://leeps-lab.github.io/otree-redwood/otree_redwood/static/otree-redwood/webcomponents/redwood-debug>`_
-------------------