""" Views for the base application """

from django.shortcuts import render, get_object_or_404, render_to_response
from base.models import *
from haystack.views import SearchView
from base.forms import AdvancedSearchForm, AdvModelSearchForm, FileUploadForm
from django.forms.formsets import formset_factory
from base import tasks
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from base.utils import get_img_ids, search_for_export, get_img_ids_spec, single_context_in_ah, single_file_upload
from django.db.models import Count
import djqscsv
from django.core import serializers
import csv
from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404
from django.utils.encoding import smart_str
from haystack.query import SQ
from datetime import datetime
from django_tables2 import RequestConfig
from base.tables import *
from base.serializers import *
from rest_framework.renderers import JSONRenderer
from rest_framework_xml.renderers import XMLRenderer
import string
from itertools import chain
from operator import attrgetter
from django.conf import settings

def create_footnotes(start_index, properties, gen_notes):
    """ Helper to create footnotes """
    #gen_notes is what ?
    #It contains objects 
    #properties of what ? What type is properties ? 
    #where is .notes defined ?
    #I think properties is a list of objects in which ".notes" is some instantaneous variable 
    

    gen_fn_count = start_index
    for gprop in properties:
        if gprop.notes != "":
            if gprop.notes in gen_notes:
                gprop.fn = gen_notes.index(gprop.notes) + 1
            else:
                gprop.fn = gen_fn_count
                gen_notes.append(gprop.notes)
                gen_fn_count += 1
    return gen_fn_count
    
def format_filename(s):
    """ Take a string and return a valid filename constructed from the string.

    Uses a whitelist approach: any characters not present in valid_chars are
    removed. Also spaces are replaced with underscores.
    
    Note: this method may produce invalid filenames such as ``, `.` or `..`
    When I use this method I prepend a date string like '2009_01_15_19_46_32_'
    and append a file extension like '.txt', so I avoid the potential of using
    an invalid filename. 
    
    Taken from: https://gist.github.com/seanh/93666. """
    
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace(' ','_') # I don't like spaces in filenames.
    return filename
    
class JSONResponse(HttpResponse):
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)
        
class XMLResponse(HttpResponse):
    def __init__(self, data, **kwargs):
        content = XMLRenderer().render(data)
        kwargs['content_type'] = 'text/xml'
        super (XMLResponse, self).__init__(content, **kwargs)

def home(request):
    """ Default view for the root """
	
    return render(request, 'base/home.html')
    
def map(request):

    return render(request, 'base/map.html')
    
def subjectdetail(request, subject_id):
    """ Detailed view of a subject record """
    
    subject = get_object_or_404(Subject, pk=subject_id)
    if subject:      
        gen_properties = subject.subjectproperty_set.filter(property__visible=True, property__property_type__id=1)
        arc_properties = subject.subjectproperty_set.filter(property__visible=True, property__property_type__id=3)
        con_properties = subject.subjectproperty_set.filter(property__visible=True, property__property_type__id=2)        
        gen_control_properties = subject.subjectcontrolproperty_set.filter(control_property__property_type__id=1).order_by('control_property__order')
        arc_control_properties = subject.subjectcontrolproperty_set.filter(control_property__property_type__id=3).order_by('control_property__order')
        con_control_properties = subject.subjectcontrolproperty_set.filter(control_property__property_type__id=2).order_by('control_property__order')        
        related_media = subject.mediasubjectrelations_set.filter(relation_type_id=2)
        related_web = subject.subjectlinkeddata_set.all()
        property_count = subject.subjectproperty_set.filter(property__visible=True).count() + subject.subjectcontrolproperty_set.all().count()
    else:     
        gen_properties = []
        arc_properties = []
        con_properties = []
        gen_control_properties = []
        arc_control_properties = []
        con_control_properties = []        
        related_media = []
        related_web = []
        property_count = 0
        
    # files
    files = {}
    files[''] = []
    files_list = SubjectFile.objects.filter(subject = subject)
    for file in files_list:
        cols = FileCollection.objects.filter(file = file.rsid)
        if not cols:
            files[''].append(file)
        else:
            for col in cols:
                if not col.collection.title in files.keys():
                    files[col.collection.title] = [file]
                else:
                    files[col.collection.title].append(file)     
        
    gen_notes = []
    gen_index = create_footnotes(1, gen_control_properties, gen_notes)
    create_footnotes(gen_index, gen_properties, gen_notes)
    
    arc_notes = []
    arc_index = create_footnotes(1, arc_control_properties, arc_notes)
    create_footnotes(arc_index, arc_properties, arc_notes)

    con_notes = []
    con_index = create_footnotes(1, con_control_properties, con_notes)
    create_footnotes(con_index, con_properties, con_notes) 
    
    return render(request, 'base/subjectdetail.html', {'subject': subject, 'gen_properties': gen_properties, 'con_properties': con_properties, 'arc_properties': arc_properties, 'control_properties': gen_control_properties, 'arc_control_properties': arc_control_properties, 'con_control_properties': con_control_properties, 'related_media': related_media, 'related_web': related_web, 'property_count': property_count, 'gen_footnotes': gen_notes, 'arc_footnotes': arc_notes, 'con_footnotes': con_notes, 'files': files})
    
def mediadetail(request, media_id):
    """ Detailed view of a media record """
    
    isfile = request.GET.get('isfile', '')
    
    media = get_object_or_404(Media, pk=media_id)
    if media:
        if isfile == 'true':
            images = get_img_ids(media, 'mf')
            '''current_page_qs = MediaProperty.objects.filter(media_id = media.id, property_id = 122)
            if current_page_qs:
                if isfloat(current_page_qs[0].property_value):
                    current_page = int(float(current_page_qs[0].property_value))
                    current_vol_qs = MediaProperty.objects.filter(media_id = media.id, property_id = 123)
                    if current_vol_qs:
                        current_vol = current_vol_qs[0].property_value
                        next_page_qs = MediaProperty.objects.filter(property_id = 122, property_value = current_page + 1)
                        if next_page_qs:
                            for item in next_page_qs:
                                next_vol_qs = MediaProperty.objects.filter(property_id = 123, media_id = item.id, property_value = current_vol)'''
        else:
            images = get_img_ids(media, 'mm')
        properties = media.mediaproperty_set.filter(property__visible=True).order_by('property__order')
        related_objects = media.mediasubjectrelations_set.all()[:10]
        related_web = media.medialinkeddata_set.all()
    else:
        images = []
        properties = []
        related_objects = []
        related_web = []
    return render(request, 'base/mediadetail.html', {'media': media, 'images': images, 'properties': properties, 'related_objects': related_objects, 'related_web': related_web})
    
def personorgdetail(request, personorg_id):
    """ Detailed view of a person/organization record """
    
    personorg = get_object_or_404(PersonOrg, pk=personorg_id)
    if personorg:
        images = get_img_ids(personorg, 'mpo')
        properties = personorg.personorgproperty_set.filter(property__visible=True)
        related_media = personorg.mediapersonorgrelations_set.filter(relation_type_id=2)
        related_web = personorg.personorglinkeddata_set.all()
        property_count = personorg.personorgproperty_set.filter(property__visible=True).count()
    else:
        images = []        
        properties = []
        related_media = []
        related_web = []
        property_count = 0
    return render(request, 'base/personorgdetail.html', {'personorg': personorg, 'images': images, 'properties': properties, 'related_media': related_media, 'related_web': related_web, 'property_count': property_count})
    
def locationdetail(request, location_id):

    # get the parameters
    location = get_object_or_404(Location, pk=location_id)
    sub_coll_id = request.GET.get('subcol', '')    
    med_coll_id = request.GET.get('medcol', '')
    po_coll_id = request.GET.get('pocol', '')
    
    show_contents = 'false'
    sub_col_title = ''
    med_col_title = ''
    po_col_title = ''
    
    # getting rid of this stuff
    related_media = location.medialocationrelations_set.filter(relation_type_id=2)
    
    location_tree = location.get_descendants(include_self=True)
    
    # properties
    control_properties = LocationControlProperty.objects.filter(location = location, control_property__visible=True).exclude(control_property__in = DescriptiveProperty.objects.filter(resultproperty__display_field__startswith = 'loc_title'))
    ff_properties = LocationProperty.objects.filter(location = location, property__visible=True).exclude(property__in = DescriptiveProperty.objects.filter(resultproperty__display_field__startswith = 'loc_title'))
    # magic to combine both property types and sort by their order fields
    sorted_properties = sorted(chain(control_properties, ff_properties), key = lambda property: property.property.order if hasattr(property, 'property') else property.control_property.order)
    # notes
    footnotes = []
    create_footnotes(1, sorted_properties, footnotes)
    properties = {}
    properties[''] = []
    for p in sorted_properties:
        if hasattr(p, 'property') and p.property.property_type:
            pt = p.property.property_type.type
        elif hasattr(p, 'control_property') and p.control_property.property_type:
            pt = p.control_property.property_type.type
        else:
            pt = ''
        if not pt in properties.keys():
            properties[pt] = [p]
        else:
            properties[pt].append(p)
            
    # files
    files = {}
    files[''] = []
    files_list = LocationFile.objects.filter(location = location)
    for file in files_list:
        cols = FileCollection.objects.filter(file = file.rsid)
        if not cols:
            files[''].append(file)
        else:
            for col in cols:
                if not col.collection.title in files.keys():
                    files[col.collection.title] = [file]
                else:
                    files[col.collection.title].append(file)    
    
    # objects
    subjects = Subject.objects.filter(locationsubjectrelations__location__in = location.get_descendants(include_self = True)).distinct()
    # media
    media = Media.objects.filter(medialocationrelations__location__in = location.get_descendants(include_self = True)).distinct()
    # people/organizations
    people = PersonOrg.objects.filter(locationpersonorgrelations__location__in = location.get_descendants(include_self = True)).distinct()
    
    # collections that include the selected objects
    scs = SubjectCollection.objects.filter(subject__in = subjects)
    subject_collections = Collection.objects.filter(subjectcollection__in = scs).distinct()
    # collections that include the selected media
    mcs = MediaCollection.objects.filter(media__in = media)
    media_collections = Collection.objects.filter(mediacollection__in = mcs).distinct() 
    # collections that include the selected people
    pocs = PersonOrgCollection.objects.filter(person_org__in = people)
    po_collections = Collection.objects.filter(personorgcollection__in = pocs).distinct()
    
    # if a specific collection was requested, get only objects in selected collection
    if sub_coll_id != '' and sub_coll_id != '0':
        selected_cols = Collection.objects.filter(pk=sub_coll_id)
        if selected_cols:
            subjects = subjects.filter(subjectcollection__collection = selected_cols[0])
            sub_col = Collection.objects.filter(pk=sub_coll_id)
            if sub_col:
                sub_col_title = sub_col[0].title
    # if a specific collection was requested, get only media in selected collection
    if med_coll_id != '' and med_coll_id != '0':
        selected_cols = Collection.objects.filter(pk=med_coll_id)
        if selected_cols:
            media = media.filter(mediacollection__collection = selected_cols[0])
            med_col = Collection.objects.filter(pk=med_coll_id)
            if med_col:
                med_col_title = med_col[0].title
    # if a specific collection was requested, get only people in selected collection
    if po_coll_id != '' and po_coll_id != '0':
        selected_cols = Collection.objects.filter(pk=po_coll_id)
        if selected_cols:
            people = people.filter(personorgcollection__collection = selected_cols[0])
            po_col = Collection.objects.filter(pk=po_coll_id)
            if po_col:
                po_col_title = po_col[0].title
    
    # create the object table
    subject_table = SubjectTable(subjects, prefix='subj-')
    RequestConfig(request).configure(subject_table)
    # create the media table
    media_table = MediaTable(media, prefix='med-')
    RequestConfig(request).configure(media_table)    
    # create the people table
    people_table = PersonOrgTable(people, prefix='po-')
    RequestConfig(request).configure(people_table)        
    
    # determine if menu is needed
    if subjects or media or people or location.get_siblings or location.get_children:
        show_contents = 'true'
    
    return render(request, 'base/locationdetail.html', {'location': location, 'subjects': subjects, 'media': media, 'show_contents': show_contents, 'subject_table': subject_table, 'media_table': media_table, 'people_table': people_table, 'subject_collections': subject_collections, 'media_collections': media_collections, 'po_collections': po_collections, 'sub_col': sub_coll_id, 'med_col': med_coll_id, 'po_col': po_coll_id, 'sub_col_title': sub_col_title, 'med_col_title': med_col_title, 'po_col_title': po_col_title, 'files': files, 'properties': properties, 'footnotes': footnotes, 'related_media': related_media })
    
def locationdetailexport (request, location_id):
    
    # get the parameters
    location = get_object_or_404(Location, pk=location_id)
    coll_id = request.GET.get('col', '')
    entity = request.GET.get('entity', '')
    format = request.GET.get('format', '')
    
    filename = location.title
    
    # subject export
    if entity == 'subject':
        filename += '_objects_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = Subject.objects.filter(locationsubjectrelations__location__in = location.get_descendants(include_self = True))
        
        # if a specific collection was requested, get only objects in selected collection
        if coll_id != '' and coll_id != '0':
            selected_cols = Collection.objects.filter(pk=coll_id)
            if selected_cols:
                qs = qs.filter(subjectcollection__collection = selected_cols[0])
                filename += '_collection-' + format_filename(selected_cols[0].title)
                
    # media export
    if entity == 'media':
        filename += '_media_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = Media.objects.filter(medialocationrelations__location__in = location.get_descendants(include_self = True))
        
        # if a specific collection was requested, get only media in selected collection
        if coll_id != '' and coll_id != '0':
            selected_cols = Collection.objects.filter(pk=coll_id)
            if selected_cols:
                qs = qs.filter(mediacollection__collection = selected_cols[0])
                filename += '_collection-' + format_filename(selected_cols[0].title)

    # people export
    if entity == 'people':
        filename += '_people_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = PersonOrg.objects.filter(locationpersonorgrelations__location__in = location.get_descendants(include_self = True))
        
        # if a specific collection was requested, get only people in selected collection
        if coll_id != '' and coll_id != '0':
            selected_cols = Collection.objects.filter(pk=coll_id)
            if selected_cols:
                qs = qs.filter(personorgcollection__collection = selected_cols[0])
                filename += '_collection-' + format_filename(selected_cols[0].title)     
                
    if qs:
        # json
        if format == 'json':
            if entity == 'subject':
                serializer = SubjectSerializer(qs, many=True)
            elif entity == 'media':
                serializer = MediaSerializer(qs, many=True)
            elif entity == 'people':
                serializer = PersonOrgSerializer(qs, many=True)                
            response = JSONResponse(serializer.data)
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.json"'
            return response
            
        # xml
        elif format == 'xml':
            if entity == 'subject':
                serializer = SubjectSerializer(qs, many=True)
            elif entity == 'media':
                serializer = MediaSerializer(qs, many=True)
            elif entity == 'people':
                serializer = PersonOrgSerializer(qs, many=True)
            response = XMLResponse(serializer.data)
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.xml"'
            return response
            
        # csv - evil, evil, flattened csv
        elif format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.csv"'

            writer = csv.writer(response)
            titles = []
            titles.append('__Title__')
            titles.append('__URL__')
            rows = []
            for result in qs:
                row = []
                row_dict = {}
                
                # store title and url
                row_dict[0] = result.title
                row_dict[1] = result.get_full_absolute_url()
                
                # controlled properties
                if entity == 'subject':
                    cps = result.subjectcontrolproperty_set.all()
                elif entity == 'media':
                    cps = result.mediacontrolproperty_set.all()
                else:
                    cps = result.personorgcontrolproperty_set.all()                    
                for each_prop in cps:
                    if each_prop.control_property.visible:
                        prop_name = each_prop.control_property.property.strip()
                        prop_value = each_prop.control_property_value.title.strip()
                        if not (prop_name in titles):
                            column_index = len(titles)                        
                            titles.append(prop_name)
                        else:
                            column_index = titles.index(prop_name)
                            if column_index in row_dict:
                                prop_value = row_dict[column_index] + '; ' + prop_value
                        row_dict[column_index] = prop_value
                
                # free-form properties
                if entity == 'subject':
                    ps = result.subjectproperty_set.all()
                elif entity == 'media':
                    ps = result.mediaproperty_set.all()
                else:
                    ps = result.personorgproperty_set.all()                  
                for each_prop in ps:
                    if each_prop.property.visible:
                        prop_name = each_prop.property.property.strip()
                        prop_value = each_prop.property_value.strip()
                        if not (prop_name in titles):
                            column_index = len(titles)                        
                            titles.append(prop_name)
                        else:
                            column_index = titles.index(prop_name)
                            if column_index in row_dict:
                                prop_value = row_dict[column_index] + '; ' + prop_value
                        row_dict[column_index] = prop_value                    
                                
                # store row in list
                for i in range(len(titles)):
                    if i in row_dict:
                        row.append(row_dict[i])
                    else:
                        row.append('')
                rows.append(row)

            # write out the rows, starting with header
            writer.writerow(titles)
            for each_row in rows:
                writer.writerow(each_row)
            return response
    
def search_help(request):

    return render(request, 'base/search_help.html')
    
def help(request):

    return render(request, 'base/help.html')
    
def about(request):

    project = get_object_or_404(SiteContent, variable='about_project')
    site = get_object_or_404(SiteContent, variable='about_site')
    excavation = get_object_or_404(SiteContent, variable='about_excavation')
    team = get_object_or_404(SiteContent, variable='about_team')
    support = get_object_or_404(SiteContent, variable='about_support')
    dev = get_object_or_404(SiteContent, variable='about_dev')
    lic = get_object_or_404(SiteContent, variable='about_lic')
    
    return render(request, 'base/about.html', {'project': project, 'site': site, 'excavation': excavation, 'team': team, 'support': support, 'dev': dev, 'lic': lic })
    
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

def propertydetail(request, prop_id):

    order = request.GET.get('o', '')
    type = request.GET.get('type', '')
    
    prop = get_object_or_404(DescriptiveProperty, pk=prop_id)
    
    if not(order == 'property_value' or order == 'count' or order == '-property_value' or order == '-count'):
            order = 'property_value'

    all_objs = None
    
    linked_data = DescPropertyLinkedData.objects.filter(desc_prop_id=prop_id)

    if prop:
        if prop.facet:
            all_objs = ControlField.objects.filter(type_id = prop_id)
        elif type == 'l':
            all_objs = LocationProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)
        elif type == 'm':
            all_objs = MediaProperty.objects.filter(property_id = prop_id, media__type__id = 2).values('property_value').annotate(count = Count('property_value')).order_by(order)
        elif type == 'po':
            all_objs = PersonOrgProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)
        else: 
            all_objs = SubjectProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)       
            
    return render(request, 'base/propertydetail.html', {'property': prop, 'all_objs': all_objs, 'order': order, 'type': type, 'linked_data': linked_data })
    
def terminology(request):

    cntl_props = DescriptiveProperty.objects.filter(control_field = True, visible = True).order_by('order')

    return render(request, 'base/terminology.html', {'cntl_props': cntl_props})
    
def collections(request):

    collections = Collection.objects.filter(public = True)

    return render(request, 'base/collections.html', {'collections': collections})
    
def termdetail(request, term_id):
    
    # get the parameters
    term = get_object_or_404(ControlField, pk=term_id)
    sub_coll_id = request.GET.get('subcol', '')
    loc_coll_id = request.GET.get('loccol', '')    
    
    show_contents = 'false'
    sub_col_title = ''
    loc_col_title = ''
    
    # linked data
    linked_data = ControlFieldLinkedData.objects.filter(control_field_id=term_id)

    # objects
    subjects = Subject.objects.filter(subjectcontrolproperty__control_property_value__in = term.get_descendants(include_self = True)).distinct()
    # locations
    locations = Location.objects.filter(locationcontrolproperty__control_property_value__in = term.get_descendants(include_self = True)).distinct()    
    
    # collections that include the selected objects
    scs = SubjectCollection.objects.filter(subject__in = subjects)
    subject_collections = Collection.objects.filter(subjectcollection__in = scs).distinct()
    # collections that include the selected locations
    lcs = LocationCollection.objects.filter(location__in = locations)
    location_collections = Collection.objects.filter(locationcollection__in = lcs).distinct()     
    
    # if a specific collection was requested, get only objects in selected collection
    if sub_coll_id != '' and sub_coll_id != '0':
        selected_cols = Collection.objects.filter(pk=sub_coll_id)
        if selected_cols:
            subjects = subjects.filter(subjectcollection__collection = selected_cols[0])
            sub_col = Collection.objects.filter(pk=sub_coll_id)
            if sub_col:
                sub_col_title = sub_col[0].title
    # if a specific collection was requested, get only locations in selected collection
    if loc_coll_id != '' and loc_coll_id != '0':
        selected_cols = Collection.objects.filter(pk=loc_coll_id)
        if selected_cols:
            locations = locations.filter(locationcollection__collection = selected_cols[0])
            loc_col = Collection.objects.filter(pk=loc_coll_id)
            if loc_col:
                loc_col_title = loc_col[0].title                
    
    # create the object table
    subject_table = SubjectTable(subjects, prefix='subj-')
    RequestConfig(request).configure(subject_table)
    # create the location table
    location_table = LocationTable(locations, prefix='loc-')
    RequestConfig(request).configure(location_table)    
    
    # determine if menu is needed
    if linked_data or subjects or locations or term.get_siblings_same_type or term.get_children_same_type:
        show_contents = 'true'
    
    return render(request, 'base/termdetail.html', {'term': term, 'subjects': subjects, 'locations': locations, 'linked_data': linked_data, 'show_contents': show_contents, 'subject_table': subject_table, 'location_table': location_table, 'subject_collections': subject_collections, 'location_collections': location_collections, 'sub_col': sub_coll_id, 'loc_col': loc_coll_id, 'sub_col_title': sub_col_title, 'loc_col_title': loc_col_title })
    
def termdetailexport (request, term_id):
    
    # get the parameters
    term = get_object_or_404(ControlField, pk=term_id)
    coll_id = request.GET.get('col', '')
    entity = request.GET.get('entity', '')
    format = request.GET.get('format', '')
    
    filename = term.title
    
    # subject export
    if entity == 'subject':
        filename += '_objects_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = Subject.objects.filter(subjectcontrolproperty__control_property_value__in = term.get_descendants(include_self = True))
        
        # if a specific collection was requested, get only objects in selected collection
        if coll_id != '' and coll_id != '0':
            selected_cols = Collection.objects.filter(pk=coll_id)
            if selected_cols:
                qs = qs.filter(subjectcollection__collection = selected_cols[0])
                filename += '_collection-' + format_filename(selected_cols[0].title)
                
    # location export
    if entity == 'location':
        filename += '_locations_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = Location.objects.filter(locationcontrolproperty__control_property_value__in = term.get_descendants(include_self = True))
        
        # if a specific collection was requested, get only objects in selected collection
        if coll_id != '' and coll_id != '0':
            selected_cols = Collection.objects.filter(pk=coll_id)
            if selected_cols:
                qs = qs.filter(locationcollection__collection = selected_cols[0])
                filename += '_collection-' + format_filename(selected_cols[0].title)        
                
    if qs:
        # json
        if format == 'json':
            if entity == 'location':
                serializer = LocationSerializer(qs, many=True)
            else:
                serializer = SubjectSerializer(qs, many=True)
            response = JSONResponse(serializer.data)
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.json"'
            return response
            
        # xml
        elif format == 'xml':
            if entity == 'location':
                serializer = LocationSerializer(qs, many=True)
            else:
                serializer = SubjectSerializer(qs, many=True)
            response = XMLResponse(serializer.data)
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.xml"'
            return response
            
        # csv - evil, evil, flattened csv
        elif format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.csv"'

            writer = csv.writer(response)
            titles = []
            titles.append('__Title__')
            titles.append('__URL__')
            rows = []
            for result in qs:
                row = []
                row_dict = {}
                
                # store title and url
                row_dict[0] = result.title
                row_dict[1] = result.get_full_absolute_url()
                
                # controlled properties
                if entity == 'location':
                    cps = result.locationcontrolproperty_set.all()
                else:
                    cps = result.subjectcontrolproperty_set.all()
                for each_prop in cps:
                    if each_prop.control_property.visible:
                        prop_name = each_prop.control_property.property.strip()
                        prop_value = each_prop.control_property_value.title.strip()
                        if not (prop_name in titles):
                            column_index = len(titles)                        
                            titles.append(prop_name)
                        else:
                            column_index = titles.index(prop_name)
                            if column_index in row_dict:
                                prop_value = row_dict[column_index] + '; ' + prop_value
                        row_dict[column_index] = prop_value
                
                # free-form properties
                if entity == 'location':
                    ps = result.locationproperty_set.all()
                else:
                    ps = result.subjectproperty_set.all()                
                for each_prop in ps:
                    if each_prop.property.visible:
                        prop_name = each_prop.property.property.strip()
                        prop_value = each_prop.property_value.strip()
                        if not (prop_name in titles):
                            column_index = len(titles)                        
                            titles.append(prop_name)
                        else:
                            column_index = titles.index(prop_name)
                            if column_index in row_dict:
                                prop_value = row_dict[column_index] + '; ' + prop_value
                        row_dict[column_index] = prop_value                    
                                
                # store row in list
                for i in range(len(titles)):
                    if i in row_dict:
                        row.append(row_dict[i])
                    else:
                        row.append('')
                rows.append(row)

            # write out the rows, starting with header
            writer.writerow(titles)
            for each_row in rows:
                writer.writerow(each_row)
            return response
    
def mapdetail(request, location_id):
    
    current_map_id = request.GET.get('mapid', '')
    location = get_object_or_404(Location, pk = location_id)
    maps = MediaLocationRelations.objects.filter(location__id = location_id, relation_type_id = 9)
    
    if current_map_id == '':
        current_map = get_object_or_404(Media, pk = maps[0].media_id)
        maps = maps[1:]
    else:
        maps = maps.exclude(media_id = current_map_id)
        current_map = get_object_or_404(Media, pk = current_map_id)
    
    other_maps = []
    for m in maps:
        try:
            id_pair = (m.media_id, m.media.notes, MediaProperty.objects.filter(media_id = m.media_id, property_id = 94)[0].property_value)
            other_maps.append(id_pair)
        except IndexError:
            continue
    
    loci = MediaLocationRelations.objects.filter(media_id = current_map.id, relation_type = 10).order_by('location__title')
    
    loci_details = {}
    for locus in loci:
        context = LocationProperty.objects.filter(Q(property_id = 96) | Q(property_id = 117), location = locus.location)
        if context:
            loci_details[locus.location.id] = context[0].property_value
    try:
        rsid = MediaProperty.objects.filter(media_id = current_map.id, property_id = 94)[0]
    except IndexError:
        raise Http404("Could not find map image")
    
    return render(request, 'base/mapdetail.html', {'location': location, 'current_map': current_map, 'other_maps': other_maps, 'loci': loci, 'rsid': rsid, 'loci_details': loci_details})
    
def collectiondetail(request, collection_id):
    
    # get the parameters
    collection = get_object_or_404(Collection, pk=collection_id)    
    
    show_contents = 'false'
    
    # objects
    subjects = Subject.objects.filter(subjectcollection__collection = collection).distinct()
    # locations
    locations = Location.objects.filter(locationcollection__collection = collection).distinct()    
    # media
    media = Media.objects.filter(mediacollection__collection = collection).distinct()    
    # people
    people = PersonOrg.objects.filter(personorgcollection__collection = collection).distinct()    
            
    # create the object table
    subject_table = SubjectTable(subjects, prefix='subj-')
    RequestConfig(request).configure(subject_table)
    # create the location table
    location_table = LocationTable(locations, prefix='loc-')
    RequestConfig(request).configure(location_table)
    # create the media table
    media_table = MediaTable(media, prefix='med-')
    RequestConfig(request).configure(media_table)  
    # create the people table
    people_table = PersonOrgTable(people, prefix='po-')
    RequestConfig(request).configure(people_table)  
    
    # determine if menu is needed
    if subjects or locations or media or people:
        show_contents = 'true'
    
    return render(request, 'base/collectiondetail.html', {'collection': collection, 'subjects': subjects, 'locations': locations, 'media': media, 'people': people, 'show_contents': show_contents, 'subject_table': subject_table, 'location_table': location_table, 'media_table': media_table, 'people_table': people_table })
        
def export_property_details(request, prop_id):
    order = request.GET.get('o', '')
    type = request.GET.get('type', '')

    if not(order == 'property_value' or order == 'count' or order == '-property_value' or order == '-count'):
        order = 'property_value'

    prop = get_object_or_404(DescriptiveProperty, pk=prop_id)        
    all_objs = None

    if prop:
        if type == 'l':
            all_objs = LocationProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)
        elif type == 'm':
            all_objs = MediaProperty.objects.filter(property_id = prop_id, media__type__id = 2).values('property_value').annotate(count = Count('property_value')).order_by(order)
        elif type == 'po':
            all_objs = PersonOrgProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)
        else: 
            all_objs = SubjectProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="property_detail.csv"'

    writer = csv.writer(response)
    writer.writerow(['Property Value', 'Count'])
    for obj in all_objs:
        writer.writerow([str(obj['property_value']), obj['count']])
    return response
    
def export_control_property_details(request, prop_id):

    prop = get_object_or_404(DescriptiveProperty, pk=prop_id)        
    all_objs = None

    if prop:
        all_objs = ControlField.objects.filter(type_id = prop_id)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="' + prop.property + '_property_detail.csv"'

    writer = csv.writer(response)
    writer.writerow(['Parent Category', 'Property Value', 'Definition', 'Specific Count', 'Cumulative Count'])
    for obj in all_objs:
        ancs = obj.ancestors()
        spec_count = SubjectControlProperty.objects.filter(control_property_value_id = obj.id).count()
        cum_count = obj.count_subj_instances()
        desc = obj.definition.encode('ascii', 'ignore')
        writer.writerow([ancs, obj.title, desc, spec_count, cum_count])
    return response
    
def export_search_results(request):
    p1 = request.GET.get('p1', '')
    st1 = request.GET.get('st1', '')
    q1 = request.GET.get('q1', '')
    op1 = request.GET.get('op1', '')
    p2 = request.GET.get('p2', '')
    st2 = request.GET.get('st2', '')
    q2 = request.GET.get('q2', '')
    op2 = request.GET.get('op2', '')
    p3 = request.GET.get('p3', '')
    st3 = request.GET.get('st3', '')
    q3 = request.GET.get('q3', '')
    order = request.GET.get('order', '')

    qs = search_for_export(p1, st1, q1, op1, p2, st2, q2, op2, p3, st3, q3, order) 
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="search_result.csv"'

    writer = csv.writer(response)
    flattened_result = {}
    for result in qs:
        pkey = result.pk
        props = SubjectProperty.objects.filter(subject_id = pkey, property__visible = True)
        for each_prop in props:
            prop_name = str(each_prop.property.property)
            prop_value = str(each_prop.property_value)
            if not (prop_name in flattened_result):
                flattened_result[prop_name] = {pkey: prop_value}
            else:
                current_property = flattened_result[prop_name]
                if pkey in current_property:
                    current_property[pkey] != '; ' + prop_value
                else:
                    current_property[pkey] = prop_value

    titles = []
    for k in flattened_result:
        titles.append(k)
    writer.writerow(titles)
    for result in qs:
        row = []
        for k in flattened_result:
            prop_dict = flattened_result[k]
            if result.pk in prop_dict:
                row.append(prop_dict[result.pk])
            else:
                row.append('')
        writer.writerow(row)
    return response
    
def kyra_special_ah(request):
    ids = single_context_in_ah()
    special_objects = Subject.objects.filter(id__in = ids)
    subj_titles = ResultProperty.objects.filter(display_field__startswith = 'subj_title').order_by('display_field')
    return render(request, 'base/single_loc_in_ah.html', {'special_objects':special_objects, 'titles':subj_titles})
    
def kyra_special_2(request):
    """ List of weights from Brad """
    special_objects = Subject.objects.filter(subjectproperty__notes = 'Data recorded by Dr. William B. Hafford.').distinct()
    subj_titles = ResultProperty.objects.filter(display_field__startswith = 'subj_title').order_by('display_field')
    return render(request, 'base/kyra_special_2.html', {'special_objects':special_objects, 'titles':subj_titles})
    
def search_export(request, selected_facets):
    if request.method == 'GET':
        form = AdvModelSearchForm(request.GET)
        if form.is_valid():
            qs = form.search()
            
            #deal with facets
            facets = selected_facets.split("&")
            
            for facet in facets:
                if ":" not in facet:
                    continue

                field, value = facet.split(":", 1)

                if value:
                    control_value = ControlField.objects.filter(pk=qs.query.clean(value))
                    if control_value:
                        value_tree = control_value[0].get_descendants(include_self=True)
                        sq = SQ()
                        for index, node in enumerate(value_tree):
                            kwargs = {str("%s" % (field)) : str("%s" % (node.id))}
                            if index == 0:
                                sq = SQ(**kwargs)
                            else:
                                sq = sq | SQ(**kwargs)
                        qs = qs.filter(sq)                
            
            response = HttpResponse(content_type='text/csv')
            filename_str = '"search_results_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S") + '.csv"'
            response['Content-Disposition'] = 'attachment; filename=' + filename_str

            writer = csv.writer(response)
            titles = []
            rows = []
            for result in qs:
                row = []
                row_dict = {}
                properties = result.text
                for each_prop in properties:
                    prop_pair = each_prop.split(':', 1)
                    if len(prop_pair) < 2:
                        continue
                    prop_name = smart_str(prop_pair[0].strip())
                    prop_value = smart_str(prop_pair[1].strip())
                    if not (prop_name in titles):
                        column_index = len(titles)                        
                        titles.append(prop_name)
                    else:
                        column_index = titles.index(prop_name)
                        if column_index in row_dict:
                            prop_value = row_dict[column_index] + '; ' + prop_value
                    row_dict[column_index] = prop_value
                for i in range(len(titles)):
                    if i in row_dict:
                        row.append(row_dict[i])
                    else:
                        row.append('')
                rows.append(row)

            writer.writerow(titles)
            for each_row in rows:
                writer.writerow(each_row)
            return response
    
    return HttpResponseRedirect('/failed_export/')

def bulk_update_subject(request):
    ids = request.GET.get('ids', '')
    subs = ids.split(",")
    objects = Subject.objects.filter(id__in=subs)
    props = DescriptiveProperty.objects.filter(control_field = False)
    control_props = DescriptiveProperty.objects.filter(control_field = True)
    control_prop_values = ControlField.objects.all()
    locations = Location.objects.all()
    
    return render(request, 'admin/base/subject/bulk_update_subject.html', {'objects': objects, 'props': props, 'control_props': control_props, 'control_prop_values': control_prop_values, 'locations': locations})
    
def collectiondetailexport(request, collection_id):

    # get the parameters
    collection = get_object_or_404(Collection, pk=collection_id)
    entity = request.GET.get('entity', '')
    format = request.GET.get('format', '')
    all = request.GET.get('a', '')
    
    filename = collection.title
    
    # subject export
    if entity == 'subject':
        filename += '_objects_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = Subject.objects.filter(subjectcollection__collection = collection)
                        
    # location export
    if entity == 'location':
        filename += '_locations_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = Location.objects.filter(locationcollection__collection = collection)
        
    # media export
    if entity == 'media':
        filename += '_media_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = Media.objects.filter(mediacollection__collection = collection)

    # person/org export
    if entity == 'people':
        filename += '_people_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        qs = PersonOrg.objects.filter(personorgcollection__collection = collection)        
                        
    if qs:
        # json
        if format == 'json':
            if all == 'y':
                if entity == 'location':
                    serializer = LocationAdminSerializer(qs, many=True)
                elif entity == 'media':
                    serializer = MediaAdminSerializer(qs, many=True)
                elif entity == 'people':
                    serializer = PersonOrgAdminSerializer(qs, many=True)                
                else:
                    serializer = SubjectAdminSerializer(qs, many=True)
            else:
                if entity == 'location':
                    serializer = LocationSerializer(qs, many=True)
                elif entity == 'media':
                    serializer = MediaSerializer(qs, many=True)
                elif entity == 'people':
                    serializer = PersonOrgSerializer(qs, many=True)                
                else:
                    serializer = SubjectSerializer(qs, many=True)            
            response = JSONResponse(serializer.data)
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.json"'
            return response
            
        # xml
        elif format == 'xml':
            if all == 'y':
                if entity == 'location':
                    serializer = LocationAdminSerializer(qs, many=True)
                elif entity == 'media':
                    serializer = MediaAdminSerializer(qs, many=True)
                elif entity == 'people':
                    serializer = PersonOrgAdminSerializer(qs, many=True)                 
                else:
                    serializer = SubjectAdminSerializer(qs, many=True)
            else:
                if entity == 'location':
                    serializer = LocationSerializer(qs, many=True)
                elif entity == 'media':
                    serializer = MediaSerializer(qs, many=True)
                elif entity == 'people':
                    serializer = PersonOrgSerializer(qs, many=True)                 
                else:
                    serializer = SubjectSerializer(qs, many=True)
            
            response = XMLResponse(serializer.data)
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.xml"'
            return response
            
        # csv - evil, evil, flattened csv
        elif format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="' + filename + '.csv"'

            writer = csv.writer(response)
            titles = []
            titles.append('__Title__')
            titles.append('__URL__')
            rows = []
            for result in qs:
                row = []
                row_dict = {}
                
                # store title and url
                row_dict[0] = result.title
                row_dict[1] = result.get_full_absolute_url()
                
                # controlled properties
                if entity == 'location':
                    cps = result.locationcontrolproperty_set.all()
                elif entity == 'media':
                    cps = result.mediacontrolproperty_set.all()
                elif entity == 'people':
                    cps = result.personorgcontrolproperty_set.all()
                else:
                    cps = result.subjectcontrolproperty_set.all()
                for each_prop in cps:
                    if each_prop.control_property.visible:
                        prop_name = each_prop.control_property.property.strip()
                        prop_value = each_prop.control_property_value.title.strip()
                        if not (prop_name in titles):
                            column_index = len(titles)                        
                            titles.append(prop_name)
                        else:
                            column_index = titles.index(prop_name)
                            if column_index in row_dict:
                                prop_value = row_dict[column_index] + '; ' + prop_value
                        row_dict[column_index] = prop_value
                
                # free-form properties
                if entity == 'location':
                    ps = result.locationproperty_set.all()
                elif entity == 'media':
                    ps = result.mediaproperty_set.all()
                elif entity == 'people':
                    ps = result.personorgproperty_set.all()                    
                else:
                    ps = result.subjectproperty_set.all()                
                for each_prop in ps:
                    if each_prop.property.visible:
                        prop_name = each_prop.property.property.strip()
                        prop_value = each_prop.property_value.strip()
                        if not (prop_name in titles):
                            column_index = len(titles)                        
                            titles.append(prop_name)
                        else:
                            column_index = titles.index(prop_name)
                            if column_index in row_dict:
                                prop_value = row_dict[column_index] + '; ' + prop_value
                        row_dict[column_index] = prop_value                    
                                
                # store row in list
                for i in range(len(titles)):
                    if i in row_dict:
                        row.append(row_dict[i])
                    else:
                        row.append('')
                rows.append(row)

            # write out the rows, starting with header
            writer.writerow(titles)
            for each_row in rows:
                writer.writerow(each_row)
            return response
            
def bulk_upload_file(request):
    tasks.bulk_file_upload()
    return HttpResponseRedirect(request.GET.get('next'))
    
def addfile(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            with open(settings.FILE_UPLOAD_FOLDER + '/' + file.name, 'wb+') as destination:
                for chunk in request.FILES['file'].chunks():
                    destination.write(chunk)
            new_file = single_file_upload(str(file.name))
            return HttpResponseRedirect("../%s" % new_file)
    else:
        form = FileUploadForm()
    return render(request, 'admin/base/file/add_form.html', {'form': form})