"""
Normal Django models with a few custom options for configuration.

If you have custom model classes that need these options, add them here and
create a child class of the appropriate options class and your custom model class.
"""
# Django
from django.db import models


class Options():

    def __init__(self, di_show=False, di_display_name=None, di_hr_primary_key=False,
                 di_choose=False, di_combinable=False,
                 *args, **kwargs):
        """
        Custom options for DISBi fields.
        
        Args:
            di_show (bool): Determines whether the column should be 
                included in the result table.
            di_display_name (str): Will be used as column header in the result table.
            di_hr_primary_key (bool): Determines whether the column should
                be used for identifying rows. If true column must be unique
                and may not be `null` or `blank`. Only one di_hr_primary_key
                is allowed per model.
                TODO: enforce this 
        """
        
        self.di_show = di_show
        self.di_display_name = di_display_name
        self.di_hr_primary_key = di_hr_primary_key
        self.di_choose = di_choose
        self.di_combinable = di_combinable
        super().__init__(*args, **kwargs)
  
        
class RelationshipOptions():

    def __init__(self, to, di_show=False, di_display_name=None, di_hr_primary_key=False,
                 di_choose=False, di_combinable=False,
                 *args, **kwargs):
        """
        Custom options for DISBi relationship fields, which have a different 
        signature than normal fields.
        
        Args:
            di_show (bool): Determines whether the column should be 
                included in the result table.
            di_display_name (str): Will be used as column header in the result table.
            di_hr_primary_key (bool): Determines whether the column should
                be used for identifying rows. If true column must be unique
                and may not be `null` or `blank`. Only one di_hr_primary_key
                is allowed per model.
                TODO: enforce this
            
        """
        
        self.di_show = di_show
        self.display_name = di_display_name
        self.di_hr_primary_key = di_hr_primary_key
        self.di_choose = di_choose
        self.di_combinable = di_combinable
        super().__init__(to, *args, **kwargs)
        

class ExcludeOptions(Options):
    """
    Adds the `exclude` option, to exclude rows where this field 
    evaluates to `False`. Should be only used on Bool fields.
    """
    def __init__(self, di_exclude=False, di_show=False, di_display_name=None, 
                 di_hr_primary_key=False, di_choose=False, di_combinable=False,
                 *args, **kwargs):
        self.di_exclude = di_exclude
        super().__init__(di_show, di_display_name, di_hr_primary_key, di_choose, 
                         di_combinable
                         *args, **kwargs)

class FloatField(Options, models.FloatField):
    """
    FloatField with custom DISBi options.
    """
    pass


class BigIntegerField(Options, models.BigIntegerField):
    """
    BigIntegerField with custom DISBi options.
    """
    pass


class BinaryField(Options, models.BinaryField):
    """
    BinaryField with custom DISBi options.
    """
    pass


class CommaSeparatedIntegerField(Options, models.CommaSeparatedIntegerField):
    """
    CommaSeparatedIntegerField with custom DISBi options.
    """
    pass


class CharField(Options, models.CharField):
    """
    CharField with custom DISBi options.
    """
    pass


class DateField(Options, models.DateField):
    """
    DateField with custom DISBi options.
    """
    pass


class DateTimeField(Options, models.DateTimeField):
    """
    DateTimeField with custom DISBi options.
    """
    pass


class DecimalField(Options, models.DecimalField):
    """
    DecimalField with custom DISBi options.
    """
    pass
    

class DurationField(Options, models.DurationField):
    """
    DurationField with custom DISBi options.
    """
    pass


class EmailField(Options, models.EmailField):
    """
    EmailField with custom DISBi options.
    """
    pass


class FileField(Options, models.FileField):
    """
    FileField with custom DISBi options.
    """
    pass


class FilePathField(Options, models.FilePathField):
    """
    FilePathField with custom DISBi options.
    """
    pass


class ImageField(Options, models.ImageField):
    """
    ImageField with custom DISBi options.
    """
    pass  


class IntegerField(Options, models.IntegerField):
    """
    IntegerField with custom DISBi options.
    """
    pass 


class GenericIPAddressField(Options, models.GenericIPAddressField):
    """
    GenericIPAddressField with custom DISBi options.
    """
    pass 


class PositiveIntegerField(Options, models.PositiveIntegerField):
    """
    PositiveIntegerField with custom DISBi options.
    """
    pass 


class PositiveSmallIntegerField(Options, models.PositiveSmallIntegerField):
    """
    PositiveSmallIntegerField with custom DISBi options.
    """
    pass 


class SlugField(Options, models.SlugField):
    """
    SlugField with custom DISBi options.
    """
    pass 


class SmallIntegerField(Options, models.SmallIntegerField):
    """
    SmallIntegerField with custom DISBi options.
    """
    pass 

    
class TextField(Options, models.TextField):
    """
    TextField with custom DISBi options.
    """
    pass


class TimeField(Options, models.TimeField):
    """
    TimeField with custom DISBi options.
    """
    pass


class URLField(Options, models.URLField):
    """
    URLField with custom DISBi options.
    """
    pass


class UUIDField(Options, models.UUIDField):
    """
    UUIDField with custom DISBi options.
    """
    pass


class ForeignKey(RelationshipOptions, models.ForeignKey):
    """
    ForeignKey with custom DISBi options.
    """
    pass

    
class ManyToManyField(RelationshipOptions, models.ManyToManyField):
    """
    ManyToManyField with custom DISBi options.
    """
    pass


class OneToOneField(RelationshipOptions, models.OneToOneField):
    """
    OneToOneField with custom DISBi options.
    """
    pass


class NullBooleanField(ExcludeOptions, models.NullBooleanField):
    """
    NullBooleanField with custom DISBi and exclude options.
    """
    pass


class BooleanField(ExcludeOptions, models.BooleanField):
    """
    BooleanField with custom DISBi and exclude options.
    """
    pass


class EmptyCharField(Options, models.CharField):
    """
    FloatField with custom DISBi options and the option to add an 
    empty value displayer.
    """
    
    def __init__(self, di_empty=None, di_show=True, di_display_name=None, di_hr_primary_key=False, 
                di_choose=False, di_combinable=False,
                 *args, **kwargs):
        self.di_empty = di_empty
        super().__init__(di_show, di_display_name, di_hr_primary_key, di_choose, di_combinable,
                         *args, **kwargs)
