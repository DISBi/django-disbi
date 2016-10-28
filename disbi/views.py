"""
DISBi views that need to subclassed and configured with 
the appropriate experiment models by a concrete app. 
"""
# standard library
import re
from io import StringIO

# third-party
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import numpy as np

# Django
from django.forms import formset_factory
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_safe
from django.views.generic import View

# DISBi
from disbi.cache_table import check_for_table_change
from disbi.exceptions import NoRelatedMeasurementModel, NotSupportedError
from disbi.forms import construct_forms, foldchange_form_factory
from disbi.option_utils import get_display_name
from disbi.experiment_filter import get_requested_experiments
from disbi.result import DataResult
from disbi.templatetags.custom_template_tags import nested_dict_as_table
from disbi.utils import get_id_str, get_ids


# ---------------------------- main views -----------------------------
class DisbiExperimentFilterView(View):
    """
    View for showing dynamic formsets, allowing to choose all combinations.
    """
    experiment_model = None

    def get(self, request):
        """
        Returns:
            TemplateResponse: The rendered forms without initial data.
        """
        formclasses = construct_forms(self.experiment_model)
        formset_list = []
        for formclass in formclasses:
            FormSetClass = (formset_factory(formclass.classname, 
                                            max_num=formclass.classname.max_num))
            formset_list.append(FormSetClass(prefix=formclass.prefix))
            
        context = {'formset_list': formset_list,
                   'subheader': 'Filter'}
        return render(request, 'disbi/filter.html', context)
        
    def post(self, request):
        """
        HttpResponseRedirect: For valid POST requests the client will
        be redirected to the appropriate data view.
        """
        formclasses = construct_forms(self.experiment_model)
        app_label = self.experiment_model._meta.app_label
        formset_list = []
        for formclass in formclasses:
            FormSetClass = formset_factory(formclass.classname, 
                                            max_num=formclass.classname.max_num)
            formset_list.append(FormSetClass(request.POST, 
                                             prefix=formclass.prefix))  
            
        # Validation
        for formset in formset_list:
            if not formset.is_valid():
                validated = False
                break
            else:
                validated = True
                continue
            
        if validated:
            requested_exps = get_requested_experiments(formset_list, self.experiment_model)
            id_str = get_id_str(requested_exps)
            url = '/{}/data/{}/'.format(app_label,
                                        id_str)
            return redirect(url)
            
            
        # If not validated...
        else:
            formset_list = []
            # Instantiate formsets with prefix and POST data.
            for formclass in formclasses:
                FormSetClass = formset_factory(formclass.classname, 
                                                max_num=formclass.classname.max_num)
                # Check whether POST contains data for this specific formset.
                has_data = False
                for pkey in request.POST.keys():
                    if pkey.startswith(formclass.prefix + '-0-'):
                        if request.POST.get(pkey):
                            has_data = True
                        break
                    else:
                        continue
                # If there is data instantiate with POST data,
                # else instantiate empty formset
                ## This is done, because forms completely removed with JS
                ## do not show up again otherwise
                if has_data:
                    formset_list.append(FormSetClass(request.POST, 
                                                 prefix=formclass.prefix))
                else:
                    formset_list.append(FormSetClass(prefix=formclass.prefix))  
        
        context = {'formset_list': formset_list,
               'subheader': 'Filter'}
        return render(request, 'disbi/filter.html', context)


class DisbiDataView(View):
    """
    View for creating the the basic data view without the data table.
    """
    experiment_meta_model = None
    
    def get(self, request, exp_id_str):
        """
        View for creating and displaying the result table.
        
        Args:
            request: The WSGI request.
            exp_id_str: The ids of all requested experiments from the table view
                joined on "_".
        
        Returns:
            TemplateResponse: The template for the data view with the appropriate
            form and the result table with information about the experiments.
        """
        # Check if the backbone table needs to be recreated.
        check_for_table_change(self.experiment_meta_model, check_for='bio')
        # Check if the data tables needs to be dropped.
        check_for_table_change(self.experiment_meta_model, check_for='data')
        
        try:
            # Get the displayed experiments from the URL.
            exp_ids = get_ids(exp_id_str)
            requested_exps = self.experiment_meta_model.objects.filter(pk__in=exp_ids)
            num_exps = len(requested_exps)
            if num_exps > 1:
                # Instantiate empty fold change form.
                FoldChangeForm = foldchange_form_factory(requested_exps)
                FoldChangeFormset = formset_factory(FoldChangeForm)
                foldchange_formset = FoldChangeFormset(prefix='fc')    
                # Instantiate empty plot compare form.
                PlotCompareForm = foldchange_form_factory(requested_exps)
                #PlotCompareFormset = formset_factory(PlotCompareForm)
                plotcompare_form = PlotCompareForm()
            else:
                foldchange_formset = None
                plotcompare_form = None
            # Create the data table.
            result = DataResult(requested_exps, self.experiment_meta_model)  
            table_data = result.get_or_create_base_table()
            # Create the talbe with information about the selected experiments.
            view_exps = [exp.result_view() for exp in requested_exps]
            
            context = {'table_data': table_data,
                       'view_exps': view_exps,
                       'num_exps': num_exps,
                       'foldchange_formset': foldchange_formset,
                       'plotcompare_form': plotcompare_form,
                       'subheader': 'Data'}
            return render(request, 'disbi/data.html', context)
        except NoRelatedMeasurementModel as exc:
            return HttpResponse('{} has no experimental data yet.'.format(exc.exp))
            

# ---------------------------- AJAX views -----------------------------
class DisbiExpInfoView(View):
    """
    View for getting information about the experiments in the preview table.
    """
    experiment_model = None
    
    def post(self, request):
        """
        Get information about matched experiments.
        
        Args:
            request: The WSGI request.
            
        Returns:
            JSONResponse: JSON object with number of matched experiments and a
            HTML table with information about those experiments.
        """
        formclasses = construct_forms(self.experiment_model)
        formset_list = []
         
        # Instantiate formsets with prefix and POST data.
        for formclass in formclasses:
            FormSetClass = formset_factory(formclass.classname, 
                                            max_num=formclass.classname.max_num)
            formset_list.append(FormSetClass(request.POST, 
                                             prefix=formclass.prefix))
        # Validation
        for formset in formset_list:
            if not formset.is_valid():
                validated = False
                break
            else:
                validated = True
                continue
            
        if validated:
            requested_exps = get_requested_experiments(formset_list, self.experiment_model)
            num_exps = len(requested_exps)
            if num_exps > 0:
                view_exps = [exp.view() for exp in requested_exps]
                table_exps = nested_dict_as_table(view_exps, make_foot=False)
            else:
                view_exps = None
                table_exps = None
                
        return JsonResponse(
            {'numExps': num_exps,
             'expParams': view_exps,
             'tableExps': table_exps}
            )


class DisbiGetTableData(View):
    """
    View for initially getting the data for the datatable.
    """
    experiment_meta_model = None
    
    def get(self, request, exp_id_str):
        """
        Return new data for the datatable with new columns for calculated fold changes.
        
        Args:
            request: The WSGI request.
            exp_id_str: The ids of all requested experiments from the table view
                joined on "_".
        
        Returns:
            JSONResponse: The data for the datatable.
        """  
        response = {}
        response['status'] = None
        response['data'] = {}
        response['err_msg'] = None
        exp_ids = get_ids(exp_id_str)
        requested_exps = self.experiment_meta_model.objects.filter(pk__in=exp_ids)
        result = DataResult(requested_exps, self.experiment_meta_model)  
        table_data = result.get_or_create_base_table(fetch_as='namedtuple')
        
        response['data']['columns'] = table_data[0]._fields
        response['data']['tableData'] = [tuple(row) for row in table_data]
        
        return JsonResponse(response)


class DisbiCalculateFoldChangeView(View):
    """
    View for calculating the fold change between two experiments.
    """
    experiment_model = None
    experiment_meta_model = None
    
    def post(self, request, exp_id_str):
        """
        Return new data for the datatable with new columns for calculated fold changes.
        
        Args:
            request: The WSGI request.
            exp_id_str: The ids of all requested experiments from the table view
                joined on "_".
        
        Returns:
            JSONResponse: The new data for the datatable or the error message.
        """    
        response = {}
        response['status'] = None
        response['data'] = {}
        response['err_msg'] = None
        exp_ids = get_ids(exp_id_str)
        # Instantiate formset with POST data
        requested_exps = self.experiment_model.objects.filter(pk__in=exp_ids)
        FoldChangeForm = foldchange_form_factory(requested_exps)
        FoldChangeFormset = formset_factory(FoldChangeForm)
        foldchange_formset = FoldChangeFormset(request.POST, prefix='fc')
        # Validation
        try:
            if foldchange_formset.is_valid():
                # Filter out empty form data. These can result if both fields
                # are left empty.
                exps_for_foldchange = [cleaned_data for cleaned_data  
                                       in foldchange_formset.cleaned_data 
                                       if cleaned_data]
                # TODO: This should be done in the form.
                # Check data.
                ## Check for empty form.
                if not exps_for_foldchange:
                
                    raise ValueError('You need to select at least two unequal experiments '
                                       'to calculate a fold change.')
                ## Check whether each two experiments have the same measurementmodel.
                for pair in exps_for_foldchange:
                    dividend = self.experiment_meta_model.objects.get(pk=pair['dividend'].pk)
                    divisor = self.experiment_meta_model.objects.get(pk=pair['divisor'].pk)
                    if dividend.measurementmodel != divisor.measurementmodel:
                        raise ValueError('To compare experiments, they need to have the same datatype.')
                result = DataResult(requested_exps, self.experiment_meta_model)
                table_data = result.add_foldchange(exps_for_foldchange, fetch_as='namedtuple')
                response['data']['columns'] = table_data[0]._fields
                response['data']['tableData'] = [tuple(row) for row in table_data]
                response['status'] = True
                
                return JsonResponse(response)
        
            else:
                response['err_msg'] = ('You need to select at least two unequal experiments '
                                       'to calculate a fold change.')
                response['status'] = False
                return JsonResponse(response)
        except ValueError as exc:
            response['err_msg'] = str(exc)
            response['status'] = False
            return JsonResponse(response)
        
    
class DisbiComparePlotView(View):
    """
    View for generating a scatter plot that compares two experiments.
    """
    experiment_model = None
    experiment_meta_model = None
    
    def post(self, request, exp_id_str):
        """
        Get the scatter plot comparing two experiments.
        
        If the data model of the two experiments matches, a plot is generated,
        else an error message is raised.
         
        Args:
            request: The WSGI request.
            exp_id_str: The ids of all requested experiments from the table view
                joined on "_".
        
        Returns:
            JSONResponse: The plot image SVG or the error message.
        """
        response = {}
        response['status'] = None
        response['data'] = None
        response['err_msg'] = None
        exp_ids = get_ids(exp_id_str)
        # Instantiate formset with POST data
        requested_exps = self.experiment_model.objects.filter(pk__in=exp_ids)
        PlotCompareForm = foldchange_form_factory(requested_exps)
        plotcompare_form = PlotCompareForm(request.POST)
        # Validation
        try:
            if plotcompare_form.is_valid():
        
                exps_for_compare = plotcompare_form.cleaned_data
                # Get the metainfo proxy to check the measurementmodel.
                dividend = self.experiment_meta_model.objects.get(pk=exps_for_compare['dividend'].pk)
                divisor = self.experiment_meta_model.objects.get(pk=exps_for_compare['divisor'].pk)
                if dividend.measurementmodel != divisor.measurementmodel:
                    raise ValueError('To compare experiments, they need to have the same datatype.')
                if exps_for_compare:
                    # Get the data from the DB
                    result = DataResult(requested_exps, self.experiment_meta_model)
                    data = result.get_exp_columns(exps_for_compare)
                    # Remove None values, because might be missing in the SVG otherwise.
                    data = [pair for pair in data if pair[0] and pair[1]]
                    # Load the data into arrays.
                    data = np.array(data).transpose()
                    x = data[0]
                    y = data[1]
                    fig = plt.figure()
                    ax = fig.add_subplot(111)
                    # Add the scatter plot.
                    ax.plot(x, y, '.', color='#005374') # color=BRICS blue 1
                    # Add a grey line through the origin.
                    a = np.linspace(*ax.get_xbound())
                    b = np.linspace(*ax.get_ybound())
                    ax.plot(a, b, '--', color='#5f5f5f') # color=BRICS grey 2
                    # Set labels.
                    ax.set_xlabel(str(dividend))
                    ax.set_ylabel(str(divisor))
                    # Write SVG tho string buffer and return it as response.
                    buf = StringIO()
                    fig.savefig(buf, format='svg')
                    buf.seek(0)  # rewind the data
                    plt.close('all')
                    response['data'] = buf.read()
                    response['status'] = True
                    
                    return JsonResponse(response)
            else:
                response['status'] = False
                response['err_msg'] = ('You need to select at least two unequal experiments '
                            'to compare experiments.')
                return JsonResponse(response)
        except ValueError as exc:
            response['status'] = False
            response['err_msg'] = str(exc)
            return JsonResponse(response)
    
    
class DisbiDistributionPlotView(View):
    """
    View for generating a histogram of the distribution of a column 
    in the data table.
    """
    experiment_model = None
    experiment_meta_model = None
    
    def post(self, request, exp_id_str):
        """
        Get the distribution of a column as a histogram.
        
        If a non fold change column is plotted the matching data is fetched
        from the DB with the ORM.
        If a fold change column is selected, a new DataResult object is 
        instantiated and only the fold change column is retrieved from the 
        result table cached in the DB.
        
        Args:
            request: The WSGI request.
            exp_id_str: The ids of all requested experiments from the table view
                joined on "_".
        
        Returns:
            JSONResponse: The plot image SVG or the error message.
        """
        response = {}
        response['status'] = None
        response['data'] = None
        response['err_msg'] = None
        try:
            fold_change = False
            # The column to be plotted.
            col = self.request.POST['column']
            # Pattern that matches the trailing id of th experiment (e.g. _16)  
            # or of a fold change column (e.g. _16_17). 
            id_pattern = re.compile(r'_(\d+(?:_\d+)*)')
            # Get the id.
            exp_id = id_pattern.search(col).group(1)
            # Substitute the experiment id with '' to get the name.
            column_display_name = id_pattern.sub('', col)
            if 'fc' not in column_display_name:
                # We're not dealing with a fold change.    
                exp = self.experiment_meta_model.objects.get(pk=exp_id)
                # Map the names used to display the columns to their actual names. 
                display_names_to_names = dict(
                                    (get_display_name(field), field.name, )
                                    for field in exp.measurementmodel._meta.get_fields() 
                                    )
                column_name = display_names_to_names[column_display_name]
                # Get only values that are not NULL.
                filter_conds = {'experiment': exp,
                               column_name+'__isnull': False}
                data = exp.measurementmodel.objects.filter(**filter_conds).values_list(column_name)
                xlabel = '{} {}'.format(exp.measurementmodel._meta.verbose_name, column_display_name)
                title = 'Distribution of {} {} {}'.format(exp.measurementmodel._meta.verbose_name,
                                                       column_display_name,
                                                       exp_id)                
        
            else:
                # We're dealing with a fold change column.
                dividend_id, divisor_id = exp_id.split('_')
                dividend_exp = self.experiment_meta_model.objects.get(pk=dividend_id)
                divisor_exp = self.experiment_meta_model.objects.get(pk=divisor_id)
               
                if dividend_exp.measurementmodel != divisor_exp.measurementmodel:
                    raise NotSupportedError('To plot a fold change the experiments '
                                            'must have the same datatype.')
                # Get the displayed experiments from the URL.
                exp_ids = get_ids(exp_id_str)
                requested_exps = self.experiment_model.objects.filter(pk__in=exp_ids)
                # Create the data table.
                result = DataResult(requested_exps, self.experiment_meta_model) 
                data = result.get_foldchange(({'dividend': dividend_exp, 
                                               'divisor': divisor_exp},))
 
                # Filter out NULL values.
                ## Flatten.
                data = sum(data, ())
                data = list((datapoint for datapoint in data if datapoint is not None))
                xlabel = 'log2 fold change {}/{}'.format(dividend_exp.id, divisor_exp.id)
                fold_change = True
                title = 'Distribution of fold change {}/{}'.format(
                            dividend_exp.id, divisor_exp.id
                            )
            ylabel = 'Number of data points' # The y-label is always same for histograms.
            fig = plt.figure()
            ax = fig.add_subplot(111)
            data = np.array(data)
            if fold_change:
                # Calculate log2 for fold change and filter out inf and NaN values
                # as result from log(0) and log(-a).
                data = np.log2(data)
                data = data[~np.isinf(data) & ~np.isnan(data)]
            # Use `doane` estimator as using `auto` for non normal distributed data
            # takes forever. 
            ax.hist(data, bins='doane', color='#005374')
            # Set labels and title.
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            
            # Store the plot in a byte stream and encode it as base64.
            buf = StringIO()
            fig.savefig(buf, format='svg')
            buf.seek(0)  # rewind the data
            plt.close('all')
    
            response['status'] = True
            response['data'] = buf.read()
            return JsonResponse(response)
        
        except NotSupportedError as exc:
            response['status'] = False
            response['err_msg'] = str(exc)
            return JsonResponse(response)
        except:
            response['status'] = False
            response['err_msg'] = 'Internal Error: Column cannot be plotted.'
            return JsonResponse(response)
