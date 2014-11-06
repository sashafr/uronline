""" Views for the base application """

from django.shortcuts import render, get_object_or_404, render_to_response
from base.models import FeaturedImgs, Subject, Media, PersonOrg, Post
from haystack.views import SearchView
from base.forms import AdvancedSearchForm
from django.forms.formsets import formset_factory
from base import tasks
from django.core.paginator import Paginator, InvalidPage, EmptyPage

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
    
def about(request):

    return render(request, 'base/about.html')
    
def update_index(request):
    t = tasks.index_update()
    return HttpResponse(t.task_id)
    
def news(request):
    posts = Post.objects.filter(published=True)
    paginator = Paginator(posts, 10)
    
    try: 
        page = int(request.GET.get("page", '1'))
    except ValueError: 
        page = 1
    
    try:
        posts = paginator.page(page)
    except (InvalidPage, EmptyPage):
        posts = paginator.page(paginator.num_pages)
        
    return render(request, 'base/news.html', {'posts':posts})
    
def post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    return render(request, 'base/post.html', {'post':post})
    
def contact(request):

    return render(request, 'base/contact.html')    