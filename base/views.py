""" Views for the base application """

from django.shortcuts import render, get_object_or_404, render_to_response
from base.models import *
from haystack.views import SearchView
from base.forms import AdvancedSearchForm
from django.forms.formsets import formset_factory
from base import tasks
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from base.utils import get_img_ids, search_for_export, get_img_ids_spec
from django.db.models import Count
import djqscsv
from django.core import serializers
import csv
from django.http import HttpResponse

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
    if subject:
        gen_images = get_img_ids_spec(subject, 'ms', 3)
        arc_images = get_img_ids_spec(subject, 'ms', 7)
        con_images = get_img_ids_spec(subject, 'ms', 6)        
        gen_properties = subject.subjectproperty_set.filter(property__visible=True, property__data_source_type='gen')
        arc_properties = subject.subjectproperty_set.filter(property__visible=True, property__data_source_type='arc')
        con_properties = subject.subjectproperty_set.filter(property__visible=True, property__data_source_type='con')        
        control_properties = subject.subjectcontrolproperty_set.all()
        related_media = subject.mediasubjectrelations_set.filter(relation_type_id=2)
        related_web = subject.subjectlinkeddata_set.all()
        property_count = subject.subjectproperty_set.filter(property__visible=True).count() + subject.subjectcontrolproperty_set.all().count()
    else:
        gen_images = []
        arc_images = []
        con_images = []        
        gen_properties = []
        arc_properties = []
        con_properties = []
        control_properties = []
        related_media = []
        related_web = []
        property_count = 0
    return render(request, 'base/subjectdetail.html', {'subject': subject, 'gen_images': gen_images, 'con_images': con_images, 'arc_images': arc_images, 'gen_properties': gen_properties, 'con_properties': con_properties, 'arc_properties': arc_properties, 'control_properties': control_properties, 'related_media': related_media, 'related_web': related_web, 'property_count': property_count})
    
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
    
    location = get_object_or_404(Location, pk=location_id)
    if location:
        images = get_img_ids(location, 'ml')
        properties = location.locationproperty_set.filter(property__visible=True)
        related_media = location.medialocationrelations_set.filter(relation_type_id=2)
        related_objects = location.locationsubjectrelations_set.all()
    else:
        images = []
        properties = []
        related_media = []
        related_objects = []
    return render(request, 'base/locationdetail.html', {'location': location, 'images': images, 'properties': properties, 'related_media': related_media, 'related_objects': related_objects})
    
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

def propertydetail(request, prop_id):

    order = request.GET.get('o', '')
    type = request.GET.get('type', '')
    
    if not(order == 'property_value' or order == 'count' or order == '-property_value' or order == '-count'):
        order = 'property_value'
    
    prop = get_object_or_404(DescriptiveProperty, pk=prop_id)
    all_objs = None
    
    linked_data = DescPropertyLinkedData.objects.filter(desc_prop_id=prop_id)

    if prop:
        if type == 'l':
            all_objs = LocationProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)
        elif type == 'm':
            all_objs = MediaProperty.objects.filter(property_id = prop_id, media__type__id = 2).values('property_value').annotate(count = Count('property_value')).order_by(order)
        elif type == 'po':
            all_objs = PersonOrgProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)
        else: 
            all_objs = SubjectProperty.objects.filter(property_id = prop_id).values('property_value').annotate(count = Count('property_value')).order_by(order)       
            
    return render(request, 'base/propertydetail.html', {'property': prop, 'all_objs': all_objs, 'order': order, 'type': type, 'linked_data': linked_data })
        
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