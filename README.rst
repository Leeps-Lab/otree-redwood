.. image:: https://readthedocs.org/projects/otree-redwood/badge/?version=latest
  :target: http://otree-redwood.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

oTree Redwood Extension
=======================

http://otree-redwood.readthedocs.io/en/latest/

Pushing to PyPI
---------------

Increment version number in ``setup.py``.

You need a ~/.pypirc like this:

.. code-block::

 [distutils]
 index-servers =
   pypi

 [pypi]
   username:yourusername
   password:yourpassword

.. code-block:: bash

  > python setup.py sdist
  > twine upload dist/*
