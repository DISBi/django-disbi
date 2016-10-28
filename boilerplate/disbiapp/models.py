# standard library
import os
from collections import OrderedDict

# Django
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

# DISBi
import disbi.disbimodels as dmodels
from disbi.models import (BiologicalModel, MeasurementModel, DisbiExperiment,
                          DisbiExperimentMetaInfo, MetaModel)
from disbi.utils import get_hr_val, get_optgroups, remove_optgroups
from disbi.validators import ec_validator, validate_flux, validate_probabilty


# ---------------------------- Meta models -----------------------------



# ------------------------- Biological models --------------------------



# ------------------------- measurement models -------------------------


        
# -------------------------- Experiment model --------------------------

class Experiment(models.Model, DisbiExperiment):
    pass
    
    def __str__(self):
        pass
        
        
class ExperimentMetaInfo(Experiment, DisbiExperimentMetaInfo):
     
    pass
