"""
Module for treating the custom DISBi options attached to the model fields.
"""
from django.apps import apps


def get_display_name(field):
    """
    Get the name used to display a field in the external representation.
    
    Args:
        field (Field): The respective field.
    
    Returns:
        str: The display_name used for external representation.
    """
    name = getattr(field, 'di_display_name', field.name)
    # If field has the `display_name` attribute, but the attribute
    # is empty return `field.name` instead.
    return name if name else field.name

def get_models_of_superclass(app_label, model_superclasses, intermediary=False):
    """
    Get all the models that derive from one superclass and include the 
    intermediary models for N:M related models.
    
    Args:
        app_label (str): The label of the app the models live in.
        model_superclasses (iterable of type): The classes from which all models of 
                interest derive.
    
    Keyword Args:
        intermediary (bool): Determines whether models should be included. 
        
    Returns:
        list: All models that derive from `mode_superclass`. Plus their
        intermediary models that are no proxys if ``intermediary`` 
        is True.
    """
    app_models = apps.get_app_config(app_label).get_models()
    models_of_supcls = []
    # Get all models of the superclasses.
    for model in app_models:  
        for model_supcls in model_superclasses:
            if issubclass(model, model_supcls) and not model._meta.proxy:
                models_of_supcls.append(model)
    # Get all intermediary models of the afore found models.
    if intermediary:
        for model in models_of_supcls:
            for intermediary_model in model._meta.many_to_many:
                models_of_supcls.append(intermediary_model.remote_field.through)
    return models_of_supcls
