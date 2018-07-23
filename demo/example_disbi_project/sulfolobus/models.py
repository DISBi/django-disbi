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


# If fieldnames are ambiguous between different biological tables, use
# di_display_name on those fields.

class Pathway(MetaModel):
    name = dmodels.CharField(max_length=255, unique=True, di_show=True,
                             di_display_name='pathway')
    reaction = dmodels.ManyToManyField('Reaction', related_name='reactions')
    
    def __str__(self):
        return self.name

class Locus(BiologicalModel):
    di_first = True
    locus_tag = dmodels.CharField(max_length=255, unique=True, di_show=True)
    product = dmodels.CharField(max_length=255, di_show=True, blank=True)
    ec_number = ArrayField(
                    dmodels.CharField(max_length=15, blank=True,
                                      validators=[ec_validator]),
                    blank=True, verbose_name='EC number'
                )
    reaction = dmodels.ManyToManyField('Reaction', related_name='loci')
    
    class Meta:
        verbose_name_plural = "loci"

    def __str__(self):
        try:
            return '{} -- {}'.format(self.locus_tag, self.gene.product)
        except:
            return '{}'.format(self.locus_tag)
        

class Reaction(BiologicalModel):
    name = dmodels.CharField(max_length=255, unique=True, di_show=True,
                             di_display_name='reaction_name')
    reaction_equation = dmodels.TextField()
    lb = dmodels.FloatField(null=True, blank=True)
    ub = dmodels.FloatField(null=True, blank=True)
    brenda = dmodels.CharField(max_length=13, blank=True)
    kegg = dmodels.CharField(max_length=10, blank=True, di_show=True)
    metacyc = dmodels.CharField(max_length=100, blank=True)
    pubmed = dmodels.CharField(max_length=12, blank=True)
    notes = dmodels.TextField(blank=True)
    metabolite = dmodels.ManyToManyField('Metabolite', related_name='reactions')#, through='ReactionMetabolite')
    
    def __str__(self):
        """Return equation and database ID if exists in specified order."""
        allowed_length = 30
        if self.brenda:
            return self.brenda
        elif self.metacyc:
            return self.metacyc
        elif self.kegg:
            return self.kegg
        else:
            if len(self.reaction_equation) < allowed_length:
                return self.reaction_equation
            else:
                return self.reaction_equation[:30] + '[...]'
        
    @property
    def brendalink(self):
        if self.brenda:
            prefix = self.brenda[:2]
            refid = self.brenda[2:]
            link = '<a href="http://www.brenda-enzymes.org/structure.php?show=reaction&id={}&type={}&displayType=marvin">{}</a>'
            if prefix == 'BS':
                return format_html(link, mark_safe(refid), mark_safe('S'), self.brenda)
            elif prefix == 'BR':
                return format_html(link, mark_safe(refid), mark_safe('I'), self.brenda)
        else:
            return None    
    
    @property
    def kegglink(self):
        if self.kegg:
            link = '<a href="http://www.genome.jp/dbget-bin/www_bget?rn:{}">{}</a>'
            return format_html(link, mark_safe(self.kegg), self.kegg)
        else:
            return None
    
    @property
    def metacyclink(self):
        if self.metacyc:
            link = '<a href="http://metacyc.org/META/NEW-IMAGE?type=NIL&object={}&redirect=T">{}</a>'
            return format_html(link, mark_safe(self.metacyc), self.metacyc)
        else:
            return None

    @property
    def db_crossref(self):
        return (self.brendalink or self.kegglink or
               self.metacyclink or 'No cross reference found.')
    
    @property
    def short_reaction(self):
        allowed_length = 30
        if len(self.reaction_id < allowed_length):
            return self.reaction_id
        else:
            return self.reaction_id[:30] + '[...]'

class Metabolite(BiologicalModel):
    name = dmodels.CharField(max_length=512, di_display_name='metabolite_name', 
                             di_show=True)
    derivative_group = dmodels.ForeignKey('DerivativeGroup', null=True, blank=True)
    co_a_derivative = dmodels.ForeignKey('CoADerivative', null=True, blank=True)
    
    def __str__(self):
        return self.name
        
class DerivativeGroup(BiologicalModel):
    name = dmodels.CharField(max_length=600, unique=True, di_show=True, 
                             di_display_name='derivative_group')

    def __str__(self):
        return self.name


class CoADerivative(BiologicalModel):
    name = dmodels.CharField(max_length=600, unique=True, di_show=True, 
                             di_display_name='CoA_derivative')
                             
    class Meta:
        verbose_name_plural = 'CoA derivatives'
    
    def __str__(self):
        return self.name
    
# ------------------------ experimental models ------------------------

## --------------------------- data models ----------------------------

class ExperimentalData(MeasurementModel): 
    mean = dmodels.FloatField(di_show=True)
    
    class Meta:
        abstract = True
        
        
class TranscriptomeData(MeasurementModel):
    locus = dmodels.ForeignKey('Locus', on_delete=models.PROTECT)

    class Meta:
        abstract = True
        unique_together = (('locus', 'experiment'),)
    
    def __str__(self):
        try:
            return '{}: {:10.2f}'.format(self.transcript.transcript_identifier,
                                        self.mean_rpkm)
        except:
            return '{}'.format(self.mean_rpkm)
        
    
class RNAseqData(TranscriptomeData):
    mean_rpkm = dmodels.FloatField(di_show=True)

    class Meta:
        verbose_name_plural = 'RNASeq data'

        
class ProteomeData(MeasurementModel):
    locus = dmodels.ForeignKey('Locus', on_delete=models.PROTECT)
    fold_change = dmodels.FloatField(di_show=True)
    adjusted_p_value = dmodels.FloatField(di_show=True, 
                                          validators=[validate_probabilty])
    unique_peptides = dmodels.IntegerField()
    
    class Meta:
        unique_together = (('locus', 'experiment'),)
        verbose_name_plural = 'Proteom data'
                
    def __str__(self):
        return 'Proteome Datapoint'


class FluxData(MeasurementModel):
    flux = dmodels.FloatField(di_show=True, validators=[validate_flux])
    flux_min = dmodels.FloatField(di_show=True, di_display_name='lb', 
                                     validators=[validate_flux])
    flux_max = dmodels.FloatField(di_show=True, di_display_name='ub',
                                     validators=[validate_flux])
    
    reaction = dmodels.ForeignKey('Reaction', on_delete=models.CASCADE)

    class Meta:
        unique_together = (('reaction', 'experiment',))
        verbose_name_plural = 'Fluxes'
        
    def __str__(self):
        return 'Flux datapoint'
    

class GCMSData(ExperimentalData):
    derivative_group = dmodels.ForeignKey('DerivativeGroup', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = (('derivative_group', 'experiment'),)
        verbose_name_plural = 'Metabolome GCMS data'
    
    def __str__(self):
        return 'Metabolome GCMS datapoint'
    
    
class CoAData(ExperimentalData):
    co_a_derivative = dmodels.ForeignKey('CoADerivative', on_delete=models.PROTECT)
    stderr = dmodels.FloatField(null=True, blank=True, di_show=True)
    
    class Meta:
        unique_together = (('co_a_derivative', 'experiment'),)
        verbose_name_plural = 'CoA data'

    def __str__(self):
        return 'CoA datapoint'

class RawData(models.Model):
    """A raw data file."""
    data_file = dmodels.FileField()
    
    class Meta:
        verbose_name_plural = "Raw datasets"
    
    def __str__(self):
        return os.path.basename(self.data_file.name)
    
    
## information about experiments ----------------------------------------

class Experiment(models.Model, DisbiExperiment):
    EXPERIMENT_TYPE_CHOICES = (('transcriptome', 'Transcriptome'),
                               ('proteome', 'Proteome'),
                               ('metabolome', 'Metabolome'),
                               ('flux', 'Predicted Flux'),
                               ) 
    experiment_type = dmodels.CharField(max_length=45, 
                                       choices=EXPERIMENT_TYPE_CHOICES, 
                                       di_choose=True)
    # The first name is the DB name, the second is human readable.
    EXPERIMENT_METHOD_CHOICES = (
        ('Transcriptome', (
                ('rnaseq', 'RNAseq'),
            )
        ),
        ('Proteome', (
                ('shotgun', 'shotgun'),
            )
        ),                             
        ('Metabolome', (
                ('gcms', 'GCMS'),
                ('coa', 'CoA-method'),
            )
        ),
        ('Predicted Flux', (
                ('fba', 'FBA'),
            )
        ),
    )                            
    experiment_method = dmodels.CharField(max_length=45, 
                                         choices=EXPERIMENT_METHOD_CHOICES, 
                                         di_choose=True)
    c_source = dmodels.CharField(max_length=45, blank=True, 
                                 verbose_name='Carbon source', di_choose=True, 
                                 di_show=True, di_combinable=True)
    place = dmodels.CharField(max_length=45)
    group = dmodels.CharField(max_length=45)
    raw_data = dmodels.ForeignKey('RawData',
                                 help_text='A file with the raw data for the experiment')
    notes = dmodels.TextField(blank=True, default='')
    
    class Meta:
        unique_together = (('experiment_type', 'experiment_method',
                            'c_source', 'group', 'raw_data'),)
    
    def __str__(self):
        return '{}. {}: {}'.format(
                self.id,
                self.get_experiment_type_display(),
                self.get_experiment_method_display(), 
            ) 
        
    def clean(self):
        """
        Check whether the experiment method matches the experiment type.
        """
        opt_groups = get_optgroups(self.EXPERIMENT_METHOD_CHOICES)
        hr_experiment_type = get_hr_val(self.EXPERIMENT_TYPE_CHOICES,
                                        self.experiment_type)
        if self.experiment_method not in opt_groups[hr_experiment_type]:
            hr_experiment_method = get_hr_val(
                    remove_optgroups(self.EXPERIMENT_METHOD_CHOICES),
                    self.experiment_method
            )
            raise ValidationError(_('{type} does not belong to the method {method}.'.format(
                    type=hr_experiment_type, method=hr_experiment_method))
                )
    
    def c_source_display(self):
        return self.c_source if self.c_source else '-'
    c_source_display.short_description = 'Carbon source'
    
    
    #~ def result_view(self):
        #~ """
        #~ Return an OrderedDict that contains important imformation about the
        #~ experiment.
        #~ """
         #~ Truncate the filename if it is too long.
        #~ filename = os.path.basename(self.raw_data.data_file.name)
        #~ if len(filename) > 30:
             #~ parts[0] is the actual filename, parts[1] the extension.
            #~ parts = os.path.splitext(filename)
            #~ name = parts[0][:20] + '[...]'
            #~ filename = name + parts[1]

        #~ view = OrderedDict()
        #~ view['Name'] = self.__str__()
        #~ view['File'] = format_html('<a href="{}">{}</a>', 
                                   #~ mark_safe(self.raw_data.data_file.url), 
                                   #~ filename)
        #~ view['Carbon Source'] = self.c_source_display()
        
        #~ return view
    
        
class ExperimentMetaInfo(Experiment, DisbiExperimentMetaInfo):
     
    pass
