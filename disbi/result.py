"""
Class for getting the joined table with data based on a list of experiments.
"""
# standard library
import re

# third-party
from more_itertools import unique_everseen

# Django
from django.apps import apps
from django.conf import settings

# DISBi
from disbi.db_utils import (db_table_exists, exec_query, from_db,
                            get_columnnames)
from disbi.exceptions import NoRelatedMeasurementModel, NotFoundError
from disbi.join import Relations
from disbi.models import BiologicalModel, MetaModel
from disbi.utils import get_id_str, get_unique, sort_by_other


class DataResult():
    """Constructs the datatable based on the request from the filter view."""
    
# ---------------------- Static class attributes ----------------------
    # SQL function for scientifc formatting of floting point numbers and zero devision.
    DB_FUNCTION_ZERO = 'divide_without_zeroerr'
    DB_PRECISION = '\'9.9999EEEE\''
    
    

    def __init__(self, requested_experiments, experiment_meta_model):
        """
        Initialize a new DataResult object.
        
        Args:
            requested_experiments (iterable): The experiments that were
                requested in the interface.
        
        Raises:
            NoRelatedMeasurementModel: If an experiment was chooses for which 
                yet no data has been uploaded.
        """
        # Ensure that ExperimentMetaInfo is the type of all experiments.
        if not False in [isinstance(exp, experiment_meta_model) for exp in requested_experiments]: 
            self.req_exps = requested_experiments 
        else:
            self.req_exps = [experiment_meta_model.objects.get(pk=exp.pk) 
                             for exp in requested_experiments]
            
        self.app_label = experiment_meta_model._meta.app_label
        for exp in self.req_exps:
            if exp.measurementmodel is None:
                raise NoRelatedMeasurementModel(exp)
        
# -------------------------- Getter methods ---------------------------        
    def get_display_names(self, exp):
        """
        Get the display names for the columns of a MeasurementModel of an experiment.
        
        Args:
            exp (Experiment): The experiment.
        
        Returns:
            tuple: A tuple of strings containing the display names 
            suffixed by the experiment id.
        """
        alias = str(exp.id)
        column_display_names = [
                                field.di_display_name if field.di_display_name else field.name
                                for field in exp.measurementmodel._meta.get_fields() 
                                if getattr(field, 'di_show', False)
                                ]
        return tuple('%s_%s' % (name, alias) for name in column_display_names)
        
    def get_colnames(self, model):
        """
        Get a list of all DB columns with di_show=True.
        
        Args:
            model (models.Model): The model for which the fields are retrieved.
            
        Returns:
            list: A list of strings with the DB column names.
        """
        return [
                    field.column  
                    for field in model._meta.get_fields() 
                    if getattr(field, 'di_show', False)
                ]
                          
    def get_notnull_column(self, exp):
        """
        Get a column that can not be NULL and will be shown. 
        
        Args:
            exp (Experiment): The experiment for which the column 
                should be retrieved. 
        
        Returns:
            models.Field: The first field that will be shown and is neither 
                NULL or blank.
            
        Raises:
            NotFoundError
        """
        for field in exp.measurementmodel._meta.get_fields():
            if not field.null and not field.blank and field.di_show:
                return field.column
        raise NotFoundError('{experiment} has no column with di_show=True that is neither NULL nor blank.'
                            .format(experiment=exp))
    
    def get_show_columns(self, model):
        """
        Get a list of DB columns that should be shown in the result table.
        
        Args:
            model (models.Model): A Django model with custom DISBI options.
            
        Returns:
            list: List of strings containing the DB column names of the fields
            to be shown.
        """
        return [
                getattr(field, 'di_display_name', False) or field.column 
                for field in model._meta.get_fields() 
                if getattr(field, 'di_show', False)
                ]
    
    def construct_SELECT_AS(self, exp):
        """
        Construct part of a SQL statement for alias DB columns with their 
        display name.
        
        Args:
            exp (Experiment): The experiment.
        
        Returns:
            str: The partial statement for aliasing the columns.
        """
        display_names = self.get_display_names(exp)
        db_colnames = self.get_colnames(exp.measurementmodel)
        
        AS_stmt = ', '.join('%s AS %s' % (db_col, display_col) 
                            for db_col, display_col in zip(db_colnames, display_names))
        return AS_stmt
        
    def construct_exptable(self, exp):
        """
        Construct the subquery for producing selection of all data points
        mapping to one experiment.
        
        Only data points which foreign key matches the experiment will
        be selected. Data points for which an exclude column evaluates
        to False will be excluded.
        
        Args:
            exp (disbimodels.Experiment): The experiment for which the 
                data is selected.
        
        Returns:
            str: A SQL statement for the selection of the datapoints.
        """       
        
        # Statement for excluding the rows where fields with the option
        # exclude=True are False.
        exclude_fields = [field for field in exp.measurementmodel._meta.get_fields() 
                          if getattr(field, 'exclude', False)]
        exclude_columns = [field.column for field in exclude_fields]
        exclude_data = ' '.join(['AND %s IS NOT FALSE' % column for column in exclude_columns])
        
        sql = '''
            SELECT %s, %s 
            FROM %s
            WHERE %s = %s %s
        ''' % (self.construct_SELECT_AS(exp), exp.biofield.column,
               exp.measurementmodel._meta.db_table,
               exp.measurementmodel._meta.get_field('experiment').column, exp.id, exclude_data)
        return sql          
      
    def construct_result_table(self, biomodels):
        """
        Construct the SQL statement for getting the result table.
        
        For each biological model, the respective experiments will be filtered.
        For those experiments a subquery is constructed, that is then LEFT JOINed
        into the prejoined backbone table. Only rows that have at least one
        data point are preserved.
        
        Args:
            biomodels (list): List of Biological models.
        
        Returns:
            str: The SQL statement for the result table.
        """
        select = 'SELECT DISTINCT '
        cached_alias = 'c'
        join_exps = 'FROM %s_%s AS %s' % (self.app_label, 
                                          settings.DISBI['JOINED_TABLENAME'], 
                                          cached_alias)
        left_join_template = '''
        LEFT JOIN (
            %s
        ) AS %s
        ON (%s = %s)
        '''
        subtables_not_null_column = []
        select_bios = []
        relations = Relations(self.app_label, model_superclass=(BiologicalModel, MetaModel))
        for biomodel in biomodels:
            # Requested experiments related to biomodel.
            req_exps_for_bio = []    
            for exp in self.req_exps:
                if exp.biomodel == biomodel:
                    req_exps_for_bio.append(exp)
            
            select_bios.extend(self.get_show_columns(biomodel))
            

            # Get Meta models for Bio model and the show columns to the 
            # SELECT clause.
            metamodels_of_biomodel = relations.get_related_metamodels(biomodel)
            #print(metamodels_of_biomodel)
            for metamodel in metamodels_of_biomodel:
                select_bios.extend(self.get_show_columns(metamodel))

                
            for exp in req_exps_for_bio:
                select_bios.extend(self.get_display_names(exp))
                exp_alias = 'exp%s' % exp.pk
                join_exps += left_join_template % (
                    self.construct_exptable(exp),
                    exp_alias,
                    '%s.%s_id' % (cached_alias, biomodel.__name__.lower()),
                        '%s.%s' % (exp_alias, exp.biofield.column)
                    )
                subtables_not_null_column.append((self.get_notnull_column(exp), 
                                                  str(exp.id)))
        exclude_empty = 'WHERE ' + ' OR '.join(['%s_%s IS NOT NULL' % col 
                                             for col in subtables_not_null_column])
        
        sql = '\n'.join((select + ', '.join(select_bios), join_exps, exclude_empty))
        return re.sub(r'^\s+', '', sql, flags=re.MULTILINE) 
    
    def construct_base_table(self):
        """
        Construct the SQL statement for creating the base table.
        
        Returns:
            str: The SQL statement for creating the base table.
        """
        # Get requested biological entities.
        req_biomodels = [exp.biomodel for exp in self.req_exps]
        # Remove duplicates.
        req_biomodels = list(unique_everseen(req_biomodels))
        # Order according to the linearized models.
        relations = Relations(self.app_label, model_superclass=(BiologicalModel, MetaModel))
        relations.start_join()
        linearized_biomodels = relations.linearized
        req_biomodels = sort_by_other(req_biomodels, 
                                     order=linearized_biomodels)
        # Construct the SQL statement.
        sql = self.construct_result_table(req_biomodels)
        return sql
            
    def create_base_table(self, table_name):
        """
        Create the base table and write it to the DB.
        
        Args:
            table_name (str): The name under which the table should be created.
            
        Returns:
            None: This is a procedure.
        """
        print('new')
        # Create table at first.
        select_stm = self.construct_base_table()
        exec_query('DROP TABLE IF EXISTS %s;' % table_name) 
        sql = """
        CREATE TABLE %s AS
        %s
        """ % (table_name, select_stm)
        exec_query(sql) 
            
    def get_or_create_base_table(self, fetch_as='ordereddict'):
        """
        Retrieve the base table from the DB. Create it if it does not exist.
        
        Returns:
            The values fetched from the DB.
        """
        # Make a sorted list of all ids.
        exp_id_str = get_id_str(self.req_exps)
        table_name = '%s_%s_%s' % (self.app_label, 
                                    settings.DISBI['DATATABLE_PREFIX'], 
                                    exp_id_str)
        if not db_table_exists(table_name):
            self.create_base_table(table_name)
        column_names = list(get_columnnames(table_name))
        # Escape all column names.
        column_names = ['%s' % column_name for column_name in column_names]
        # Format all columns with scientific notation that end with underscore and a number.
        # These columns contain numerical data and should be presented in 
        # scientific notation.
        datacol_pattern = re.compile(r'_\d+$')
        for i, column_name in enumerate(column_names):
            if datacol_pattern.search(column_name) is not None:
                column_names[i] = '{} as {}'.format(self.wrap_in_func('to_char', 
                                                                  column_name, 
                                                                  self.DB_PRECISION),
                                                column_name)
        sql = 'SELECT %s FROM %s' % (', '.join(column_names), table_name)
        #return from_db(sql)
        return from_db(sql, fetch_as=fetch_as)
    
    def wrap_in_func(self, func, *cols):
        """
        Pass column names as arguments to DB function.
        """
        return '{func}({args})'.format(func=func,
                                       args=', '.join(cols))
    
    def add_foldchange(self, exps_for_fc, fetch_as='ordereddict'):
        """
        Add the fold change to a base table.
        """
        exp_id_str = get_id_str(self.req_exps)
        table_name = '%s_datatable_%s' % (self.app_label, exp_id_str)
        # Make experiment for fold change unique.
        exps_for_fc = get_unique(exps_for_fc)
        if not db_table_exists(table_name):
            self.create_base_table(table_name)
        column_names = list(get_columnnames(table_name))
        # Inititialize lists.
        dividend = [None] * len(exps_for_fc)
        divisor = [None] * len(exps_for_fc)
        fc_col_position = [None] * len(exps_for_fc)
        # Format all columns with scientific notation that end with underscore and a number.
        datacol_pattern = re.compile(r'_\d+$')
        for i, column_name in enumerate(column_names):
            if datacol_pattern.search(column_name) is not None:
                column_names[i] = '{} AS {}'.format(self.wrap_in_func('to_char',
                                                                      column_name, 
                                                                      self.DB_PRECISION),
                                                    column_name)
                for j, pair in enumerate(exps_for_fc):
                    pattern = r'_{}$'.format(str(pair['dividend'].id))
                    if re.search(pattern, column_name):
                        if not dividend[j]: 
                            dividend[j] = (column_name, pair['dividend'].id,)
                            # For the j-th column there will be j columns inserted before that.
                            fc_col_position[j] = i + j
                    elif (str(pair['divisor'].id) in column_name and 
                          not divisor[j]):
                        divisor[j] = (column_name, pair['divisor'].id)
        
        # Insert the columns for calculating the fold change.
        for i in range(len(dividend)): 
            fc_col = '{quotient} AS {quotient_name}'.format(
                quotient=self.wrap_in_func(
                            'to_char', 
                            self.wrap_in_func(
                                self.DB_FUNCTION_ZERO, 
                                dividend[i][0], divisor[i][0]
                            ),
                            self.DB_PRECISION
                ),
                quotient_name='"fc_%s_%s"' % (dividend[i][1], divisor[i][1]),
            )
            
            column_names.insert(fc_col_position[i], fc_col)
        sql = "SELECT %s FROM %s" % (', '.join(column_names), table_name)
        return from_db(sql, fetch_as=fetch_as)
        
    def get_foldchange(self, exps_for_fc):
        """
        Get only the fold change column.
        """
        exp_id_str = get_id_str(self.req_exps)
        table_name = '%s_datatable_%s' % (self.app_label, exp_id_str)
        # Make experiment for fold change unique.
        exps_for_fc = get_unique(exps_for_fc)
        if not db_table_exists(table_name):
            self.create_base_table(table_name)
        column_names = list(get_columnnames(table_name))
        # Inititialize lists.
        dividend = [None] * len(exps_for_fc)
        divisor = [None] * len(exps_for_fc)
        fc_col_position = [None] * len(exps_for_fc)
        # Format all columns with scientific notation that end with underscore and a number.
        datacol_pattern = re.compile(r'_\d+$')
        for i, column_name in enumerate(column_names):
            if datacol_pattern.search(column_name) is not None:
                for j, pair in enumerate(exps_for_fc):
                    pattern = r'_{}$'.format(str(pair['dividend'].id))
                    if re.search(pattern, column_name):
                        if not dividend[j]: 
                            dividend[j] = (column_name, pair['dividend'].id,)
                            # For the jth column there will be j columns inserted before that.
                            fc_col_position[j] = i + j
                    elif (str(pair['divisor'].id) in column_name and 
                          not divisor[j]):
                        divisor[j] = (column_name, pair['divisor'].id)
        
        # Insert the columns for calculating the fold change.
        for i in range(len(dividend)): 
            fc_col = '{quotient} AS {quotient_name}'.format(
                quotient=self.wrap_in_func(self.DB_FUNCTION_ZERO, dividend[i][0], divisor[i][0]),
                quotient_name='"fc_%s/%s"' % (dividend[i][1], divisor[i][1]),
            )
            column_names.insert(fc_col_position[i], fc_col)
    
        sql = "SELECT %s FROM %s" % (fc_col, table_name)
        return from_db(sql, fetch_as='tuple')
    
    def get_exp_columns(self, wanted_exps):
        """
        Get column of respective experiment.
        """
        # Get the dict.
        exp_id_str = get_id_str(self.req_exps)
        table_name = '%s_datatable_%s' % (self.app_label, exp_id_str)
        # Make experiment unique.
        if not db_table_exists(table_name):
            self.create_base_table(table_name)
        column_names = list(get_columnnames(table_name))
        divisor_col = None
        dividend_col = None
        #exp_cols = []
        #potential_columns = []
        # Iterate over all column names, and make a list of those that hold data.
        datacol_pattern = re.compile(r'_\d+$')
        dividend_pattern = r'_{}$'.format(str(wanted_exps['dividend'].id))
        divisor_pattern = r'_{}$'.format(str(wanted_exps['divisor'].id))
        for column_name in column_names:
            if datacol_pattern.search(column_name) is not None:
                if divisor_col is None:
                    if re.search(divisor_pattern, column_name):
                        divisor_col = column_name
                if dividend_col is None:
                    if re.search(dividend_pattern, column_name):
                        dividend_col = column_name
        
        sql = "SELECT %s, %s FROM %s;" % (dividend_col, divisor_col, table_name)
        return from_db(sql, fetch_as='tuple')
