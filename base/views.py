""" Views for the base application """

from django.shortcuts import render, get_object_or_404, render_to_response
from base.models import *
from haystack.views import SearchView
from base.forms import AdvancedSearchForm, AdvModelSearchForm
from django.forms.formsets import formset_factory
from base import tasks
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from base.utils import get_img_ids, search_for_export, get_img_ids_spec, single_context_in_ah
from django.db.models import Count
import djqscsv
from django.core import serializers
import csv
from django.http import HttpResponse
from django.http import Http404
from django.utils.encoding import smart_str
from haystack.query import SQ
from datetime import datetime

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
        gen_control_properties = subject.subjectcontrolproperty_set.filter(control_property__data_source_type='gen').order_by('control_property__order')
        arc_control_properties = subject.subjectcontrolproperty_set.filter(control_property__data_source_type='arc').order_by('control_property__order')
        con_control_properties = subject.subjectcontrolproperty_set.filter(control_property__data_source_type='con').order_by('control_property__order')        
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
        gen_control_properties = []
        arc_control_properties = []
        con_control_properties = []        
        related_media = []
        related_web = []
        property_count = 0
    return render(request, 'base/subjectdetail.html', {'subject': subject, 'gen_images': gen_images, 'con_images': con_images, 'arc_images': arc_images, 'gen_properties': gen_properties, 'con_properties': con_properties, 'arc_properties': arc_properties, 'control_properties': gen_control_properties, 'arc_control_properties': arc_control_properties, 'con_control_properties': con_control_properties, 'related_media': related_media, 'related_web': related_web, 'property_count': property_count})
    
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
    
def help(request):

    return render(request, 'base/help.html')
    
def about(request):

    project = get_object_or_404(SiteContent, variable='about_project')
    site = get_object_or_404(SiteContent, variable='about_site')
    excavation = get_object_or_404(SiteContent, variable='about_excavation')
    team = get_object_or_404(SiteContent, variable='about_team')
    support = get_object_or_404(SiteContent, variable='about_support')
    dev = get_object_or_404(SiteContent, variable='about_dev')
    
    return render(request, 'base/about.html', {'project': project, 'site': site, 'excavation': excavation, 'team': team, 'support': support, 'dev': dev})
    
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
            id_pair = (m.media_id, m.media.notes, MediaProperty.objects.filter(media_id = m.media_id, property_id = 94)[0])
            other_maps.append(id_pair)
        except IndexError:
            continue
    
    loci = MediaLocationRelations.objects.filter(media_id = current_map.id, relation_type = 10).order_by('location__title')
    try:
        rsid = MediaProperty.objects.filter(media_id = current_map.id, property_id = 94)[0]
    except IndexError:
        raise Http404("Could not find map image")
    
    return render(request, 'base/mapdetail.html', {'location': location, 'current_map': current_map, 'other_maps': other_maps, 'loci': loci, 'rsid': rsid})
    
'''def collectiondetail(request, collection_id):
    
    current_item_id = request.GET.get('item', '')
    collection = get_object_or_404(Collection, pk = collection_id)
    subj_items = SubjectCollection.objects.filter(collection__id = collection.id)
    
    if current_item_id == '':
        current_item = get_object_or_404(Subject, pk = subj_items[0].subject_id)
        subj_items = subj_items[1:]
    else:
        subj_items = subj_items.exclude(subject_id = current_item_id)
        current_item = get_object_or_404(Subject, pk = current_item_id)
    
    other_items = []
    for m in maps:
        try:
            id_pair = (m.media_id, m.media.notes, MediaProperty.objects.filter(media_id = m.media_id, property_id = 94)[0])
            other_maps.append(id_pair)
        except IndexError:
            continue
    
    loci = MediaLocationRelations.objects.filter(media_id = current_map.id, relation_type = 10).order_by('location__title')
    try:
        rsid = MediaProperty.objects.filter(media_id = current_map.id, property_id = 94)[0]
    except IndexError:
        raise Http404("Could not find map image")
    
    return render(request, 'base/mapdetail.html', {'location': location, 'current_map': current_map, 'other_maps': other_maps, 'loci': loci, 'rsid': rsid})'''
        
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
    response['Content-Disposition'] = 'attachment; filename="property_detail.csv"'

    writer = csv.writer(response)
    writer.writerow(['Parent Category', 'Property Value', 'Specific Count', 'Cumulative Count'])
    for obj in all_objs:
        ancs = obj.ancestors()
        spec_count = SubjectControlProperty.objects.filter(control_property_value_id = obj.id).count()
        cum_count = obj.count_subj_instances()
        writer.writerow([ancs, obj.title, spec_count, cum_count])
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