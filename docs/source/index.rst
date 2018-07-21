.. DISBi documentation master file, created by
   sphinx-quickstart on Mon Sep 19 13:43:44 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

DISBi Integrates Systems Biology
================================

DISBi is a flexible framework for setting up Django apps for managing 
experimental and predicted data from 
Systems Biology projects. A DISBi app presents an integrated online environment,
that helps your team to manage the flood of data and share it 
across the project. DISBi dynamically adapts to its data model at
runtime. Therefore, it offers a solution for the needs of many different
types of projects. DISBi is open source and freely available.



**Features**

* Automatic constructions of a *Filter* interface, that allows you
  to find exactly the experiments you're interested in.
* Integration of related biological objects and the associated experimental
  data in the *Data View*. Data can be further filtered and downloaded in 
  various formats.
* Preliminary analysis directly in the browser. Fold changes can be calculated
  and exported with the rest of the data. Histograms of the distributions of
  data and scatter plots comparing experiments can be generated with
  one button press.
* Flexible abstract data model. Specify a data model that meets the
  requirement of your project. DISBi will figure out the relations between
  the models and necessary steps to integrate the data at runtime.
* Adapt the admin interface to handle large datasets. With the DISBi framework
  the admin can be easily configured to allow uploads and export
  of large datasets using common formats such as CSV or Excel.
  
To get an impression of what DISBi can do for you, see the following 
screenshots:

 .. figure:: _static/images/filter.png

      A screenshot of the *filter view* that helps in choosing the 
      experiments of interest.
      
 .. figure:: _static/images/data.png

      A screenshot of the integrated data in an interactive table 
      in the *Data View*.
      
 .. figure:: _static/images/plot.png

      A screenshot of a histogram and scatter plot, generated form
      transcriptome data.


.. toctree::
   :maxdepth: 2
   :caption: Programmer's Guide

   django_setup
   disbi_setup
   production
   contributing
   
.. toctree::
   :maxdepth: 2
   :caption: User's Guide
   
   user_guide
   
.. toctree::
   :maxdepth: 2
   :caption: API documentation
   
   disbi



