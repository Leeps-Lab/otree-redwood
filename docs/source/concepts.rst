.. _concepts:

Concepts
========

Group
-----

:ref:`Groups` are the main unit of organization in otree-redwood. You extend one of
the group classes with your group behavior.

All the otree-redwood Groups extend ``otree.api.BaseGroup``, which is the
class you usually extend. So all your groups will just be oTree groups, with
a few extra methods to deal with events coming from the Players.

WebSocket
---------

otree-redwood has JavaScript libraries to automatically connect a `WebSocket <https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API>`_
to the oTree server. The WebSocket lets you send messages to and from the
oTree server without reloading the page. Generally, WebSocket messages should
take 10-200 milliseconds to go between the page and the server. This puts
an upper bound of around 10 messages per second per player.

Event
-----

otree-redwood turns WebSocket messages into Events. An Event contains some
metadata about who and when the message was sent. The Event also contains
the message payload (value).

Channel
-------

All Events come in across a channel. A channel is just a string that tags the
event so you can organize different types of events. For example, the
ContinuousDecisionGroup uses 3 channels - ``state``, ``decisions``, and
``group_decisions``.

WebComponent
------------

otree-redwood JavaScript libraries are packages as `WebComponents <https://www.webcomponents.org/introduction>`_.
WebComponents contain HTML, JavaScript, and CSS in a single importable package.
This makes it easy to drop otree-redwood into the pages of your existing oTree
experiments.