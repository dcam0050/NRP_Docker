PYXB Usage
==========

PyXB (“pixbee”) is a pure Python package that generates Python source code for classes that
correspond to data structures defined by XMLSchema. More information on
http://pyxb.sourceforge.net/index.html

Install pyxb
------------

You can install pyxb with python pip.

.. code-block:: bash

    $ sudo apt-get install python-pip
    $ sudo pip install pyxb


Generate a parser
-----------------

The following command will read a specema document and generate a parser.
Attention: the xml schema has to be specified with its file ending, the python module without.

.. code-block:: bash

    $ pyxbgen -u <XML Schema document>.xsd -m <name of generated python module>
