# DISBi
from disbi.views import (DisbiCalculateFoldChangeView, DisbiComparePlotView,
                         DisbiDataView, DisbiDistributionPlotView,
                         DisbiExperimentFilterView, DisbiExpInfoView,
                         DisbiGetTableData)

# App
from .models import Experiment, ExperimentMetaInfo


class ExperimentFilterView(DisbiExperimentFilterView):
    experiment_model = Experiment

    
class ExperimentInfoView(DisbiExpInfoView):
    experiment_model = Experiment


class DataView(DisbiDataView):
    experiment_meta_model = ExperimentMetaInfo
   
    
class CalculateFoldChangeView(DisbiCalculateFoldChangeView):
    experiment_model = Experiment
    experiment_meta_model = ExperimentMetaInfo


class ComparePlotView(DisbiComparePlotView):
    experiment_model = Experiment
    experiment_meta_model = ExperimentMetaInfo

    
class DistributionPlotView(DisbiDistributionPlotView):    
    experiment_model = Experiment
    experiment_meta_model = ExperimentMetaInfo


class GetTableData(DisbiGetTableData):
    experiment_meta_model = ExperimentMetaInfo
