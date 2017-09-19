.. otree-redwood documentation master file, created by
   sphinx-quickstart on Fri Sep 15 12:05:12 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to otree-redwood!
=========================

otree-redwood is a library that enables oTree experiments to use websockets.
An oTree page might collect one decision per player on the order of one minute.
With websockets, player decisions can be collected and broadcast to other
players in the group within tens of milliseconds without leaving the current
page.

otree-redwood includes two parts:

1. Server-side Python modules let the experimenter control how player input is collected and broadcast amongst a group.
2. Client-side Javascript modules to integrate websocket events into existing user interfaces.

otree-redwood is being developed on GitHub. The core branch is maintained by
the LEEPS Lab at https://github.com/Leeps-Lab/otree-redwood.

Development is in progress on 3 experiments using otree-redwood:

* :ref:`ContinuousBimatrix`
* :ref:`StochasticBimatrix`
* :ref:`ImperfectMonitoring`

Contents:
=========

.. toctree::
   :maxdepth: 2

   getting_started.rst
   concepts.rst
   groups.rst
   webcomponents.rst
   examples.rst
   modules.rst

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
