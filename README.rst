oTree Redwood Extension
=================

The oTree Redwood extension enables inter-page communication in an oTree
experiment.

Installation
------------

(Requires otree-core >= 1.2)

.. code-block::

    pip3 install -U otree-core
    pip3 install -U otree-redwood

In ``settings.py``, add ``'otree-redwood'`` to ``INSTALLED_APPS``,
e.g. ``INSTALLED_APPS = ['otree', 'otree-redwood']``

Then run ``otree resetdb``.

For installation on your server, your ``requirements_base.txt`` should
contain ``otree-redwood`` as well as ``otree-core>=1.2.0`` (or higher, etc).

Usage
-----

Basic usage
~~~~~~~~~~~

Add ``{% load otree_redwood %}`` to the top of your template, e.g.:

.. code-block:: html+django

    {% load staticfiles otree_tags %}
    {% load otree_redwood %}

Exporting CSV logs
--------------------------

Upgrading
---------

    pip install -U otreechat

TODO
----
Awesome debugging - watch events live in otree-redwood-debug, filter events
by group, participant, channel, and values. Save and replay events into the
otree-events component.