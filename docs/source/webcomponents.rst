
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

`otree-constants <https://github.com/Leeps-Lab/otree-redwood/tree/master/otree_redwood/static/otree-redwood/webcomponents/redwood-channel/redwood-channel.html>`_
-----------------------------

It's useful to have an easy way to access oTree template variables in JavaScript
without double-curly brackets everywhere (e.g. "{{ }}"). Also, using JavaScript
variables makes it possible to test your JavaScript in a more isolated way than
running a full experiment.

otree-constants requires you to include a small bit of code to set useful
variables from the oTree template. You can access these either from JavaScript
by using the "oTree" object, or with the otree-constants tag itself.

otree-constants is used by most of the other webcomponents, so this block is
required in any template using the otree-redwood components:

.. code-block:: html+django

  {% block scripts %}
    <script>
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
    </script>
  {% endblock %}

.. _redwood-events:

`redwood-events <https://github.com/Leeps-Lab/otree-redwood/tree/master/otree_redwood/static/otree-redwood/webcomponents/redwood-events/redwood-events.html>`_
------------

redwood-events is the lowest-level component. It maintains a single WebSocket
connection to the oTree server, reconnecting if possible. The socket is a
singleton - if you put multiple redwood-events on a single page there will still
only be one socket opened.

redwood-events has some facilities for displaying connection status and ping if
the oTree.debug variable is set in the oTree constants.

.. _redwood-channel:

`redwood-channel <https://github.com/Leeps-Lab/otree-redwood/tree/master/otree_redwood/static/otree-redwood/webcomponents/redwood-channel/redwood-channel.html>`_
-------------

redwood-channel lets you send and receive events on a given channel. This works
in conjunction with the groups from otree-redwood.

For example, let's say we want to let subjects send and receive orders on the
"orders" channel:

In your models.py:

.. code-block:: python

  from otree_redwood.models import Group as RedwoodGroup

  class Group(RedwoodGroup):

    def _on_orders_event(self, event=None, **kwargs):
      # probably should verify the event.participant has enough balance/units
      # to send the order

      # broadcast the order out to all subjects
      self.send("orders", event.value)

In your page template:



.. code-block:: html

  <!-- see above to import the redwood-channel tag and include the oTree constants -->

  <redwood-channel
    id="ordersChannel"
    channel="orders">
  </redwood-channel>

  <button on-click="sendOrder">Send Order</button>

.. code-block:: javascript

  // some fake order we're going to send when the button is clicked
  var fakeOrder = {
    'type': 'bid',
    'price': 5,
    'quantity': 2
  }

  var ordersChan = document.getElementbyId('ordersChannel');

  // send the order out
  function sendOrder() {
    ordersChan.send(fakeOrder);
  }

  // receive orders from the server
  ordersChan.addEventListener('event', function(event) {
    console.log(event.detail.channel); // "orders"
    console.log(event.detail.timestamp);
    console.log(event.detail.payload); // fakeOrder, above
  });

.. _redwood-decision:

`redwood-decision <https://github.com/Leeps-Lab/otree-redwood/tree/master/otree_redwood/static/otree-redwood/webcomponents/redwood-decision/redwood-decision.html>`_
--------------

redwood-decision makes it easy to handle a single decision variable that each
player can set. The decision variable can be a number, boolean, string, or even
an Object. At any given point in time each player only has one value for their
decision forming a set of decisions for the group.

.. _redwood-decision-bot:

`redwood-decision-bot <https://github.com/Leeps-Lab/otree-redwood/tree/master/otree_redwood/static/otree-redwood/webcomponents/redwood-decision-bot/redwood-decision-bot.html>`_
------------------

redwood-decision-bot is useful for testing - it randomly sets the player's
decision in redwood-decision to a numeric value.

.. _redwood-period:

`redwood-period <https://github.com/Leeps-Lab/otree-redwood/tree/master/otree_redwood/static/otree-redwood/webcomponents/redwood-period/redwood-period.html>`_
------------

redwood-period listens for period-start and period-end events on the "state"
channel. When the period-end event is seen, it automatically moves players on
to the next oTree page.

.. _redwood-debug:

`redwood-debug <https://github.com/Leeps-Lab/otree-redwood/tree/master/otree_redwood/static/otree-redwood/webcomponents/redwood-debug/redwood-debug.html>`_
-------------------

redwood-debug is a utility for testing - it can fetch Events from previous
sessions from the oTree server and replay these events back to the redwood-events
component.