# standard library
from collections import OrderedDict

# Django
from django.apps import apps
from django.db import models

# DISBi
import disbi.disbimodels as dmodels


class MetaModel(models.Model):
    """
    Baseclass for clustering the entities with meta information.
     
    Meta informations are considered here as entities that can not be measured 
    in an experiment. 
    """
     
    class Meta:
        abstract = True


class BiologicalModel(models.Model):
    """
    Baseclass for clustering the biological entities.
    """ 
    pass
     
    class Meta:
        abstract = True


class MeasurementModel(models.Model):
    """Base class for clustering the measurement models."""
    experiment = dmodels.ForeignKey('Experiment', on_delete=models.CASCADE)
    
    class Meta:
        abstract = True
    
    
class DisbiExperiment():
    """
    Mixin for managing experiments.
    """    
    def view(self):
        """
        Construct an OrderedDict based on a tuple of column names.
        
        Each column name is either expected to be a method or an 
        attribute of the object. For the keys of the dict, the
        `short_description` is preferred. For attributes `verbose_name`
        is preferred over `name`. 
        
        Args:
            cols (tuple): The column names.
        
        Returns:
            OrderedDict: The external representation or view of the 
            experiment object.
        """
        
        cols = [
                field.name for field in self.__class__._meta.get_fields()
                if field.concrete and
                getattr(field, 'di_show', False)
            ]
        # Use the string representation as first field.
        cols.insert(0, '__str__')
        
        view = OrderedDict()
        for col in cols:
            # Will throw an error if the given col is no attribute.
            attr = self.__getattribute__(col)
            if callable(attr):
                if hasattr(attr, 'short_description'):
                    header = attr.short_description
                elif col == '__str__':
                    header = self.__class__.__name__
                else:
                    header = col
                view[header] = attr()
            else:
                try:
                    field = self.__class__._meta.get_field(col)
                    header = field.verbose_name\
                     if field.verbose_name != field.name.replace('_', ' ')\
                     else field.verbose_name.capitalize()
                except:
                    header = col
                if isinstance(attr, models.Model):
                    attr = attr.__str__() 
                view[header] = attr
        return view
    
    def result_view(self):
        """
        Creates a row with information that should be displayed
        in the data view. Override in your app, if you need specific
        information in the table.
        
        Returns:
            OrderedDict: Contains the information for one row of the 
            result table.  
        """
        return self.view()
    
            
class DisbiExperimentMetaInfo():
    """
    Mixin for Experiment proxy model, that fetches additionaly information about
    the experiment when instantiated.
    """
    
    class Meta:
        proxy = True 
    
    def __init__(self, *args, **kwargs):
        """
        Get the related MeasurementModel and the biological model for the experiment.
        
        The found classes are attached as attributes to the instance.
        """
        super().__init__(*args, **kwargs)
        
        app_models = apps.get_app_config(self._meta.app_label).get_models()
        # Iterate throw all models and check whether they are a MeasurementModel and no proxy.
        # If the key of the experiment exists in the model table, that is the 
        # right model.
        self.measurementmodel = None
        for model in app_models:  
            if issubclass(model, MeasurementModel) and not model._meta.proxy:
                related_data = model.objects.filter(experiment=self.id)
                if related_data.exists():
                    self.measurementmodel = model
        if self.measurementmodel is not None:        
            for field in self.measurementmodel._meta.get_fields():
                # Assuming that each MeasurementModel maps to one type in the biological
                # level, the first that is of that type is the right one.
                if field.rel:
                    if issubclass(field.related_model, BiologicalModel):
                        self.biofield = field
                        self.biomodel = field.related_model
        else:
            self.biofield = None
            self.biomodel = None
        
        
class Checksum(models.Model):
    """
    Model for storing the checksums of other tables for 
    checking whether data has changed.
    """
    table_name = models.CharField(max_length=512)
    checksum = models.CharField(max_length=1024, null=True)
