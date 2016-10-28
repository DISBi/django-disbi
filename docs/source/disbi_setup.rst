========================
Setting up a DISBi App
========================

This guide describes both how to install DISBi and configure
your Django project correctly, as well as how to use the DISBi
framework to set up an app for your Systems Biology project.

Installation and Configuration
==============================

First you should install DISBi via ``pip``.

Install from PyPI to get the latest release::

    $ pip install django-disbi
    
Or install directly from GitHub to get the latest development version::

     $ pip install -e git+https://github.com/disbi/django-disbi.git#egg=django-disbi

Once installed, you can create a new project for setting up a DISBi app or
incorporate it in one of your existing projects.

Start project::
    
    $ django-admin startproject <disbi_project>

Start app:: 
    
    $ python manage.py startapp <organism>

Next you need to adapt a few options in your project's ``settings.py``.

Add DISBi itself, your newly created DISBi app and ``import_export``
into intalled apps. DISBi uses 
`django-import-export <https://github.com/django-import-export/django-import-export>`_
to enable uploads of data via Excel and CSV files::

    INSTALLED_APPS = [
        'disbi', # put app first to customize admin CSS
        'organism.apps.OrganismConfig',
        'import_export',
        ...
    ]

For ``import_export`` the following configuration is recommended to
wrap uploads in transactions and skip the admin log, which speeds up the upload process::
    
    IMPORT_EXPORT_USE_TRANSACTIONS = True
    IMPORT_EXPORT_SKIP_ADMIN_LOG = True

For global configuration of DISBi apps in your project the following 
settings are required. ``JOINED_TABLENAME`` is the name of the backbone
table that is used for caching. ``DATATABLE_PREFIX`` is the prefix added
to each cached datatable. ``SEPARATOR`` determines
how values in experiments comparing condintions are separated.
For example, a microarray experiment comparing the two mutants *mutA* and *mutB*
could be specified in the admin as ``mutA/mutB``, given the settings below.
``EMPTY_STR`` is an internal variable used to represent
the empty option in case of combined experiments. It only needs to be replaced if the
minus sign has another meaning in your experiments. For example,
to specify an experiments that compares *mutA* to the wildtype, 
``mutA/-`` could be given in the admin.
  

.. code-block:: python

    # Custom DISBi Settings
    DISBI = {
        'JOINED_TABLENAME': 'joined_bio_table',
        'DATATABLE_PREFIX': 'datatable',
        'SEPARATOR': '/',
        'EMPTY_STR': '-',

    }

Then you set up the connection to your Postgres database::

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql', 
            'NAME': '<disbidb>',
            'USER': '<disbi_admin>',
            'PASSWORD': '<passwd>',
            'HOST': '127.0.0.1',   # Or an IP Address that your DB is hosted on
            'PORT': '5432',
        }
    }
    

Now you need to set up directories and URLs for serving
`static files <https://docs.djangoproject.com/en/1.10/howto/static-files/#serving-files-uploaded-by-a-user>`_
and collect those files for ``import_export``.

Set up ``MEDIA_ROOT`` and URL and ``STATIC_ROOT`` and URL::

    MEDIA_ROOT = '/home/disbi/media/disbi/'
    MEDIA_URL = '/media/'
    STATIC_ROOT = os.path.join('/home/disbi/disbi/project/disbi/static')
    STATIC_URL = '/static/'

If you decide to use some of the custom templates from the boilerplate, you need to add the
directories they are included in to your template directories. For example,
if you include the templates at the project's root you need to add::

    TEMPLATES = [
        {
            ...,
            'DIRS': [os.path.join(BASE_DIR, 'templates'),],
            ...,
        },
    ]


Then let Django collect it static files::

    $ python manage.py collectstatic





Now you are free to set up your models, admin, views and URLs. While the
view and URLs can be simply copied from the boilerplate, models and admin 
are more complex and need to be adapted to your project's needs. 
A detailed description of how to configure them is available in :ref:`data-model`. 
Once you are finished with configuring
the models and the admin, you can migrate your app, create an admin superuser
and other accounts and let people start to upload their experimental data.

Make migrations and migrate::

    $ python manage.py makemigrations
    $ python manage.py migrate

Create a new Django superuser for the admin::

    $ python manage.py createsuperuser
    
Verify that everything works as expected with the development server::
    
    $ python manage.py runserver


Using the DISBi framework
=========================

To make DISBi useful for wide range of projects, it is designed
rather as a framework than an an application. 
Though it in fact is a Django app, that handles some
basic tasks, it mostly provides you with classes that help you set
up an application that meets your requirements.
In this section we walk you through the necessary steps to set up a DISBi app by 
constructing a simple app that integrates data from flux balance predictions
and metabolome analysis.

.. _data-model:

Specifying a data model
-----------------------
The data model defines what kind of information is stored in your
app and how this information interrelates. DISBi uses extended versions
of Django Models and Fields for the specification of its data model. 
Though DISBi will adapt dynamically to your data model at runtime, it
requires the data model to conform to an overall general structure, 
the *abstract data model*. The abstract data model is an attempt
at generalizing the structure of data from the domain of Systems Biology
or experimental data in general. It does so by grouping models into three
abstract categories and a concrete model: :class:`.BiologicalModel`, 
:class:`.MeasurementModel`, :class:`.MetaModel` and :class:`Experiment`.

Every source of data (simulation or real experiment) is stored in the
``Experiment`` model, with its respective parameters. :class:`MeasurementModels` store
the data points generated in these experiments. :class:`BiologicalModels` store
biological objects to which data points map and :class:`MetaModels` store information
about these biological objects.

.. _abstract-datamodel:

.. figure:: _static/images/abstract_datamodel.*
    
    Entity relationship model for relations between the model groups in 
    DISBi's abstract data model.
    
As you can see in the entity relationship model in :numref:`abstract-datamodel`, 
each data point from the :class:`MeasurementModels` can be uniquely identified by mapping to 
exactly one experiment and one instance of a :class:`BiologicalModel`.

Let's consider how we would construct models for a DISBi app that integrates
flux and metabolome data.

First we need to consider what parameters we will vary in our experiments
and simulations. To keep things simple, we will say that we only
use different *carbon sources* and different *mutants*. Additionally,
we should store the *type* of the experiment, i.e. flux or metabolome, and
the *date* it was performed on. Moreover, we will leave some space for *notes*.

.. code-block:: python

    # models.py
    import disbi.disbimodels as dmodels
    from disbi.models import (BiologicalModel, DisbiExperiment, 
                              DisbiExperimentMetaInfo, MetaModel, 
                              MeasurementModel,)
    
    class Experiment(models.Model, DisbiExperiment):
        EXPERIMENT_TYPE_CHOICES = (
            ('flux', 'Predicted Flux'),
            ('metabolome', 'Metabolome'),
        ) 
        experiment_type = dmodels.CharField(max_length=45, 
                                           choices=EXPERIMENT_TYPE_CHOICES, 
                                           di_choose=True)
        carbon_source = dmodels.CharField(max_length=45, blank=True, 
                                            di_choose=True, di_show=True)
        mutant = dmodels.CharField(max_length=45, blank=True, di_choose=True, 
                                     di_show=True)
        date = dmodels.DateField(max_length=45)
        notes = dmodels.TextField(blank=True)
        
        def __str__(self):
            return '{}. {}'.format(
                       self.id,
                       self.get_experiment_type_display()
                   ) 

Your :class:`Experiment` needs to be constructed by mixing in :class:`~disbi.models.DisbiExperiment`
to the standard Django :class:`Model` class.
As you notice, we imported and used ``dmodels.FieldClass`` instead of the
standard Django ``models.FieldClass``. These are extended versions of 
Django field classes, that allow for some DISBi specific options to 
be passed, which always start with ``di_``. Otherwise they work as the standard Django classes.
Let's have a look at what those options do:

* ``di_choose`` Determines whether a select widget will be created for 
  this field in the Data View. Since we only want to filter by experiment type,
  carbon source and mutant, we only need to set the attribute on those fields.

* ``di_show`` Determines whether the field will be shown in the tables summarizing the matched 
  experiments in the filter view. In addition to these fields, the 
  :meth:`__str__()` method of the :class:`Experiment` class will be included in the table. 
  Since :meth:`__str__()` includes the experiment type already, we don't need to include it again. 

        
Next we could override the :meth:`~disbi.models.DisbiExperiment.result_view` method, that determines
the content of the table summarizing the matched experiments in the data 
view. However, this is only necessary if would want to include information
that is not directly in the :class:`Experiment` models fields, such
as hyperlinks. So we just leave it untouched, such that it will yield
the same table as in the Data View. 

Finally, we need to add a class called :class:`ExperimentMetaInfo`.
This class handles determining the :class:`MeasurementModel` and
:class:`BiologicalModel` for each experiment. We only have to create
it by using a MixIn. No further customization is required.

.. code-block:: python

    class ExperimentMetaInfo(Experiment, DisbiExperimentMetaInfo):
         
        pass
        

Now we want to set up models that store information
about the biological objects we measure in our experiments, the 
:class:`BiologicalModels`. We will map the flux data to *Reactions* and
the metabolome data to *Metabolites*. We will relate a reaction to a 
metabolite, whenever a metabolite occurs in the reaction equation
of a reaction. This is a many-to-many relation:

.. code-block:: python

    class Reaction(BiologicalModel):
        name = dmodels.CharField(max_length=255, unique=True, di_show=True,
                                 di_display_name='reaction_name')
        reaction_equation = dmodels.TextField()
        metabolite = dmodels.ManyToManyField('Metabolite', related_name='reactions')
        
        def __str__(self):
            return self.name
        
    class Metabolite(BiologicalModel):
        name = dmodels.CharField(max_length=512, unique=True, di_show=True,
                                 di_display_name='metabolite_name', 
                                 di_show=True)
        
        def __str__(self):
            return self.name
        
As you notice, both classes derive from :class:`~disbi.models.BiologicalModel`.
This is done to identify them as :class:`BiologicalModels` for DISBi. Moreover,
you see a new field option.

* ``di_display_name`` This option is the name by which the field will
  be included in the *result table*. It only makes sense to be set if ``di_show``
  is set to ``True``, but has to be set if the normal field name collides
  with field names of other models. Otherwise, the columns
  would be indistinguishable in the result table. 
  (Notice that both :class:`Reaction`
  and :class:`Metabolite` have a :attr:`name` attribute.)

* ``di_show`` This option has a different meaning for ``BiologicalModels``.
  It determines whether or not the field should be included in the result table.

When constructing your :class:`BiologicalModels` it is always important
to keep in mind the granularity of your measurement data. For example,
you should not use a :class:`Metabolite` model to map data from a measurement
method that can only resolve groups of derivatives. Instead you should
create a new :class:`Derivative` model to which you map your data
and relate it to your :class:`Metabolite` model, such that each
:class:`Derivative` is related to each :class:`Metabolite` it can derive
from. 

Now we also want to store more information about our :class:`Reactions`. For 
example we could store all biochemical pathways in which the reaction
occurs. This is a perfect case for a :class:`~disbi.models.MetaModel`:

.. code-block:: python

    class Pathway(MetaModel):
        name = dmodels.CharField(max_length=255, unique=True, di_show=True,
                                 di_display_name='pathway')
        reaction = dmodels.ManyToManyField('Reaction', related_name='reactions')
        
        def __str__(self):
            return self.name

Notice that we could not have stored this information as a field on the
original :class:`Reaction` model, since many reactions can
occur in many pathways and vice versa. The relation is therefore
many-to-many.        
        
 
As a final step we need to set up our :class:`MeasurementModels`.
These models need to reflect the data generated by our methods.
Moreover, we need to include an explicit reference to the :class:`BiologicalModel`
the data maps to. The reference to the :class:`Experiment` model
is already included in the base class.
Let's assume that our flux balance analysis program gives us
a flux value and an upper and lower bound for this value. Let's further
assume that we perform our metabolome method in triplets, so that 
we only store the mean and the standard error of each sample. This could
be encoded in the models as follows:

.. code-block:: python

    class FluxData(MeasurementModel):
        flux = dmodels.FloatField(di_show=True)
        flux_min = dmodels.FloatField(di_show=True, di_display_name='lb')
        flux_max = dmodels.FloatField(di_show=True, di_display_name='ub')
        
        reaction = dmodels.ForeignKey('Reaction', on_delete=models.CASCADE)

        class Meta:
            unique_together = (('reaction', 'experiment',))
            verbose_name_plural = 'Fluxes'
            
        def __str__(self):
            return 'Flux data point'
        

    class MetabolomeData(MeasurementModel):
        mean = dmodels.FloatField(di_show=True)
        stderr = dmodels.FloatField(di_show=True)
        
        metabolite = dmodels.ForeignKey('Metabolite', on_delete=models.CASCADE)
        
        class Meta:
            unique_together = (('metabolite', 'experiment'),)
            verbose_name_plural = 'Metabolome data points'
        
        def __str__(self):
            return 'Metabolome data point'
    
If we look at our data model as a whole, we can see that it has
all the features demanded by the abstract data model.

.. figure:: _static/images/example_erm.*

    Entity relationship model for the concrete data model.

    
Congratulations, you have just finished making your first DISBi
data model. DISBi data models can grow much more complex than
described here. You can map more than one :class:`MeasurementModel`
to the same :class:`BiologicalModel` or no :class:`MeasurementModel` at all.
You can also have more complex relation between your :class:`BiologicalModels`.
The only requirement is that the graph formed by the relations between your
:class:`BiologicalModels`  and :class:`MetaModels` is a *tree*, i.e. every model
needs to be reachable from every other model and their must be no circles. 
This is due to the way DISBi automatically joins the data behind the
scenes.          
        


Configuring the admin
---------------------

Once you have figured out your data model, you need to set up an admin 
interface so that researches can easily upload their data.
Though you have full freedom in customizing the Django admin, DISBi
provides a few usefull classes to set up an admin that's suitable
for handling experimental datasets.

In general you'll want one :class:`Admin` class for each of your model
classes. Since normal Django :class:`ModelAdmins` just offer
an HTML form to enter new data, DISBi uses 
`django-import-export <http://django-import-export.readthedocs.io/en/latest/>`_
to enable data upload of larger datasets from files, like CSV and Excel. The handling
of the file upload is mostly done by a :class:`Resource` class.
DISBi offers the factory function :func:`~disbi.admin.disbiresource_factory`
that produces a :class:`Resource` class that checks data integrity
before inserting the value into the database. It is recommended, though
not necessary to use the factory.
The admin classes for our :class:`BiologicalModels` could look like this:

.. code-block:: python

    # admin.py
    from import_export.admin import ImportExportModelAdmin
    from django.contrib import admin
    from disbi.admin import (DisbiDataAdmin, disbiresource_factory)
    from .models import (Experiment, FluxData, MetabolomeData,
                         Metabolite, Reaction, Pathway)

    @admin.register(Reaction)
    class ReactionAdmin(ImportExportModelAdmin):
        resource_class = disbiresource_factory(
            mymodel=Reaction,
            myfields=('name', 'reaction_equation',
                      'metabolite',),
            myimport_id_fields=['name'],
            mywidgets={'metabolite':
                       {'field': 'name'}}
        )
        search_fields = ('name', 'reaction_equation',)
        filter_horizontal = ('metabolite',)
        
        
    @admin.register(Metabolite)
    class MetaboliteAdmin(ImportExportModelAdmin):
        resource_class = disbiresource_factory(
            mymodel=Metabolite,
            myfields=('name',),
            myimport_id_fields=['name'],
        )
        search_fields = ('name',)
    

Let's look more closely at the arguments of :func:`~disbi.admin.disbiresource_factory`.

* ``mymodel`` is the :class:`Model` class the :class:`Resource` is created 
  for. This is the same class that is registered for the admin.
  
* ``myfields`` are the fields that will be imported from the uploaded file
  and therefore have to be present as columns in the file. The list 
  should include all fields that were set in ``models.py``.
  
* ``myimport_id_fields`` is the human readable primary key that serves
  for identifying the rows in the uploaded file as objects in the 
  database. Though Django uses numerical ids internally, researchers 
  don't talk about reactions and metabolites in terms of numbers.
  With this option, you can also specify compound keys (a key
  that consist of more than one field) and update data by changing
  values in your data file and re-uploading it.
  
* ``mywidgets`` is a dictionary, that passes Meta options to the 
  :class:`~import_export.widgets.Widget` class used in the import.
  That is especially important when importing a foreign key, as the 
  identifying attributes of the other :class:`Model` have to be put here.
  

The configuration of the admin class for our :class:`Pathway` model
follows the same principle::
  
    @admin.register(Pathway)   
    class PathwayAdmin(ImportExportModelAdmin):
        resource_class = disbiresource_factory(
                mymodel=Pathway,
                myfields=('name', 'reaction',),
                myimport_id_fields=['name'],
                mywidgets={'reaction':
                           {'field': 'name'}}
        )
        search_fields = ('name',)
        filter_horizontal = ('reaction',)


Now lets turn to our :class:`MeasurementModels`. These pose a special
challenge since researchers usually will produce one file per experiment.
This way, each file will have to contain a column with the same
value for the same experiments. To save users from the tedious process
of appending a column to each file, DISBi offers a special admin class.
It gives the user the opportunity to choose the experiment the data
belongs to at the time the file is uploaded.
This class only has to be configured with our concrete :class:`Experiment` model.
A pattern we'll encounter again when setting up the views.  

.. code-block:: python

    class MeasurementAdmin(DisbiMeasurementAdmin):
        model_for_extended_form = Experiment
 
Then we can use it as a base class to define the admin classes for our :class:`MeasurementModels`::

    @admin.register(FluxData)
    class FluxAdmin(MeasurementAdmin):
        resource_class = FluxResource
        
        filter_for_extended_form = {'experiment_type': 'flux'}
        
        list_display = ('reaction', 'flux', 'flux_min', 'flux_max',)
        search_fields = ('reaction__reaction_equation', 'reaction__name',)
        
        
    @admin.register(MetobolomeData)
    class MetabolomeDataAdmin(MeasurementAdmin):    
        resource_class = disbiresource_factory(
            mymodel=MetobolomeData,
            myfields=('metabolite', 'mean', 'stderr', 'experiment',),
            myimport_id_fields=['metabolite', 'experiment'],
            mywidgets={'metabolite':
                       {'field': 'name'},}
        ) 
        
        filter_for_extended_form = {'experiment_type': 'metabolome'}
        
        list_display = ('metabolite', 'mean',)


Note that we don't have to specify how the experiments should be 
identified in ``mywidgets`` as this will be handled by the :class:`MeasurementAdmin`
class. We also set a the class-level attribute :attr:`.filter_for_extended_form`.
This dictionary will be passed as keyword arguments to the :meth:`.filter`
on the :class:`Experiment` model. It determines which of the stored
experiments are eligible. It makes sense to limit those to the 
experiments of the corresponding type. :class:`MeasurementAdmin` will
also add a filter in the admin site for each :class:`MeasurementModel`,
so the data points can be filtered by the experiments they belong to.

Finally, we need an admin class for our :class:`Experiment` model. This
can be kept simple. Let's only set the ``save_as`` option to
allow users to use existing experiments as templates for 
creating new entries::

    @admin.register(Experiment)
    class ExperimentAdmin(admin.ModelAdmin):
        save_as = True 
        save_as_continue = False 

Now you've gone through the difficult part of configuring your
DISBi app. You'll be good to go after a few final steps.

Setting up views and URLs
-----------------------------

The configuration of the views and URLs is simply boilerplate code.
DISBi uses class-based views to allow for easy configuration.
The idea is that you subclass this views and configure them
with your concrete :class:`Experiment` model, as DISBi cannot
know about your model by itself. However, since the code will always
look the same you can simply copy it::

    # views.py
    from disbi.views import (DisbiCalculateFoldChangeView, DisbiComparePlotView,
                             DisbiDataView, DisbiDistributionPlotView,
                             DisbiExperimentFilterView, DisbiExpInfoView,
                             DisbiGetTableData)
    from .models import Experiment, ExperimentMetaInfo


    class ExperimentFilterView(DisbiExperimentFilterView):
        experiment_model = Experiment

        
    class ExperimentInfoView(DisbiExpInfoView):
        experiment_model = Experiment


    class DataView(DisbiDataView):
        experiment_meta_model = ExperimentMetaInfo
       
        
    class CalculateFoldChangeView(DisbiCalculateFoldChangeView):
        experiment_model = Experiment
        experiment_meta_model = ExperimentMetaInfo


    class ComparePlotView(DisbiComparePlotView):
        experiment_model = Experiment
        experiment_meta_model = ExperimentMetaInfo

        
    class DistributionPlotView(DisbiDistributionPlotView):    
        experiment_model = Experiment
        experiment_meta_model = ExperimentMetaInfo


    class GetTableData(DisbiGetTableData):
        experiment_meta_model = ExperimentMetaInfo
        
Unless you want to modify some of the views, it is not really
important to know what they do exactly. More information can be
found in the :doc:`API documentation <disbi>`.

The configuration of the URLs is similarly fixed. You simply
need to associate your views with the right URL patterns. As
the views often take arguments from the URL patterns, you should 
not try to change them. The simplest thing is again to stick to
the boilerplate code::

    # urls.py
    from django.conf.urls import url
    from . import views

    app_name = 'yourapp'
    urlpatterns = [
        url(r'^filter/exp_info/', views.ExperimentInfoView.as_view(), name='exp_info'),
        url(r'^filter/', views.ExperimentFilterView.as_view(), name='experiment_filter'),
        url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/get_distribution_plot/', 
            views.DistributionPlotView.as_view(), 
            name='get_distribution_plot'),
        url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/get_compare_plot/', 
           views.ComparePlotView.as_view(), 
           name='get_compare_plot'),
        url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/calculate_fold_change/', 
            views.CalculateFoldChangeView.as_view(), 
            name='fold_change'),
        url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/get_table_data/', 
            views.GetTableData.as_view(), 
            name='get_table_data'),
        url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/$', views.DataView.as_view(), name='data'),
    ]

Then you only need to include your apps URLs in your project's 
``urls.py`` and your done.

This was a quick tour through what you can accomplish with
DISBi and how to do it. To help getting started even faster, there 
is a complete boilerplate available on GitHub.

If you encounter any problems when setting up your DISBi app, feel free to 
contact us on GitHub and open an issue.
We are happy to hear your experiences, so we can continuously improve
and extend DISBi in the way the research community needs it.
If you want to help to improve DISBi yourself, you can find 
all necessary information in :doc:`contributing`.



























