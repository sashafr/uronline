"""urlconf for the base application"""

from django.conf.urls import url, patterns, include
from forms import *
from haystack.views import SearchView, search_view_factory, FacetedSearchView
from haystack.query import SearchQuerySet

class SubjectFacetedSearchView(FacetedSearchView):
    """
    We subclass the base haystack view in order to add context.
    """
    
    def extra_context(self):
    
        extra_context = super(SubjectFacetedSearchView, self).extra_context()
        subject_facets = DescriptiveProperty.objects.filter(control_field = True, visible = True).filter(Q(primary_type='SO') | Q(primary_type='AL'))
        extra_context['subject_facets'] = subject_facets
            
        return extra_context

class LocationFacetedSearchView(FacetedSearchView):
    """
    We subclass the base haystack view in order to add context.
    """
    
    def extra_context(self):
    
        extra_context = super(LocationFacetedSearchView, self).extra_context()
        location_facets = DescriptiveProperty.objects.filter(control_field = True, visible = True).filter(Q(primary_type='SL') | Q(primary_type='AL'))
        extra_context['location_facets'] = location_facets
            
        return extra_context
        
class MediaFacetedSearchView(FacetedSearchView):
    """
    We subclass the base haystack view in order to add context.
    """
    
    def extra_context(self):
    
        extra_context = super(MediaFacetedSearchView, self).extra_context()
        media_facets = DescriptiveProperty.objects.filter(control_field = True, visible = True).filter(Q(primary_type='MP') | Q(primary_type='AL'))
        extra_context['media_facets'] = media_facets
            
        return extra_context
        
class PeopleFacetedSearchView(FacetedSearchView):
    """
    We subclass the base haystack view in order to add context.
    """
    
    def extra_context(self):
    
        extra_context = super(PeopleFacetedSearchView, self).extra_context()
        people_facets = DescriptiveProperty.objects.filter(control_field = True, visible = True).filter(Q(primary_type='PO') | Q(primary_type='AL'))
        extra_context['people_facets'] = people_facets
            
        return extra_context
        

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
    url(r'^search/', SubjectFacetedSearchView(
        form_class = AdvFacetedSearchForm,
        template = 'search/search.html',
    ), name='haystack_search'),    
    # ex: /ur.iaas.upenn.edu/subject/5/
    url(r'^subject/(?P<subject_id>\d+)/$', 'subjectdetail', name='subjectdetail'),
    url(r'^subject_export/(?P<subject_id>\d+)/$', 'subjectdetailexport', name='subjectdetailexport'),        
    # ex: /ur.iaas.upenn.edu/personorg/5/
    url(r'^personorg/(?P<personorg_id>\d+)/$', 'personorgdetail', name='personorgdetail'),
    # ex: /ur.iaas.upenn.edu/media/5/
    url(r'^media_item/(?P<media_id>\d+)/$', 'mediadetail', name='mediadetail'),
    url(r'^media_export/(?P<media_id>\d+)/$', 'mediadetailexport', name='mediadetailexport'),
    url(r'^people_export/(?P<person_org_id>\d+)/$', 'peopledetailexport', name='peopledetailexport'),      
    url(r'^file-detail/(?P<file_id>\d+)/$', 'filedetail', name='filedetail'),
    url(r'^file_export/(?P<file_id>\d+)/$', 'filedetailexport', name='filedetailexport'),  
    url(r'^about/(?P<about_id>\d+)/$', 'aboutdetail', name='aboutdetail'),
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
    url(r'^export/$', 'export', name='export'),
    url(r'^search_locations/', LocationFacetedSearchView(
        form_class = LocationFacetedSearchForm,
        template = 'search/search_locations.html',
    ), name='haystack_search_locations'),   
    url(r'^location_search_export/(?P<selected_facets>\S+)/$', 'location_search_export', name='location_search_export'),
    url(r'^search_media/', MediaFacetedSearchView(
        form_class = MediaFacetedSearchForm,
        template = 'search/search_media.html',
    ), name='haystack_search_media'),   
    url(r'^media_search_export/(?P<selected_facets>\S+)/$', 'media_search_export', name='media_search_export'),
    url(r'^search_people/', PeopleFacetedSearchView(
        form_class = PeopleFacetedSearchForm,
        template = 'search/search_people.html',
    ), name='haystack_search_people'),   
    url(r'^people_search_export/(?P<selected_facets>\S+)/$', 'people_search_export', name='people_search_export'),    
    
)
