# Django
from django.conf.urls import url

# App
from . import views

app_name = 'sulfolobus'
urlpatterns = [
    url(r'^filter/exp_info/', views.ExperimentInfoView.as_view(), name='exp_info'),
    url(r'^filter/', views.ExperimentFilterView.as_view(), name='experiment_filter'),
    url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/get_distribution_plot/', 
        views.DistributionPlotView.as_view(), 
        name='get_distribution_plot'),
    url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/get_compare_plot/', 
       views.ComparePlotView.as_view(), 
       name='get_compare_plot'),
    url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/calculate_fold_change/', 
        views.CalculateFoldChangeView.as_view(), 
        name='fold_change'),
    url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/get_table_data/', 
        views.GetTableData.as_view(), 
        name='get_table_data'),
    url(r'^data/(?P<exp_id_str>\d+(?:_\d+)*)/$', views.DataView.as_view(), name='data'),
]
