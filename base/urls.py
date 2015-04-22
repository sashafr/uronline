"""urlconf for the base application"""

from django.conf.urls import url, patterns, include
from forms import AdvancedSearchForm, AdvFacetedSearchForm, AdvModelSearchForm
from haystack.views import SearchView, search_view_factory, FacetedSearchView
from haystack.query import SearchQuerySet

sqs = SearchQuerySet().facet('prop_19_exact')

urlpatterns = patterns('base.views',
    url(r'^$', 'home', name='home'),
    url(r'^map/(?P<location_id>\d+)/$', 'mapdetail', name='mapdetail'),
    url(r'^about/', 'about', name='about'),
    url(r'^search/', FacetedSearchView(
        form_class = AdvModelSearchForm,
        searchqueryset = sqs
    ), name='haystack_search'),
    # ex: /ur.iaas.upenn.edu/subject/5/
    url(r'^subject/(?P<subject_id>\d+)/$', 'subjectdetail', name='subjectdetail'),
    # ex: /ur.iaas.upenn.edu/personorg/5/
    url(r'^personorg/(?P<personorg_id>\d+)/$', 'personorgdetail', name='personorgdetail'),
    # ex: /ur.iaas.upenn.edu/media/5/
    url(r'^media_item/(?P<media_id>\d+)/$', 'mediadetail', name='mediadetail'),
    url(r'^property/(?P<prop_id>\d+)/$', 'propertydetail', name='propertydetail'),    
    url(r'^location/(?P<location_id>\d+)/$', 'locationdetail', name='locationdetail'),    
    url(r'^search_help/', 'search_help', name='search_help'),
    url(r'^help/', 'help', name='help'),
    url(r'^update_index/', 'update_index', name='update_index'),
    url(r'^news/(?P<slug>[\w\-]+)/$', 'post'),
    url(r'^news/', 'news', name='news'),
    url(r'^contact/', 'contact', name='contact'),
    url(r'^property_export/(?P<prop_id>\d+)/$', 'export_property_details', name='export_property_details'),
    url(r'^control_property_export/(?P<prop_id>\d+)/$', 'export_control_property_details', name='export_control_property_details'),    
    url(r'^result_export/', 'export_search_results', name='export_search_results'),
    url(r'^single_loc_in_ah/', 'kyra_special_ah', name='kyra_special_ah'),
    url(r'^search_export/(?P<selected_facets>\S+)/$', 'search_export', name='search_export'),
    url(r'^penn_metal_subdiv/', 'kyra_special_penn_metal_subdiv', name='kyra_special_penn_metal_subdiv'),    
)
