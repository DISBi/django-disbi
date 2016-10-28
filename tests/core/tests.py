"""
Unittest for DISBi components that work without database interaction.
"""
# standard library
from copy import deepcopy
from itertools import product
from types import SimpleNamespace

# Django
from django.core.exceptions import ValidationError
from django.test import TestCase

# DISBi
from disbi.admin import *
from disbi.join import Relations
from disbi.experiment_filter import combine_on_sep
from disbi.result import DataResult
from disbi.utils import get_choices, sort_by_other, construct_none_displayer,\
    get_hr_val, get_optgroups, remove_optgroups, get_id_str, get_ids,\
    get_unique
from disbi.validators import *

    

class ValidatorsTest(TestCase):
    
    def test_validate_probability(self):
        in_range = [0.5, 0, 1]
        below_range = -0.2
        over_range = 1.2
        
        # check if it works
        for num in in_range:
            validate_probabilty(num)
            
        # Check that it raises an error.
        with self.assertRaises(ValidationError):
            validate_probabilty(below_range)
        with self.assertRaises(ValidationError):
            validate_probabilty(over_range)
        
    def test_validate_flux(self):
        
        in_range = [-500, 0, 25]
        below_range = -1001.2
        over_range = 10000.2
        
        # check if it works
        for num in in_range:
            validate_flux(num)
            
        # check that it raises an error
        with self.assertRaises(ValidationError):
            validate_flux(below_range)
        with self.assertRaises(ValidationError):
            validate_flux(over_range)

            
    def test_ec_validator(self):
        
        valid_ec_numbers = {'1.1.1.1', '2.3.4.-', '2.3.-.-', '2.-.-.-',
                            '2.3.4.B5', '2.3.4.n5', '2.3.4.m5'}
        invalid_ec_numbers = {'7.1.1.1', '2.3.-', '2.-', '2.-.-.5', '1.2.3.4.5'}
        
        # Check the valid EC numbers.
        for ec in valid_ec_numbers:
            ec_validator(ec)
        
        # Check that the invalid EC numbers raise error.
        for ec in invalid_ec_numbers:
            with self.assertRaises(ValidationError, 
                                   msg='Invalid EC number {} got validated'.format(ec)):
                ec_validator(ec)
                
    def test_short_ec_validator(self):
        
        valid_ec_numbers = {'1.1.1.1', '2.3.4.-', '2.3.-', '2.-',
                            '2.3.4.B5', '2.3.4.n5', '2.3.4.m5'}
        invalid_ec_numbers = {'7.1.1.1', '2.3.-.-', '2.-.-.-', '2.-.-.5', '1.2.3.4.5'}
        
        # Check the valid EC numbers.
        for ec in valid_ec_numbers:
            short_ec_validator(ec)
        
        # Check that the invalid EC numbers raise error.
        for ec in invalid_ec_numbers:
            with self.assertRaises(ValidationError, 
                                   msg='Invalid EC number {} got validated'.format(ec)):
                short_ec_validator(ec)
        
        
class UtilsTest(TestCase):
    
    def test_get_choices(self):
        
        # example choice values
        t_opt = (
        ('Transcriptomics', (
                ('RNAseq', 'RNAseq'),
                ('microarray', 'Microarray'),
            )
        ),
        ('Proteomics', (
                ('cytosolic', 'cytosolic'),
                ('exometabolome', 'exometabolome'),
                ('membrane', 'membrane'),
            )
        ),                             
        ('Metabolomics', (
                ('intracellular', 'intracellular'),
                ('extracellular', 'extracellular'),
            )
        ),
        ('Predicted Flux', (
                ('fba', 'FBA'),
                ('fva', 'FVA'),
            )
        ),
        )  

        t_noopt = (('intracellular', 'Intracellular'),
           ('extracellular', 'Extracellular'))
        
        self.assertEqual(get_choices(t_opt), ['RNAseq', 'microarray', 'cytosolic',
                                              'exometabolome', 'membrane', 
                                              'intracellular', 'extracellular', 
                                              'fba', 'fva'])
        self.assertEqual(get_choices(t_opt, style='db'), ['RNAseq', 'microarray', 'cytosolic',
                                              'exometabolome', 'membrane', 
                                              'intracellular', 'extracellular', 
                                              'fba', 'fva'])
        self.assertEqual(get_choices(t_opt, style='display'), ['RNAseq', 'Microarray',
                                                                'cytosolic', 'exometabolome', 
                                                                'membrane', 'intracellular', 
                                                                'extracellular', 
                                                                'FBA', 'FVA'])

        self.assertEqual(get_choices(t_noopt), ['intracellular', 'extracellular'])
        self.assertEqual(get_choices(t_noopt, style='db'), ['intracellular', 'extracellular'])
        self.assertEqual(get_choices(t_noopt, style='display'),['Intracellular', 'Extracellular'])
        with self.assertRaises(ValueError):
            get_choices(t_noopt, style='unknown')

    def test_sort_by_other(self):
        
        o = ['g', 'f', 'e', 'd', 'c', 'b', 'a']
        l = ['c', 'f', 'a']
        self.assertEqual(sort_by_other(l, o), ['f', 'c', 'a'])

    def test_camelize(self):
        
        from disbi.utils import camelize

        lower_underscore = 'all_words_lowercase_and_separated_by_underscore'
        camel_case_first_upper = 'AllWordsLowercaseAndSeparatedByUnderscore'
        camel_case = 'allWordsLowercaseAndSeparatedByUnderscore'
        
        self.assertEqual(camelize(lower_underscore), camel_case_first_upper)
        
        self.assertEqual(camelize(lower_underscore, uppercase_first_letter=False),
                         camel_case)
        
    def test_construct_none_displayer(self):
        
        short_entries = ['a', 'aa', 'aaa']
        self.assertEqual('-----', construct_none_displayer(short_entries))
    
        long_entries = ['a', 'aa', 'aaa', 'longer', 'very very long']
        self.assertEqual('---------------', construct_none_displayer(long_entries))
        
    def test_get_hr_val(self):
        
        choice_tuple = (('db_val_1', 'First value from the database'),
                        ('db_val_2', 'Second value from the database'),
                        ('db_val_3', 'Third value from the database'))
        self.assertEqual('Third value from the database', get_hr_val(choice_tuple, 'db_val_3'))
        self.assertEqual(None, get_hr_val(choice_tuple, 'db_val_4'))
        
    def test_get_optgroups(self):
        
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
                    ('lcms', 'LCMS'),
                )
            ),
            ('Predicted Flux', (
                    ('fba', 'FBA'),
                )
            ),
        )
        
        optgroups_with_db_values = {'Transcriptome': ['rnaseq'],
                                    'Proteome': ['shotgun'],
                                    'Metabolome': ['gcms', 'lcms'],
                                    'Predicted Flux': ['fba']}
        self.assertEqual(optgroups_with_db_values, 
                         get_optgroups(EXPERIMENT_METHOD_CHOICES, style='db'))
    
    
        optgroups_with_display_values = {'Transcriptome': ['RNAseq'],
                                         'Proteome': ['shotgun'],
                                         'Metabolome': ['GCMS', 'LCMS'],
                                         'Predicted Flux': ['FBA']}
        self.assertEqual(optgroups_with_display_values, 
                         get_optgroups(EXPERIMENT_METHOD_CHOICES, style='display'))
        with self.assertRaises(ValueError):
            get_optgroups(EXPERIMENT_METHOD_CHOICES, style='unknown')
        
        EXPERIMENT_TYPE_CHOICES = (
            ('transcriptome', 'Transcriptome'),
            ('proteome', 'Proteome'),
            ('metabolome', 'Metabolome'),
            ('flux', 'Predicted Flux'),
        )
        with self.assertRaises(ValueError):
            get_optgroups(EXPERIMENT_TYPE_CHOICES, style='db')
        
    def test_remove_optgroups(self):
        
        EXPERIMENT_METHOD_CHOICES_with_optgroups = (
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
                    ('lcms', 'LCMS'),
                )
            ),
            ('Predicted Flux', (
                    ('fba', 'FBA'),
                )
            ),
        )

        EXPERIMENT_METHOD_CHOICES_without_optgroups = (
            ('rnaseq', 'RNAseq'),
            ('shotgun', 'shotgun'),
            ('gcms', 'GCMS'),
            ('lcms', 'LCMS'),
            ('fba', 'FBA'),
        )
        
        self.assertEqual(EXPERIMENT_METHOD_CHOICES_without_optgroups,
                         remove_optgroups(EXPERIMENT_METHOD_CHOICES_with_optgroups))
        
    def test_get_id_str(self):
        
        ids = [5, 3, 7, 1]
        model_objs = []
        for identifier in ids:
            mock_model = SimpleNamespace()
            mock_model.id = identifier
            model_objs.append(deepcopy(mock_model))
        
        self.assertEqual('1_3_5_7', get_id_str(model_objs))
        
    def test_get_ids(self):
        
        id_str = '1_3_5_7'
        self.assertEqual([1, 3, 5, 7], get_ids(id_str))
        
    def test_get_unique(self):
        
        non_unique_list = [
            'a', 'a', 'b', 
            [1, 2, 3],
            [1, 2, 3],
            [1, 2, 3, 4],
        ]
        unique_list = [
            'a', 'b', 
            [1, 2, 3],
            [1, 2, 3, 4],
        ]
    
        self.assertEqual(unique_list, get_unique(non_unique_list))
        
class QueryTest(TestCase):
    
    
    def test_combine_on_sep(self):
        
        l = ['a', 'b', 'c', 'd']
        combined_list =  ['a/b', 'a/c', 'a/d', 'b/a', 'b/c', 'b/d', 'c/a', 'c/b', 
                          'c/d', 'd/a', 'd/b', 'd/c']
        self.assertEqual(combine_on_sep(l, '/'), combined_list)


class JoinTest(TestCase):
    
    def test_is_cyclic(self):
        
        r = Relations.__new__(Relations)
        
        # Set up graphs with 3 nodes.
        coords = ['a', 'b', 'c']
    
        proto_map = dict((t, False) for t in product(coords, coords))
        
        non_cyclic_map = deepcopy(proto_map)
        cyclic_map = deepcopy(proto_map)
        
        # Set up non cyclic graph.
        vertices = [('a', 'b'), ('a', 'c')]
        for vertex in vertices:
            non_cyclic_map[vertex] = 1
            non_cyclic_map[tuple(reversed(vertex))] = 1
        # Set up a cyclic graph.
        vertices = [('a', 'b'), ('b', 'c'), ('c', 'a')]
        for vertex in vertices:
            cyclic_map[vertex] = 1
            cyclic_map[tuple(reversed(vertex))] = 1
        
        r.models = coords
        
        r.relation_map = non_cyclic_map
        self.assertTrue(r.is_tree)
        
        r.relation_map = cyclic_map
        self.assertFalse(r.is_tree)
        
        
        # Set up graphs with 4 nodes.
        coords = ['a', 'b', 'c', 'd']
        proto_map = dict((t, False) for t in product(coords, coords))
        
        non_cyclic_map = deepcopy(proto_map)
        cyclic_map = deepcopy(proto_map)
        
        # Set up non cyclic graph.
        vertices = [('a', 'b'), ('a', 'c'), ('c', 'd')]
        for vertex in vertices:
            non_cyclic_map[vertex] = 1
            non_cyclic_map[tuple(reversed(vertex))] = 1
        # Set up a cyclic graph.
        vertices = [('a', 'b'), ('b', 'c'), ('c', 'd'), ('b', 'd')]
        for vertex in vertices:
            cyclic_map[vertex] = 1
            cyclic_map[tuple(reversed(vertex))] = 1
    
        r.models = coords
    
        r.relation_map = non_cyclic_map
        self.assertTrue(r.is_tree)
        
        r.relation_map = cyclic_map
        self.assertFalse(r.is_tree)
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
