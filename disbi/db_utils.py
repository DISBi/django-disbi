"""
Helper functions for performing operations circumventing the ORM layer.
"""
# standard library
from collections import OrderedDict, namedtuple

# Django
from django.db import connection


# see https://docs.djangoproject.com/en/1.9/topics/db/sql/
def dictfetchall(cursor):
    """Return all rows from a cursor as a dict."""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def namedtuplefetchall(cursor):
    """Return all rows from a cursor as a namedtuple."""
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]

def ordereddictfetchall(cursor):
    """Return all rows from a cursor as an OrdredeDict."""
    columns = [col[0] for col in cursor.description]
    return [
        OrderedDict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def from_db(sql, parameters=None, fetch_as='ordereddict'):
    """
    Fetch values from the DB, given a SQL query.
    
    Args:
        sql (str): The SQL statement.
    
    Keyword Args:
        parameters: Parameters for a parametrized query. If given `sql`
            must contain the appropriate palceholders. Defaults to None.
        fetch_as (str): The data type as which the values should be fetched.
            Choices are 'ordereddict', 'dict', 'namedtuple' and 'tuple'.
    
    Raises:
        ValueError: If a unrecognized value for ``fetch_as`` is given.
    """ 
    with connection.cursor() as cursor:
        if parameters is not None:
            cursor.execute(sql, parameters)
        else:
            cursor.execute(sql)
        if fetch_as == 'ordereddict':
            rows = ordereddictfetchall(cursor)
        elif fetch_as == 'dict':
            rows = dictfetchall(cursor)
        elif fetch_as == 'namedtuple': 
            rows = namedtuplefetchall(cursor)
        elif fetch_as == 'tuple':
            rows = cursor.fetchall()
        else:
            raise ValueError('Values cannot be fetched as {fetch_type}. '
                             .format(fetch_type=fetch_as) +
                             'Choices are \'ordereddict\', \'dict\', \'namedtuple\' and \'tuple\'.')
    
    return rows           

def exec_query(sql, parameters=None):
    """
    Execute a plain SQL query.
    
    Use parameterized query if parameters are given.
    
    Args:
        sql (str): The SQL query.
    
    Keyword Args:
        parameters (iterable): An iterable of parameters, that will be autoescaped.
    """
    with connection.cursor() as cursor:
        if parameters is not None:
            cursor.execute(sql, parameters)
        else:
            cursor.execute(sql)

def db_table_exists(table_name):
    """
    Check whether a table with a specific name exists in the DB.
    
    Args:
        table_name (str): The name of the table to check for.
        
    Returns:
        bool: True if the table exists, else False.
    """
    return table_name in connection.introspection.table_names()

def get_columnnames(table_name):
    """
    Get the column names of a DB table.
    
    Args:
        table_name (str): The name of the table.
        
    Returns:
        tuple: The column names.
    """
    query = """
    SELECT *
    FROM %s 
    LIMIT 1""" % table_name    
    row = from_db(query, fetch_as='namedtuple')
    return row[0]._fields

def get_m2m_field(intermediary_model, related_model):
    """
    Get the field of an intermediary model, that constitutes the
    relation to `related_model`.
    """
    fields = [field for field 
              in intermediary_model._meta.get_fields()
              if field.concrete]
       
    for field in fields:
        if getattr(field, 'target_field', False):
            if field.target_field.model == related_model:
                return field


def get_pk_query_name(model):
    """Format the primary key column of a model with its DB table."""
    return '%s.%s' % (model._meta.db_table, model._meta.pk.column)

def get_fk_query_name(model, related_model):
    """
    Format the DB column name of a foreign key field of a model
    with the DB table of the model. Finds the foreign key relating to 
    related model automatically, but assumes that there is only one related field.
    
    Args:
        model (Model): The model for which the foreign key field is searched.
        related_model (Model): A model related to `model`.
    
    Returns:
        str: The formated foreign key column name.
    """
    related_field = [f for f in model._meta.get_fields()
                     if f.is_relation and f.concrete and f.related_model == related_model]
    return '%s.%s' % (model._meta.db_table, related_field[0].column)

def get_field_query_name(model, field):
    """Format the DB column name of a field with the DB table of its model."""
    return '%s.%s' % (model._meta.db_table, field.column)
