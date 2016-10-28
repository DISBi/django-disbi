"""
Some utility functions used throughout the DISBi app.
"""
# standard library
from collections import OrderedDict
from copy import deepcopy

# Django
from django.conf import settings
from django.db import models


def clean_set(cleaned_formset_data):
    """Return a dictionary with keys from POST and lists as values.
    
    The cleaned_data of a formset is a list of dictionaries that can have 
    overlapping keys. The function changes that into a dictionary where each
    key corresponds to list of values that belonged to the same key.
    
    Returns:
        dict: Dictionary with items joined on keys.
    """
    cleaned_set = {}
    for clean_data in cleaned_formset_data:
        for attr, val in clean_data.items():
            # Turn empty string placeholder back into empty string,
            # thus the empyt string can be passed through the froms clean() method.
            if val == settings.DISBI['EMPTY_STR']:
                val = ''
            if attr in cleaned_set.keys():
                cleaned_set[attr].append(val)
            else:
                cleaned_set[attr] = [val]
    return cleaned_set

def construct_none_displayer(entries, placeholder='-'):
    """Return a string to be used as a placeholder for an empty option.
    
    The length of the placeholder is based on the length of the longest
    option in a list of entries.
    """
    # Convert to string as a precaution to figure out length. 
    entries = [str(e) for e in entries]
    # Get length of longest string from list
    max_len = len(max(entries, key=len))
    # Insert display option for choosing None
    if max_len > 4:
        none_dislplayer =  placeholder * (max_len+1)
    else:
        none_dislplayer = placeholder * 5
    return none_dislplayer

def get_choices(choice_tup, style='db'):
    """
    Return the choices given on a model Field.
    
    Args:
        choice_tup: The choice tuple given in the model.
    
    Keyword Args:
        style: Determines whether the human readable "display" values should
               be returned or those from the "db".
    """
    
    if style == 'db':
        idx = 0
    elif style == 'display':
        idx = 1
    else:
        raise ValueError
    
    # check whether the tuple contains extra optgroup
    if isinstance(choice_tup[0][1][0], str):
        optgroup = False
    else:
        optgroup = True
        
    output_choices = []
            
    if optgroup:    
        for group in choice_tup:
            for pair in group[1]:
                output_choices.append(pair[idx])
    else:
        for pair in choice_tup:
            output_choices.append(pair[idx])
                
    return output_choices

def get_optgroups(choice_tup, style='db'):
    """
    Parse the choices given on a model Field and map them to their groups.
    
    Args:
        choice_tup: The choice tuple given in the model.
    
    Keyword Args:
        style: Determines whether the human readable "display" values should
               be returned or those from the "db".
    
    Returns:
        dict: A list of choices mapped to their optgroup.
    """

    if style == 'db':
        idx = 0
    elif style == 'display':
        idx = 1
    else:
        raise ValueError('Style must either be "db" or "display".')
    
    # Check whether the tuple contains extra optgroup.
    if isinstance(choice_tup[0][1][0], str):
        optgroup = False
    else:
        optgroup = True
        
    output_choices = {}
            
    if optgroup:    
        for group in choice_tup:
            opt_choices = []
            for pair in group[1]:
                opt_choices.append(pair[idx])
            output_choices[group[0]] = opt_choices
    else:
        raise ValueError('The choices must contain optgroups.')
                
    return output_choices

def get_hr_val(choices, db_val):
    """
    Get the human readable value for the DB value from a choice tuple.
    
    Args:
        choices (tuple): The choice tuple given in the model.
        db_val: The respective DB value.
        
    Returns:
        The matching human readable value.
    """
    
    for pair in choices:
        if pair[0] == db_val:
            return pair[1]
    # Value not found.
    return None    

def remove_optgroups(choices):
    """
    Remove optgroups from a choice tuple.
     
    Args:
        choices (tuple): The choice tuple given in the model.
        
    Returns:
        The n by 2 choice tuple without optgroups.
    """
    
    # Check whether the tuple contains extra optgroup
    if isinstance(choices[0][1][0], str):
        optgroup = False
    else:
        optgroup = True
        
    output_choices = []
            
    if optgroup:    
        # Remove the optgroups and return the new tuple.
        for group in choices:
            for pair in group[1]:
                output_choices.append(pair)
        return tuple(output_choices)
    else:
        # The choices do not contain optgroups and can simply be returned.
        return choices
                
    
def reverse_dict(dic):
    """
    Return a reversed dictionary.
    
    Each former value will be the key of a list of all keys that were 
    mapping to it in the old dict.
    """
    return {new_key: [old_key for old_key, old_val in dic.items() if old_val == new_key]
                for new_key in set(dic.values())}
    
def merge_dicts(a, b):
    """
    Merge two dicts without modifying them inplace.
    
    Args:
        a (dict): The first dict.
        b (dict): The second dict. Overrides ``a`` on conflicts.
    
    Returns:
        dict: A merged dictionary.
    """
    merged_dict = deepcopy(a)
    merged_dict.update(b)
    return merged_dict    
    
def zip_dicts(a, b):
    """Merge two dicts, choose none empty value on key conflicts.
    
    The dicts are not modified inplace, but returned.
    
    Args:
        a (dict): The first dict.
        b (dict): The second dict. Overrides a on conflicts, when both
            values are none emtpy.
    Returns:
        dict: A merged dictionary.
    """ 
    merged_dict = deepcopy(a)
    
    for k, v in b.items():
        if k not in merged_dict.keys():
            merged_dict[k] = v
        else:
            if v:
                merged_dict[k] = v   

def object_view(obj, cols):
    """
    Construct an external representation of an object
    based on a tuple of field/column names.
    
    Each column name is either expected to be a method or an 
    attribute of the object. For the keys of the dict, the
    `short_description` is preferred. For attributes `verbose_name`
    is preferred over `name`. 
    
    Args:
        obj: Any object with `cols` as attributes.
        cols (tuple): The column names.
    
    Returns:
        OrderedDict: The headers as keys and the entries as values.
    """
    view = OrderedDict()
    for col in cols:
        # Will throw an error if the given col is no attribute.
        attr = obj.__getattribute__(col)
        if callable(attr):
            if hasattr(attr, 'short_description'):
                header = attr.short_description
            elif col == '__str__':
                header = obj.__class__.__name__
            else:
                header = col
            view[header] = attr()
        else:
            try:
                field = obj.__class__._meta.get_field(col)
                header = field.verbose_name
            except:
                header = col
            if isinstance(attr, models.Model):
                attr = attr.__str__() 
            view[header] = attr
    return view

def get_id_str(objects, delimiter='_'):
    """
    Get a string of sorted ids, separated by a delimiter.
    
    Args:
        objects (Model): An iterable of model instances.
    
    Keyword Args:
        delimiter (str): The string the ids will be joined on.
        
    Returns:
        str: The joined and sorted id string.
    """
    ids = [obj.id for obj in objects]
    ids.sort()
    ids = [str(identifier) for identifier in ids]
    id_str = delimiter.join(ids)
    return id_str

def get_ids(string, delimiter='_'):
    """
    Get sorted `ids`. 
    """
    ids = string.split(delimiter)
    ids = [int(identifier) for identifier in ids]
    ids.sort()
    return ids

def get_unique(items):
    """
    Get a list of unique items, even for non hashable items.
    """
    unique_list = []
    for item in items:
        if not item in unique_list:
            unique_list.append(item)
    return unique_list

def sort_by_other(sequence, order):
    """
    Order a list a another list that contains the desired order.
    
    Args:
        sequence (list): The list that is ordered. All items must be
            contained in order.
        order (list): The list containing the order.
    
    Returns:
        list: The sequence ordered according to order.
    """
    # Map the names of order to their indexes.
    order_dict = dict({(key, idx) for idx, key,  in enumerate(order)})
    # Get the indexes in respect to order from sequence.
    implicit_order = [order_dict[val] for val in sequence]
    # Zip and sort.
    return [val for (idx, val) in sorted(zip(implicit_order, sequence))]

def camelize(string, uppercase_first_letter=True):
    """
    Convert a string with underscores to a camelCase string.
    
    Inspired by :func:`inflection.camelize` but even seems to run a little faster.
    
    Args:
        string (str): The string to be converted.
        uppercase_first_letter (bool): Determines whether the first letter
            of the string should be capitalized.
    
    Returns:
        str: The camelized string.
    """    

    if uppercase_first_letter:
        return ''.join([word.capitalize() for word in string.split('_')])
    elif not uppercase_first_letter:
        words = [word.capitalize() for word in string.split('_')]
        words[0] = words[0].lower()
        return ''.join(words)

