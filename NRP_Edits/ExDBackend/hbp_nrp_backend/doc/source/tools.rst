Software Tools
==============

This section describes tools that proved useful when developing the backend software.


PyCharm
-------

PyCharm is a python integrated development environment (IDE) that is among the best suited for developing in
 the Python programming language. To set up the IDE, do

1. Follow the steps in :ref:`installation`
2. Set up the virtual environment :ref:`virtualenv`
3. Open the ``ExDBackend`` project and set the interpreter to the virtual environment in ``...``
4. Install plugins that might come in handy
   a. ``ReStructuredText`` for editing documentation of the project
   b. ``VIM`` for emulating the behavior of the popular text editor (author's choice).
   c. ...

.. _tmux:

tmux
----

Enables to run several sessions in the same terminal windows (also in split screen with mouse support).
Link (or copy) the example config file to your home directory to enable mouse support

.. code-block:: bash

     ln -s $EXDB/etc/tmux.conf ~/.tmux.conf

To exit the tmux session press ``<ctrl>-B`` and ``d``.

.. _runbackend:

runbackend / runbackend4
------------------------

.. code-block:: bash

    TODO More detailed description
