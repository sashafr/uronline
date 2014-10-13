""" Views for the base application """

from django.shortcuts import render, get_object_or_404, render_to_response
from base.models import FeaturedImgs, Subject, Media, PersonOrg
from haystack.views import SearchView
from base.forms import AdvancedSearchForm
from django.forms.formsets import formset_factory

def home(request):
    """ Default view for the root """
	
    """ Load featured images """
    featured_imgs = FeaturedImgs.objects.all()
    context = {'featured_imgs': featured_imgs}
	
    return render(request, 'base/home.html', context)
    
def map(request):

    return render(request, 'base/map.html')
    
def subjectdetail(request, subject_id):
    """ Detailed view of a subject record """
    
    subject = get_object_or_404(Subject, pk=subject_id)
    return render(request, 'base/subjectdetail.html', {'subject': subject})
    
def mediadetail(request, media_id):
    """ Detailed view of a media record """
    
    media = get_object_or_404(Media, pk=media_id)
    return render(request, 'base/mediadetail.html', {'media': media})
    
def personorgdetail(request, personorg_id):
    """ Detailed view of a person/organization record """
    
    personorg = get_object_or_404(PersonOrg, pk=personorg_id)
    return render(request, 'base/personorgdetail.html', {'personorg': personorg})
    
def search_help(request):

    return render(request, 'base/search_help.html')