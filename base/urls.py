"""urlconf for the base application"""

from django.conf.urls import url, patterns, include
from forms import AdvancedSearchForm, AdvFacetedSearchForm
from haystack.views import SearchView, search_view_factory, FacetedSearchView
from haystack.query import SearchQuerySet

sqs = SearchQuerySet().facet('prop_19_exact')

urlpatterns = patterns('base.views',
    url(r'^$', 'home', name='home'),
    url(r'^map/', 'map', name='map'),
    url(r'^search/', FacetedSearchView(
        form_class = AdvFacetedSearchForm,
        searchqueryset = sqs
    ), name='haystack_search'),
    # ex: /ur.iaas.upenn.edu/subject/5/
    url(r'^subject/(?P<subject_id>\d+)/$', 'subjectdetail', name='subjectdetail'),
    # ex: /ur.iaas.upenn.edu/personorg/5/
    url(r'^(?P<personorg_id>\d+)/$', 'personorgdetail', name='personorgdetail'),
    # ex: /ur.iaas.upenn.edu/media/5/
    url(r'^media/(?P<media_id>\d+)/$', 'mediadetail', name='mediadetail'),
    url(r'^search_help/', 'search_help', name='search_help'),
)
