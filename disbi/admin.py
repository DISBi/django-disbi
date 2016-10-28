"""
Useful admin classes and factory function that can be used
to configure the admin of the concrete app. 
"""
# standard library
import io

# third-party
from tablib.core import Dataset

# Django
from django.contrib import admin
from django.core.exceptions import ValidationError

# DISBi
from disbi._import_export import resources
from disbi._import_export.admin import (ImportExportModelAdmin,
                                       RelatedImportExportModelAdmin)


def dataframe_replace_factory(replace):
    """
    Factory for creating a mixin that replaces entries globally in an
    uploaded dataset.
    
    Args:
        replace (tuple): A 2-tuple with the old and the new value.
    
    Returns:
        Dataset: The new dataset with the replaced values.
    """
    class DataframeReplaceMixin():
        """
        DataframeReplaceMixIn provides a function to change entries in
        the dataframe before import.
        """
        def before_import(self, dataset, dry_run, **kwargs):
            stream = io.StringIO(dataset.csv
                                 .replace(replace[0], replace[1]))
            dataset = Dataset().load(stream.read(), format='csv')
            return dataset
    
    return DataframeReplaceMixin

def disbiresource_factory(mymodel, myfields, myimport_id_fields, mywidgets=None):
    """Return a resource class with the given meta options and the validation hook."""
    class DisbiResource(resources.ModelResource): 
        def before_save_instance(self, instance, dry_run):
            """Perform full_clean for validation before the instance is saved."""
            try:
                instance.full_clean()
            except ValidationError:
                raise
            
        class Meta:
            model = mymodel
            fields = myfields
            import_id_fields = myimport_id_fields
            widgets = mywidgets
    
    return DisbiResource

# ------------------------------ Inlines ------------------------------
def inline_factory(proxy, inline_type='tabular'):
    """
    Create an inline class from a proxy Model.
    
    Args:
        proxy (Model): The proxy or just the normal model from which 
            the inline class is created.
    
    Keyword Args:
        inline_type (str): The type of Inline that should be created.
            Defaults to 'tabular'.
    
    Returns:
        InlineModelAdmin: The created class.
        
    Raises:
        ValueError
        
    """
    cls_name = proxy.__class__.__name__.strip('Proxy') + 'Inline'
    if inline_type == 'tabular':
        return type(cls_name, (admin.TabularInline,), dict(model=proxy))
    elif inline_type == 'stacked':
        return type(cls_name, (admin.StackedInline,), dict(model=proxy))
    else:
        raise ValueError('InlineModelAdmin cannot be created with type {inline_type}'
                         .format(inline_type=inline_type))
    

# --------------------------- Admin classes ---------------------------    
class DisbiDataAdmin(RelatedImportExportModelAdmin):
    """
    Allow experimental data models to be filtered by their related experiments.
    """
    filter_for_extended_form = None
                               
    # Show only those experiments in the filter that have data attached to it.
    list_filter = (
        ('experiment', admin.RelatedOnlyFieldListFilter),
    )
    list_per_page = 30
