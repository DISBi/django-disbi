=====================================
Setting up the production environment
=====================================

Once you have successfully set up your DISBi application and verified that
everything works as intended, you will want to make DISBi available to all people 
from your Systems Biology project. To do this, you need to move from the development
to a `production environment <https://docs.djangoproject.com/en/1.11/howto/deployment/>`_.

Going into production with Docker (recommended)
-----------------------------------------------

In the root of the ``django-disbi`` repository you find a ``docker-compose.yml`` that
should serve as a good starting point for a production ready container system. Basically,
you should only have to adapt the ``entry.sh`` to run your app instead of the demo app.

You will also have to adapt the ``settings.py`` file for production:

.. code-block:: python

    DEBUG = False
    ALLOWED_HOSTS = ['www.myhost.org']

    # Enable whitenoise for serving static files.
    MIDDLEWARE_CLASSES = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # 'django.middleware.security.SecurityMiddleware',
    ...
    ]


Going into production with Apache
---------------------------------
 
This is a guide for using `Apache Server <https://httpd.apache.org/>`_ on Debian/Ubuntu as a production server.  
Any other production environment or server recommended by the Django documentation will
do as well.

Install Apache::

    $ sudo apt-get install apache2 apache2-dev 

Download `mod_wsgi <http://modwsgi.readthedocs.io/en/develop/index.html>`_, 
but look for newer version on https://github.com/GrahamDumpleton/mod_wsgi/releases::

    $ wget https://github.com/GrahamDumpleton/mod_wsgi/archive/4.5.7.tar.gz
    $ tar xvfz 4.5.7.tar.gz 
 
Install from source::
    
    $ ./configure --with-python=</path/to/env/>
    $ make
    $ sudo make install
    
Enable mod_wsgi with Debian script::

    $ sudo a2enmod wsgi  

Set ``WSGIPythonHome``, in ``apache2.conf``.

See http://modwsgi.readthedocs.io/en/develop/user-guides/installation-issues.html
in case of problems.

Set ``WSGIPythonHome``, in ``apache2.conf``,
see also https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/modwsgi/.

Set up a virtual host by using the template from the boilerplate.

Enable vhost and reload the server::

    $ a2ensite disbi.conf
    $ service apache2 reload

If error occurs, probably ``tkinter`` is missing::

    $ sudo apt-get install python3-tk
    
Preparing for production by adapting ``settings.py``:

.. code-block:: python

    DEBUG = False
    ALLOWED_HOSTS = ['myhost']
