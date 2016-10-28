# third-party
from import_export.admin import ImportExportModelAdmin

# Django
from django.contrib import admin

# DISBi
from disbi.admin import (DisbiDataAdmin, dataframe_replace_factory,
                         disbiresource_factory, inline_factory)

# App
from .models import Experiment
                     

class DataAdmin(DisbiDataAdmin):
    model_for_extended_form = Experiment
    
# ----------------------- Admins for Meta models -----------------------



# -------------------- Admins for Biological models --------------------

    

# ------------------- Admins for Measurement models --------------------



# ---------------------- Admins for other models -----------------------

@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    save_as = True # Allow to use existing object as template for new one.
    save_as_continue = False
    
