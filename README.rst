.. image:: https://readthedocs.org/projects/otree-redwood/badge/?version=latest
  :target: http://otree-redwood.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

oTree Redwood Extension
=======================

http://otree-redwood.readthedocs.io/en/latest/

Pushing to PyPI
---------------

Increment version number in ``otree_redwood/__init__.py``.

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

Building the Docs
-----------------

.. code-block:: bash

 // From docs/
 // Build API docs, autodetected from docstrings.
 // Ignore setup.py because it will try to call os.exit.
 > sphinx-apidoc -f -e --ext-autodoc -o source/ ../ ../setup.py
 // Build the docs, check for warnings.
 > make html
 // Run server for live editing.
 > sphinx-autobuild . _build/html
