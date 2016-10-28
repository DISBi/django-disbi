from __future__ import unicode_literals

import os.path

from django import forms
from django.contrib.admin.helpers import ActionForm
from django.utils.translation import ugettext_lazy as _


class ImportForm(forms.Form):
    import_file = forms.FileField(
        label=_('File to import')
        )
    input_format = forms.ChoiceField(
        label=_('Format'),
        choices=(),
        )

    def __init__(self, import_formats, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)
        choices = []
        for i, f in enumerate(import_formats):
            choices.append((str(i), f().get_title(),))
        if len(import_formats) > 1:
            choices.insert(0, ('', '---'))

        self.fields['input_format'].choices = choices


class ConfirmImportForm(forms.Form):
    import_file_name = forms.CharField(widget=forms.HiddenInput())
    original_file_name = forms.CharField(widget=forms.HiddenInput())
    input_format = forms.CharField(widget=forms.HiddenInput())

    def clean_import_file_name(self):
        data = self.cleaned_data['import_file_name']
        data = os.path.basename(data)
        return data


class ExportForm(forms.Form):
    file_format = forms.ChoiceField(
        label=_('Format'),
        choices=(),
        )

    def __init__(self, formats, *args, **kwargs):
        super(ExportForm, self).__init__(*args, **kwargs)
        choices = []
        for i, f in enumerate(formats):
            choices.append((str(i), f().get_title(),))
        if len(formats) > 1:
            choices.insert(0, ('', '---'))

        self.fields['file_format'].choices = choices


def export_action_form_factory(formats):
    """
    Returns an ActionForm subclass containing a ChoiceField populated with
    the given formats.
    """
    class _ExportActionForm(ActionForm):
        """
        Action form with export format ChoiceField.
        """
        file_format = forms.ChoiceField(
            label=_('Format'), choices=formats, required=False)
    _ExportActionForm.__name__ = str('ExportActionForm')

    return _ExportActionForm


class RelatedImportForm(ImportForm):
    """Add a model choice field for a given model to the standard form."""
     
    appended_instance = forms.ModelChoiceField(queryset=None)
 
    def __init__(self, extend_form_model, extend_form_filter, import_formats, *args, **kwargs):
        super().__init__(import_formats, *args, **kwargs)
        if extend_form_filter is not None:
            self.fields['appended_instance'].queryset = extend_form_model.objects.filter(**extend_form_filter)
        else:
            self.fields['appended_instance'].queryset = extend_form_model.objects.all()
        self.fields['appended_instance'].label = extend_form_model._meta.verbose_name.capitalize()

class RelatedConfirmForm(ConfirmImportForm):
    """
    Form for confirmation of the import with the appended instance.
    """
    appended_instance = forms.ModelChoiceField(queryset=None,
                                               widget=forms.HiddenInput())
    
    def __init__(self, extend_form_model, extend_form_filter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if extend_form_filter is not None:
            self.fields['appended_instance'].queryset = extend_form_model.objects.filter(**extend_form_filter)
        else:
            self.fields['appended_instance'].queryset = extend_form_model.objects.all()



