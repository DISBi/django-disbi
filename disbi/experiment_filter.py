"""
Functions for filtering the experiments based on conditions.
"""
# standard library
from copy import deepcopy

# Django
from django.conf import settings

# DISBi
from disbi.utils import clean_set


def lookup_format(dic):
    """
    Return a dictionary readily useable for filter kwargs.
    
    Args:
        dic (dict): The dictionary to be formatted.
    
    Returns:
        dict: The same dictionary with the keys concatenated with '__in'
    """
    return dict((k + '__in', v) for k, v in dic.items())

def combine_on_sep(items, separator):
    """
    Combine each item with each other item on a `separator`.
    
    Args:
        items (list): A list or iterable that remembers order.
        separator (str): The SEPARATOR the items will be combined on.
    
    Returns:
        list: A list with all the combined items as strings.
    """
    combined_items = []
    # Combine items only if there is more than 1 items.
    if len(items) > 1:
        # Convert the empty string back to minus.
        items = [i if i!='' else '-' for i in items]
        for i, item in enumerate(items):
            reduced_items = items[:i] + items[i+1:]
            combined_with_item = [separator.join((item, r)) for r in reduced_items]
            combined_items += combined_with_item
    # Else simply return the given list.
    else:
        combined_items = items
         
    return combined_items

def combine_conditions(conditions, combinable_conditions):
    """
    Apply :func:`combine_on_sep` to each value in a dictionary.
     
    Args:
        conditions (dict): Dictionary with a list of condition values.
         
    Returns:
        dict: A dictionary with the same keys and lists of combined values.
    """
    combined_conditions = {}
    
    for k, values in conditions.items():
        if k in combinable_conditions:
            combined_conditions[k] = combine_on_sep(values, settings.DISBI['SEPARATOR'])
        else:
            combined_conditions[k] = values
    return combined_conditions

def get_experiments_by_condition(conditions, experiment_model):
    """
    Return a set of experiments that match the conditions.
    
    Args:
        conditions (dict): A dictionary with conditions as keys and a list of values.
    
    Returns:
        set: A set of experiments that match the conditions.
    """
    # If nothing was chosen conditions is an empty dict and
    # evaluates to false.
    if not conditions:
        return set() 
    query_conditions = lookup_format(conditions)
    # Experiments from parameters.
    exps_by_condition = set(experiment_model.objects.filter(**query_conditions))


    # Experimental parameters that can be combined in a microarray experiment.
    combinable_conditions = [field.name for field in experiment_model._meta.get_fields()
                             if getattr(field, 'di_combinable', False)]
    combined_conditions = combine_conditions(conditions, combinable_conditions)
    combined_query_conditions = lookup_format(combined_conditions)
    # Experiments from all combinable conditions combined.
    exps_by_combined_condtion = set(experiment_model.objects.filter(**combined_query_conditions) or ()) 
    # Experiments from a single combinable condition, combined each.
    for combinable_condition in combinable_conditions:
        if combinable_condition in conditions.keys():
            c_conditions = deepcopy(conditions)
            c_conditions[combinable_condition] = combine_on_sep(conditions[combinable_condition], 
                                                                settings.DISBI['SEPARATOR'])
            c_combined_query_conditons = lookup_format(c_conditions)
            exps_by_combined_condtion |= set(experiment_model.objects.filter(
                                            **c_combined_query_conditons) or ()) 
            
    return exps_by_condition | exps_by_combined_condtion

def get_requested_experiments(formset_list, experiment_model):
    """
    Return all experiments that match the request from the form.
    
    Args:
        formset_list (list): Formsets containing POST data.
        
    Returns:
        set: The union of the set of the directly requested experiments
        and those that matched the requested conditons. 
    """
    
    # Formsets with these prefixes return model instances,
    # thus no further query is needed.
    no_query = ['experiment']
             
    conditions = {}
    for formset in formset_list:
        if formset.prefix not in no_query:
            conditions.update(clean_set(formset.cleaned_data))
        elif formset.prefix == 'experiment':
            # Directly requested experiments.
            directly_req_exps = (set(
                clean_set(formset.cleaned_data).get('experiment') or ())
                                )
    exps_from_conditions = get_experiments_by_condition(conditions, experiment_model)
    return directly_req_exps | exps_from_conditions
