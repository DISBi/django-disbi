============
Contributing
============

DISBi is an open source project released under MIT License. Everybody
is welcome to contribute! There is always a need for better documentation,
cleaner code and new features. To ensure long term code quality and
consistency  here are a few guidelines that you should heed when committing
code to the project. 

Design Goals
============

DISBi aims at presenting a general solution for data integration
in Systems Biology. To do this the software pursues several goals.

* Data model independence
    To be able to adapt to the diverse requirements of different 
    projects, all features should rely only on the :ref:`abstract data model <data-model>`.
    
* Data management
    Data should be easy to manage through the admin interface.
    Moreover, the data should be made accessible through user 
    friendly *filter* interfaces, that do not require knowledge of
    the underlying database structure.

* Data integration
    Data should be made available in an integrated manner that
    facilitates further analysis and discovery of underlying patterns.
    Moreover, one should be able to export the integrated data in
    commonly used formats.
    
* Preliminary analysis
    DISBi tries to support the researcher by automating common
    analysis routines. These should help in identifying data that is 
    worthwhile for more in depth analysis. However, DISBi tries not to replicate the
    full functional scope of mature data analysis tools. 
    Instead, it tries to  give the user the freedom to export 
    data in interchangeable formats and let him
    choose his own analysis tool.

If you have a contribution that surpasses the scope of the Design Goals,
but is useful nevertheless, you should consider designing
your contribution as a pluggable extension. 

Style Guide
===========

Python
------

Try to follow  and :pep:`8`
the `Google Style Guide <https://google.github.io/styleguide/pyguide.html>`_
as closely as possible. Everything should have at least a one-line
docstring. Use `Google Style <http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_
for longer docstrings. 

JavaScript
----------

In general, follow the recommendations of the 
`jQuery style guide <https://contribute.jquery.org/style-guide/js/>`_
and code examples presented in the jQuery documentation.

Sass
----

Follow the recommendations of the 
`Sass styleguide <https://sass-guidelin.es/>`_
by Hugo Giraudel.




`PEP8 <https://www.python.org/dev/peps/pep-0008/>`_






