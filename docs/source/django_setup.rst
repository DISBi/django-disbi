=================
Setting up Django
=================

If you are new to Django, it is recommended to take the
`tutorial <https://docs.djangoproject.com/en/1.10/intro/>`_. If you have worked
with Django, but not in conjunction with a virtual environment or PostgreSQL,
you can use the documentation as an opinionated guide. Programmers who have a Django
environment with PostgreSQL already running can skip this part.


Setting up a virtual environment
================================

To encapsulate your project dependencies, it is recommended to use a 
`virtual environment <https://docs.python.org/3/glossary.html#term-virtual-environment>`_.
A convenient way to do this is to use `Conda <http://conda.pydata.org/docs/>`_, but any environment
manager will do. For a lightweight installation in production, you should use the `Miniconda <http://conda.pydata.org/miniconda.html>`_
distribution.
 
Find the installer appropriate for your distribution at http://conda.pydata.org/miniconda.html
and downlaod it, e.g.::

    $ wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh 

Then install from the command line.
If you decide to use conda upadate it first::

    $ conda update conda

Then create a new environment for DISBi::

    $ conda create -n disbienv python






Setting up the database
=======================

A DISBi app requires `PostgreSQL <https://www.postgresql.org/>`_ as 
database backend. This section describes how to install Postgres and 
set up a new user and a new database that will be used to store the data
of your DISBi app. Note that it is not necessary, but only convenient to
create the new user as a superuser.

Install compiler::

    $ sudo apt-get install gcc

Install Postgres server and client::

    $ sudo apt-get install postgresql postgresql-client libpq-dev

Login as postgres user::

    $ sudo -u postgres psql postgres

From the Postgres shell create a new superuser::

    CREATE ROLE <disbi_admin> SUPERUSER LOGIN;

And set a password::

    ALTER USER <disbi_admin> WITH PASSWORD '<passwd>';

Exit the Postgres shell and create a database for DISBi::

    $ sudo -u postgres createdb <disbidb>
