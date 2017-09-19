README
======

.. code-block:: bash

 > sphinx-apidoc -f -e --ext-autodoc -o source/ ../ ../setup.py
 > make html
 > sphinx-autobuild . _build/html
