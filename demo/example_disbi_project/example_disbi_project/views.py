# Django
from django.shortcuts import redirect


def go_to_organism(request):
    
    organism_slug = request.GET['organism']
    url = '/{}/filter/'.format(organism_slug)
    return redirect(url) 
