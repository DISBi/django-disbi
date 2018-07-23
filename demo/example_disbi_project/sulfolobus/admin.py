# third-party
from import_export.admin import ImportExportModelAdmin

# Django
from django.contrib import admin

# DISBi
from disbi.admin import (DisbiMeasurementAdmin, dataframe_replace_factory,
                         disbiresource_factory, inline_factory)

# App
from .models import (DerivativeGroup, Experiment, FluxData, GCMSData,
                     Locus, Metabolite, RawData, Reaction, RNAseqData,
                     GCMSData, CoAData, ProteomeData, CoADerivative, Pathway)
                     
class DataAdmin(DisbiMeasurementAdmin):
    model_for_extended_form = Experiment
    

@admin.register(Pathway)   
class PathwayAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    filter_horizontal = ('reaction',)

# ------------------- Admins for biological models --------------------
@admin.register(Locus)
class LocusAdmin(ImportExportModelAdmin):
    resource_class = disbiresource_factory(
        mymodel=Locus,
        myfields=('locus_tag', 'product', 'ec_number', 'reaction'),
        myimport_id_fields=['locus_tag'],
        mywidgets={'reaction':
                   {'field': 'name'},}
    )
    
    search_fields = ('locus_tag',)
    filter_horizontal = ('reaction',)
    

@admin.register(Reaction)
class ReactionAdmin(ImportExportModelAdmin):
    resource_class = disbiresource_factory(
        mymodel=Reaction,
        myfields=('name', 'reaction_equation',
                  'lb', 'ub', 
                  'brenda', 'kegg', 'metacyc', 
                  'pubmed', 'notes', 'metabolite',),
        myimport_id_fields=['name'],
        mywidgets={'metabolite':
                   {'field': 'name'}}
    )
    search_fields = ('name', 'reaction_equation',)
    filter_horizontal = ('metabolite',)
    list_display = ('reaction_equation', 'db_crossref')
    
    
@admin.register(Metabolite)
class MetaboliteAdmin(ImportExportModelAdmin):
    resource_class = disbiresource_factory(
        mymodel=Metabolite,
        myfields=('name', 'co_a_derivative', 'derivative_group',),
        myimport_id_fields=['name'],
        mywidgets={'derivative_group':
                       {'field': 'name'},
                   'co_a_derivative':
                       {'field': 'name'},}
    )
    search_fields = ('model_name', 'brenda_group_id')
    
    
@admin.register(DerivativeGroup)
class DerivativeGroupAdmin(ImportExportModelAdmin):
    resource_class = disbiresource_factory(
        mymodel=DerivativeGroup,
        myfields=('name',),
        myimport_id_fields=['name',],
    )
    search_fields = ('name',)
    

@admin.register(CoADerivative)
class CoADerivativeAdmin(ImportExportModelAdmin):
    resource_class = disbiresource_factory(
        mymodel=CoADerivative,
        myfields=('name',),
        myimport_id_fields=['name',],
    )
    search_fields = ('name',)
    
    
# ---------------------- Admins for DataModels ------------------------
@admin.register(RNAseqData)
class RNASeqAdmin(DataAdmin):
    resource_class = disbiresource_factory(
        mymodel=RNAseqData,
        myfields=('locus', 'mean_rpkm', 'experiment',),
        myimport_id_fields=['locus', 'experiment'],
        mywidgets={'locus':
                   {'field': 'locus_tag'},}
    )
    
    filter_for_extended_form = {'experiment_method': 'rnaseq'}
    
    list_display = ('locus', 'mean_rpkm',)
    search_fields = ('locus__locus_tag',)
    

@admin.register(ProteomeData)
class ProteomeDataAdmin(DataAdmin):
    resource_class = disbiresource_factory(
        mymodel=ProteomeData,
        myfields=('locus', 'fold_change', 'adjusted_p_value',
                  'unique_peptides', 'experiment',),
        myimport_id_fields=['locus', 'experiment'],
        mywidgets={'locus': 
                   {'field': 'locus_tag'},}
    )
    filter_for_extended_form = {'experiment_type': 'proteome'}
    list_display = ('locus', 'fold_change', 'adjusted_p_value',)
    search_fields = ('locus__locus_tag',)
    
    
BaseFluxResource = disbiresource_factory(
    mymodel=FluxData,
    myfields=('reaction', 'flux', 'flux_min',
              'flux_max', 'experiment',),
    myimport_id_fields=['reaction', 'experiment'],
    mywidgets={'reaction':
               {'field': 'name'},}
) 
 
    
class FluxResource(dataframe_replace_factory(('inf', '1000')), BaseFluxResource):
    """
    Child with functionality to replace inf values and the standard
    Import/Export model resource.
    """    
    pass
    

@admin.register(FluxData)
class FluxAdmin(DataAdmin):
    resource_class = FluxResource
    
    filter_for_extended_form = {'experiment_type': 'flux'}
    
    list_display = ('reaction', 'flux', 'flux_min', 'flux_max',)
    search_fields = ('reaction__reaction_equation', 'reaction__name',)
    
    
@admin.register(GCMSData)
class GCMSAdmin(DataAdmin):    
    resource_class = disbiresource_factory(
        mymodel=GCMSData,
        myfields=('derivative_group', 'mean', 'experiment',),
        myimport_id_fields=['derivative_group', 'experiment'],
        mywidgets={'derivative_group':
                   {'field': 'name'},}
    ) 
    
    filter_for_extended_form = {'experiment_method': 'gcms'}
    
    list_display = ('derivative_group', 'mean', 'experiment',)
    
    
@admin.register(CoAData)
class CoADataAdmin(DataAdmin):    
    resource_class = disbiresource_factory(
        mymodel=CoAData,
        myfields=('co_a_derivative', 'mean', 'experiment',),
        myimport_id_fields=['co_a_derivative', 'experiment'],
        mywidgets={'co_a_derivative':
                   {'field': 'name'},}
    ) 
    
    filter_for_extended_form = {'experiment_method': 'coa'}
    
    list_display = ('co_a_derivative', 'mean', 'experiment',)


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'c_source_display',)
    ordering = ('experiment_type', 'experiment_method',)
    list_filter = ('experiment_type', 'experiment_method',)
    save_as = True # Allow to use existing object as template for new one.
    save_as_continue = False
    

admin.site.register(RawData)
