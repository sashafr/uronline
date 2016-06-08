"""urlconf for the base application"""

from django.conf.urls import url, patterns, include
from forms import AdvancedSearchForm, AdvFacetedSearchForm, AdvModelSearchForm
from haystack.views import SearchView, search_view_factory, FacetedSearchView
from haystack.query import SearchQuerySet

sqs = SearchQuerySet().facet('prop_19_exact')

urlpatterns = patterns('base.views',
    url(r'^admin/base/file/add/', 'addfile', name='addfile'),
    url(r'^$', 'home', name='home'),
    url(r'^map/(?P<location_id>\d+)/$', 'mapdetail', name='mapdetail'),
    url(r'^about/ur-online-project', 'about', name='about'),
    url(r'^about/ancient-ur/', 'ancientur', name='ancientur'),
    url(r'^about/excavations/', 'excavations', name='excavations'),
    url(r'^about/woolleys-excavations/', 'woolley', name='woolley'),
    url(r'^about/cast-of-characters/', 'characters', name='characters'),
    url(r'^developers/', 'developers', name='developers'),
    url(r'^sample/', 'sample', name='sample'),
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
    url(r'^terminology/', 'terminology', name='terminology'),
    url(r'^browse/', 'browse', name='browse'),
    url(r'^collections/', 'collections', name='collections'),    
    url(r'^term/(?P<term_id>\d+)/$', 'termdetail', name='termdetail'), 
    url(r'^collection/(?P<collection_id>\d+)/$', 'collectiondetail', name='collectiondetail'),    
    url(r'^term_export/(?P<term_id>\d+)/$', 'termdetailexport', name='termdetailexport'),
    url(r'^collection_export/(?P<collection_id>\d+)/$', 'collectiondetailexport', name='collectiondetailexport'),    
    url(r'^location/(?P<location_id>\d+)/$', 'locationdetail', name='locationdetail'),
    url(r'^location_export/(?P<location_id>\d+)/$', 'locationdetailexport', name='locationdetailexport'),    
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
    url(r'^kyra_special_2/', 'kyra_special_2', name='kyra_special_2'),
    url(r'^select2/', include('django_select2.urls')),
    url(r'^bulk_update_subject/$', 'bulk_update_subject', name='bulk_update_subject'),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^bulk_upload_file/', 'bulk_upload_file', name='bulk_upload_file'),
)
