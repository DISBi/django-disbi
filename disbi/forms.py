"""
Forms used throughout the DISBi app.
"""
# standard library
from collections import namedtuple

# third-party
from more_itertools import unique_everseen

# Django
from django import forms
from django.conf import settings
from django.db.models.fields.related import ForeignKey
from django.utils.translation import ugettext_lazy as _

# DISBi
from disbi.utils import camelize, construct_none_displayer


# ----------------------------- functions -----------------------------

def make_ChoiceField(model, attribute, label=None, empty_choice=None):
    """
    Return a ChoiceField and the maxiumn number of choices.
    
    The ChoiceField contains all distinct values of an attribute of model.
    Addtionally a NULL option is inserted as first choice.
    
    Args:
        attribute (Field): The attribute of the model. 
        label (str): The label used when displaying the form (default None).
        empty_choice (tuple): 2-tuple of a value label pair, used for enabling
            the user to choose an empty condition, e.g. no stress.
    
    Returns:
        ChoiceField: A Choicefield based on the available options in the DB.
        int: The number of availablbe options.
        
    Raises:
        IndexError: Raises error when no entries are found in the DB. 
    """
    
    try:
        entries = model.objects.values_list(attribute, flat=True).distinct()
        
        max_num = len(entries)
       
        # Format human-readable label according to type
        if isinstance(entries[0], str):
            # Split on SEPARATOR, flatten list and make it unique.
            entries = [e.split(settings.DISBI['SEPARATOR']) for e in entries if e]
            entries = sum(entries, [])
            entries = list(unique_everseen(entries))
            entries = [e for e in entries if e != settings.DISBI['EMPTY_STR']]
            # Capitalize first letter, ignore empty string
            choices = [(e, e.capitalize()) if e == e.lower() else (e, e) 
                       for e in entries if e]
            
        else:
            choices = [(e, e) for e in entries if e]
        
        if empty_choice is not None:
            choices.append(empty_choice)
        
        choices.insert(0, (None, construct_none_displayer(entries)))
        # Use label if given
        if label is not None:
            field = forms.ChoiceField(choices=choices, label=label)
        else:
            field = forms.ChoiceField(choices=choices)
        return field, max_num
    except IndexError:
        raise Exception('No entries for field {}'.format(attribute))
        

def construct_direct_select_form(model):
    """
    Construct a form for directly selecting model instances.
    
    Args:
        model (models.Model): A Django model, for which the form is constructed.
    """
    cls_name = model.__name__ + 'Form'
    entries = model.objects.all()
    mymax_num = len(entries)
    myselect_field = forms.ModelChoiceField(queryset=entries)
    form = type(cls_name, (forms.Form,), {
                model.__name__.lower(): myselect_field,
                'max_num': mymax_num,}
            )
    return form

def construct_foreign_select_field(model, field):
    """
    Construct a form for directly selecting related model instances.
    
    Args:
        model (models.Model): A Django model, for which the form is constructed.
        field (fields.related.ForeignKey): The field of the realated instances.
    """
    entries = field.related_model.objects.filter(pk__in=
                model.objects.values_list(field.name, flat=True).distinct()
            )
    max_num = len(entries)
    select_field = forms.ModelChoiceField(queryset=entries)
    return select_field, max_num 




def construct_modelfieldsform(model, exclude=['id'], direct_select=False):
    """
    Construct forms based on a model and available values in the DB.
    
    Args:
        model (models.Model): A Django model, for which the forms are constructed.
        
    Keyword Args:
        exclude (iterable): Fields for which no forms should be constructed.
        direct_select (bool): Determines whether a form for directly selecting
            model instances is constructed.
    
    Returns:
        list: A list of namedtuples with the form classes and the prefix. 
    """
    NamedFormClass = namedtuple('NamedFormClass', ['classname', 'prefix'])
    formclasses = []
    if direct_select:
        form = construct_direct_select_form(model)
        formclasses.append(NamedFormClass(form, model.__name__.lower()))
    
    fields = [f for f in model._meta.get_fields() if f.concrete]
    for field in fields:
        if field.name not in exclude:
            # Construct class name and form label.
            cls_name = camelize(field.name) + 'Form'
            mylabel = field.verbose_name\
                    if field.verbose_name != field.name.replace('_', ' ')\
                    else None
            # If dealing with a foreign key field, get the related objects.
            if isinstance(field, ForeignKey):
                myselect_field, mymax_num = construct_foreign_select_field(model, field)
            # When dealing else with a normal field use make_Choicefield().
            else:
                # Check whether an empty value representation was added to the model.
                try:
                    myempty_choice = (settings.DISBI['EMPTY_STR'], field.di_empty)
                except AttributeError:
                    myempty_choice = None
                myselect_field, mymax_num = make_ChoiceField(model, field.name, 
                                                             label=mylabel,
                                                             empty_choice=myempty_choice)
            form = type(cls_name, (forms.Form,), {
                    field.name: myselect_field,
                    'max_num': mymax_num,}
                    )
            formclasses.append(NamedFormClass(form, field.name))
    return formclasses

def construct_forms(experiment_model):
    """Wrapper for `construct_modelfieldsform` with appropriate arguments."""
    
    exclude_fields = [
                      field.name for field in experiment_model._meta.get_fields()
                      if field.concrete and
                      not getattr(field, 'di_choose', False)
                      ]
    
    return  construct_modelfieldsform(
                experiment_model,
                direct_select=True, 
                exclude=exclude_fields
            )

def foldchange_form_factory(experiments):
    """
    Create a form with two fields for selecting experiments.
    
    The fields are select widgets allowing to calculate a fold change
    between the two.
    
    Args:
        experiments (Queryset): The selectable experiments.
    
    Returns:
        Form: The constructed form.
    """
    class FoldChangeForm(forms.Form):
        """
        Form for getting two experiments that should be compared.
        """
        dividend = forms.ModelChoiceField(queryset=experiments)
        divisor = forms.ModelChoiceField(queryset=experiments)
        
        def clean(self):
            """
            Check whether the two selected experiments are different.
            """
            cleaned_data = super().clean()
            if cleaned_data.get('dividend') == cleaned_data.get('divisor'):
                raise forms.ValidationError(
                        _('Selected same experiment for calculating fold change'),
                        code='divided by self',
                )
            
    return FoldChangeForm
    
