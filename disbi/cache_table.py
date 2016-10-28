"""
Handles the caching of joined tables in the DB.
"""
# Django
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

# DISBi
from disbi.db_utils import exec_query, from_db
from disbi.join import Relations
from disbi.models import BiologicalModel, Checksum, MeasurementModel, MetaModel
from disbi.option_utils import get_models_of_superclass


def reconstruct_backbone_table(app_label):
    """
    Reconstruct the prejoined backbone table of the biological models.
    """
    # Use the Relations class to do the JOIN.
    relations = Relations(app_label, model_superclass=(BiologicalModel, MetaModel))
    relations.start_join()
    relations.create_joined_table()        
        
def get_table_names_by_pattern(pattern):
    """
    Get all tables from DB that match a pattern.
    
    Args:
        pattern (str): An SQL string or pattern with placeholders.
    
    Returns:
        tuple: The matched table names.
    """
    select_query = '''
    SELECT tablename 
    FROM pg_catalog.pg_tables
    WHERE tablename LIKE '%s';
    ''' % pattern
    return from_db(select_query, fetch_as='tuple')

def drop_datatables(app_label):
    """
    Drop all cached datatables.
    
    Args:
        app_label (str): The name of the app the tables belong to.
    """
    # Construct the pattern that matches all datatables.
    pattern = '%s_%s_%%' % (app_label, settings.DISBI['DATATABLE_PREFIX'])
    dbtables = get_table_names_by_pattern(pattern)
    drop_query = "DROP TABLE %s;"
    # Flatten
    dbtables = sum(dbtables, ())
    # Drop all tables that matched the pattern.
    for tablename in dbtables:
        exec_query(drop_query % tablename)

def check_table(dbtables):
    """
    Check whether DB tables changed since the last time.
    
    Args:
        dbtables (iterable of str): The tables that should be checked.
        
    Returns:
        bool: True if at least one table changed, else False.
    """
    # Construct the query to get a checksum of a table denpending on the RDBMS.
    checksum_query = '''
    SELECT        
    md5(CAST((array_agg(t.* order by id)) AS text)) AS Checksum /* id is a primary key of table (to avoid random sorting) */
    FROM %s t; 
    ''' 
    # Initialize value to False.
    data_changed = False
    # Got through all tables and update the checksums. 
    # Set data_changed to True in case data changed.
    for dbtable in dbtables:
        # Get the checksum of the table.
        check = from_db(checksum_query % dbtable, fetch_as='namedtuple')[0]
        new_checksum = check.checksum

        try:
            # Get the old checksum from the DB.
            old_check = Checksum.objects.get(table_name=dbtable)
            if old_check.checksum != new_checksum:
                # If checksum changed, store the new checksum in the DB 
                # for later comparision and set `data_changed` to True.
                old_check.checksum = new_checksum
                old_check.save()
                data_changed = True
                
        except ObjectDoesNotExist:
            # No DB entry yet. Make the DB entry of the checksum and assume 
            # that data has changed.  
            Checksum.objects.create(table_name=dbtable, checksum=new_checksum)
            data_changed = True
    
    return data_changed    
        

def check_for_table_change(exp_model, check_for):
    """
    Wrapper for checking whether data in DB tables has changed.
    
    Args:
        check_for (str): Either ``bio`` for checking all tables that
            belong to :class:`.BiologicalModel` or ``data`` for checking
            all tables that belong to :class:`MeasurementModel`.
    """
    app_label = exp_model._meta.app_label
    # Get all models that belong to the appropriate superclasses.
    if check_for == 'bio':
        models = get_models_of_superclass(app_label, (BiologicalModel, MetaModel),
                                          intermediary=True)
    elif check_for == 'data':
        models = get_models_of_superclass(app_label, (MeasurementModel,),
                                          intermediary=True)
    else:
        raise ValueError('Unknown argument: {}'.format(check_for))
    dbtables = tuple(model._meta.db_table for model in models)
    # Check whether data has actually changed.
    data_changed = check_table(dbtables)
    # Call the appropriate function in case data did change.
    if data_changed:
        print('db changed, table is rejoined: ', check_for )
        # Call the reconstruct callback function.
        if check_for == 'bio':
            reconstruct_backbone_table(app_label)
            drop_datatables(app_label)
        elif check_for == 'data':
            drop_datatables(app_label)
