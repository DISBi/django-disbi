"""
Contains the class Relations that stores relations between models
and joins them together appropriately.
"""
# standard library
from collections import deque
from itertools import product

# Django
from django.apps import apps
from django.conf import settings
from django.db import connection, models

# DISBi
from disbi.db_utils import (exec_query, get_field_query_name,
                            get_fk_query_name, get_m2m_field,
                            get_pk_query_name)
from disbi.models import MetaModel
from disbi.option_utils import get_models_of_superclass


class Relations():
    """
    Stores relations of models and has the ability to join them.
    """
    # pylint: disable=too-many-instance-attributes
    # Eight is reasonable in this case.
    def __init__(self, app_label, model_superclass=None):
        """
        Initialize Relations.
        
        Args:
            app_label (str): The label of the app the models live in.
            model_superclass (iterable of type): The classes from which 
                all models of interest derive. Defaults to None.
        """
        self.app_label = app_label
        self.relation_map = self._construct_relation_map(model_superclass)
        self.sql = ''
        self.m2m_count = 0

    def _construct_relation_map(self, model_superclass):
        """
        Store the relations bewteen models in a 2-D hashmap.
        
        Args: 
        model_superclass (iterable of type): The classes from which 
                all models of interest derive.
                
        Returns:
            dict: A 2-D hashmap where either the ForeignKey field,
            the intermediary model or False is stored for each two
            models. Depending on whether their relation is 1:N, N:M or 
            they have no relation.
        """
        if model_superclass is not None:
            self.models = get_models_of_superclass(self.app_label, model_superclass)
        else:
            self.models = apps.get_app_config(self.app_label).get_models()
        
        # Use dict as hashmap for adjacency matrix.
        relation_map = dict((t, None) for t in product(self.models, self.models))
        # Set model pairs that have no realtion to False.
        for pair in relation_map.keys():
            model_a, model_b = pair
            # If the pair is a mapping to itself, set entry to False.
            if model_a == model_b:
                relation_map[pair] = False
                continue
            # Introspect relation between the two models.
            model_a, model_b = pair
            # Get concrete relationship fields.
            relation_fields = [f for f in model_a._meta.get_fields()
                               if f.is_relation and f.concrete]
            for field in relation_fields:
                if field.related_model == model_b:
                    # Set the relation in both directions, so it does not 
                    # matter how it is specified in models.py.
                    if field.many_to_many:
                        relation_map[pair] = field.remote_field.through
                    elif field.many_to_one:
                        relation_map[pair] = field
                    relation_map[tuple(reversed(pair))] = relation_map[pair]
            # If nothing has been found set relation to False.
            if relation_map[pair] is None:
                relation_map[pair] = False

        return relation_map
    
    #TODO: could be refactored with later depth first search.
    @property
    def is_tree(self):
        """
        Determine whether the relation_map is a tree.
        
        Perform some setup and then call the depth first search, starting 
        from an arbitrary node.
        
        Returns:
            bool: True if the graph is a tree. If it contains at least on cycle
            or is not connected, return False.
            
        """
        self.nodes = self.models
        self.visited = set()
        start = self.nodes[0]
        
        cyclic = self._df_search(start, None)
        connected = (self.visited == set(self.nodes))
        
        return (not cyclic and connected)
          
    def _df_search(self, current, parent):
        """
        Depth first search for cycles in a relation map.
        
        Args:
            current: The node that is searched in this function call.
            parent: The node from which the current node was called as child.
            
        Returns:
            bool: True if the graph contains at least on cycle, else False.
        """
        # Find all childs of the node.
        childs = set()
        for node in self.nodes:
            if (node is not parent and
            node is not current and 
            self.relation_map[current, node]):
                childs.add(node)
        # Check if one of the childs was already visited, which would 
        # denote a cycle.
        for child in childs:
            if child in self.visited:
                return True
        # Now the node has been checked and can be added to the
        # visited set.
        self.visited.add(current)
        # Search each child node recursively.
        for child in childs:
            if self._df_search(child, current):
                return True 
        return False
        
    def get_related_metamodels(self, model):
        """
        Get all models related to ``model`` of a superclass.
        """
        possible_relatives = get_models_of_superclass(self.app_label, (MetaModel,))
        related_models = []
        models_to_search = [model,]
        visited = set()
        
        while models_to_search:
            searched_model = models_to_search.pop()
            children = self._get_children(searched_model, 
                                          possible_relatives, visited)
            related_models.extend(children)
            models_to_search.extend(children)
            visited.add(searched_model)
        
        return related_models
            
    def _get_children(self, parent, group, visited):
        """
        Get all children of a parent model in a specific group of models.
        
        Args:
            parent (Model): The model for which the childs are searched.
        
        Returns:
            set: All child models of the parent model.
        """
        children = []
        for model in group:
            if (model is not parent and 
            model not in visited and
            self.relation_map[parent, model]):
                children.append(model)
        return children
        
        
        
        
    
    def start_join(self):  
        """
        Start the join process between all models.
        """
        # Confirm that DB backend is Postgres.
        if not connection.vendor == 'postgresql':
            raise ValueError('Database system {} not supported. Use PostgreSQL.'.format(connection.vendor))
        # First check whether the graph formed by the relation_map
        # is actually a tree.
        if not self.is_tree:
            raise ValueError('The graph formed by the relationships of the ' 
                             'models is no tree.')
        # list that stores all models in a linear order,
        # determining the order the columns are displayed in the end.
        self.linearized = []
        # Get the model that was set as the root of the relation tree.
        for model in self.models:
            if getattr(model, 'di_first', False):
                first = model
                break
        self.linearized.append(first)
        
        # Construct the from statement with the root model.
        self._construct_SQL(first)
        
        # Start the JOIN.
        self._join(first)
        
        # Add the select clause.
        self.sql = self._construct_SELECT() + self.sql
        
        
    def _join(self, model):
        """
        Depth first, ForeignKey first traversal trough the relation tree.
        
        Construct the appropriate SQL JOIN statement for each child 
        of the model. Then call the function directly for each child.
        
        Args:
            model (Model): The current model in the traversal. 
        """
                
        childs = self._get_prioritized_childs(model)
        for child in childs:
            self._construct_SQL(model, child)
            self.linearized.append(child)
            self._join(child)
            
    def _get_prioritized_childs(self, parent):
        """
        Get all childs of a model. Prioritize ForeignKeys over ManyToMany relations.
        
        Args:
            parent (Model): The model for which the childs are searched 
                and prioritized.
        Returns:
            deque: All child models of the parent model.
            N:1 related models first, N:M related models last.
        """
        childs = deque()
        for model in self.models:
            if (model not in self.linearized and 
            self.relation_map[(parent, model)]):
                if isinstance(self.relation_map[(parent, model)], models.ForeignKey):
                    childs.appendleft(model)
                else:
                    childs.append(model) 
        return childs
    
    def _construct_SQL(self, model_a, model_b=None):
        """
        Construct SQL statement for JOINing two models depending on their relation.
     
        Args:
            model_a (Model): The model that comes first in the JOIN statement.
            model_a (Model): The model that comes second in the JOIN statement.
                Defaults to None.
        """
        # If only one model is given, it is the start of the SQL statement.
        # Insert the model in a FROM clause.
        if model_b is None:
            sql = '''
            FROM %s
            ''' % model_a._meta.db_table
        # Two models are given, a JOIN clause is required.
        else:                
            sql = self._construct_PostgreSQLJOIN(model_a, model_b)
            
        # Add the newly constructed SQL to the models attribute.
        self.sql += sql
        
    def _construct_PostgreSQLJOIN(self, model_a, model_b):
        """
        Construct SQL statement for JOINing two N:M related models
        in PostgreSQL dialect.
        
        Args:
            model_a (Model): The model that comes first in the JOIN statement.
            model_a (Model): The model that comes second in the JOIN statement.
            intermediary_model (Model): The model mediating the N:M relation
                between model_a and model_b.
        Returns:
            str: The constructed SQL JOIN statement. 
        """
        # When dealing with a N:1 relation a FULL JOIN with the other model
            # is sufficient.
        if isinstance(self.relation_map[(model_a, model_b)], models.ForeignKey):
            sql = '''
            FULL JOIN %s
            ON %s = %s
            ''' % (model_b._meta.db_table,
                   get_fk_query_name(model_a, model_b), get_pk_query_name(model_b),
                )
            
        # When dealing with a N:M relation a FULL JOIN spanning
        # the intermediary model is required.
        elif issubclass(self.relation_map[(model_a, model_b)], models.Model):
            intermediary_model = self.relation_map[(model_a, model_b)]

            # When dealing with a N:M relation a FULL JOIN spanning
            # the intermediary model is required.
            intermediary_model = self.relation_map[(model_a, model_b)]
            sql = '''
            FULL JOIN %s
            ON %s = %s
            FULL JOIN %s
            ON %s = %s 
            ''' % (intermediary_model._meta.db_table,
                   get_pk_query_name(model_a), 
                        get_field_query_name(intermediary_model, 
                                             get_m2m_field(intermediary_model, model_a)),
                   model_b._meta.db_table,
                   get_field_query_name(intermediary_model, 
                                        get_m2m_field(intermediary_model, model_b)), 
                        get_pk_query_name(model_b),
                )
        
        else:
            raise ValueError('Unsupported relation. The relation between {} and {} is neither ForeignKey nor ManyToMany.'. format(model_a, model_b))
        
        
        return sql
        
    def _construct_directions(self, num):
        """
        Return a list of lists of directions needed for a FULL OUTER JOIN of 
        `num` N:M related tables. Moving from LEFT to RIGHT.
         
        Args:
            num (int): The number of tables to be joined together.
         
        Returns:
            list of lists of str: The directions by which the tables 
                have to be joined together.
        """
        if num < 2:
            err_msg = 'Tried to join {number} tables. Less than 2 tables cannot be joined.'
            raise ValueError(err_msg.format(number=num))
        directions = []
        num += 1
        for i in range(1, num+1):
            left = num - i
            right = num - 1 - left
            directions.append(((['RIGHT'] * right) + ['LEFT'] * left))
        return directions
            
    def _format_direction(self, direction):
        """
        Return a tuple were each entry of a list is duplicated.
         
        This is done because the direction of a join spans two tables, 
        the intermediary and the the related table, in N:M relations.
         
        Args:
            direction (list): A list of strings of the direction needed for
                one UNION statement.
         
        Returns:
            tuple:  Each entry of directions list duplicated.
        """
        duplicated_direction = tuple((lr, lr) for lr in direction)
        return sum(duplicated_direction, ())
    
    def _construct_SELECT(self):
        """
        Construct the SELECT clause for the SQL JOIN.
        
        The order of the SELECTed models is based on the order in
        that they were linerized.
        """
        column_names = (self._get_column_names(model) for model in self.linearized)
        # Flatten 
        column_names = sum(column_names, [])
        select_stmt = 'SELECT DISTINCT %s' % ', '.join(column_names)
        return select_stmt 

    def _get_column_names(self, model):
        """
        Get the DB column names for the fields of a MeasurementModel of an experiment.
        
        Args:
            model (Model): The model.
        
        Returns:
            list: A list of strings containing the display names.
        """
        # Construct the id column name as 'modelname_id'
        column_names = [
                        '%s.%s AS %s_%s' % (model._meta.db_table, model._meta.pk.column,
                                         model.__name__.lower(), model._meta.pk.column)
                       ]
        # Add all columns where `show` is True. 
        column_names += [
                            self._as_display_name(model, field)
                            for field in model._meta.get_fields() 
                            if getattr(field, 'di_show', False)
                        ]

        return column_names
    
    def _as_display_name(self, model, field):
        """
        Get the name by which a model field should be fetched from the 
        DB. Either as the plain name as an AS statement with the display_name.
        
        Args:
            model (Model): The model class.
            field (Field): The field class of the model.
            
        Returns:
            str: The DB name of the field or an AS statement with its display
            name.
         
        """
        display_name = getattr(field, 'di_display_name', False)
        if display_name:
            return '%s.%s AS %s' % (model._meta.db_table, field.column, display_name)
        else:
            return field.column
        
    
    def create_joined_table(self):
        """
        Execute the the SQL JOIN and create a table thereof. 
        """
        table_name = '%s_%s' % (self.app_label, settings.DISBI['JOINED_TABLENAME'])
        exec_query('DROP TABLE IF EXISTS %s;' % table_name)
        sql = '''
        CREATE TABLE %s AS
        %s
        ''' % (table_name,
               self.sql)
        exec_query(sql)
