from django import template
from django.core.urlresolvers import reverse
from base.models import *
from django.contrib.admin.templatetags.admin_list import result_list
from django.db.models import Q, Count
import re, urllib
from django.contrib.admin.views.main import (ALL_VAR, EMPTY_CHANGELIST_VALUE,
    ORDER_VAR, PAGE_VAR, SEARCH_VAR)
from ordereddict import OrderedDict
from suit.templatetags.suit_list import result_list_with_context
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.contrib.admin.helpers import AdminReadonlyField, AdminField

register = template.Library()

DOT = '.'

@register.simple_tag
def navactive(request, urls):
    """ Returns "active" if the current request is for the givens urls. 
        Used by the nav menus to highlight the active tab. """

    if request.path in ( reverse(url) for url in urls.split() ):
        return "active"
    return ""

@register.simple_tag    
def load_globals(key):
    """ Returns the value of a global variable """

    global_var = GlobalVars.objects.get(variable = key)

    return global_var.val
    
@register.simple_tag    
def load_content(key):
    """ Returns the value of site content """

    content = SiteContent.objects.get(variable = key)

    return content.val
    
@register.simple_tag    
def load_result_display_fields(fields, key):
    """ Selects the field to be displayed in result list """

    prop_list = []
    
    for i in range(3):
        title_str = key + str(i + 1)
        titles = ResultProperty.objects.filter(display_field = title_str)
        if titles[0]:
            title = titles[0]
            if title.field_type and title.field_type.visible:
                p = title.field_type.id
                property_name = title.field_type.property
                long_id = fields.get('id')
                id_group = long_id.split('.')
                id = id_group[2]
                if key.startswith('med'):
                    value = MediaProperty.objects.filter(property_id=p, media_id=id)
                elif key.startswith('po'):
                    value = PersonOrgProperty.objects.filter(property_id=p, person_org_id=id)
                elif key.startswith('loc'):
                    value = LocationProperty.objects.filter(property_id=p, location_id=id)
                else:
                    value = SubjectProperty.objects.filter(property_id=p, subject_id=id)
                for i, v in enumerate(value):
                    if i > 0:
                        prop_list.append(property_name + ' : ' + v.property_value + '; ')
                    else: 
                        prop_list.append(property_name + ' : ' + v.property_value)
    prop_str = ''
    
    for p in prop_list:
        prop_str += (p + '<br>')
 
    return prop_str
        
@register.simple_tag    
def get_query_params(request):
    str = ''
    
    keys = ['property', 'q', 'models']
    
    for key in keys:
        if key in request:
            param = key + '=' + request[key] + '&amp;'
            str += param
    
    return str
    
@register.simple_tag    
def get_result_details(fields):
    rowhtml = ''
    
    row_dict = {}

    for field, value in fields.items():
        if field.startswith('prop_') and not field.endswith('_exact'):
            prop_num = field[5:].strip()
            
            #sloppy (hopefully temporary) fix for Haystack auto-converting BM Reg #s to lists of ints
            if prop_num == '33':
                long_id = fields.get('id')
                id_group = long_id.split('.')
                id = id_group[2]
                vals = SubjectProperty.objects.filter(property_id=prop_num, subject_id=id)
                for i, v in enumerate(vals):
                    if i > 0:
                        value = value + '; ' + v.property_value
                    else: 
                        value = v.property_value                
            try:
                prop = DescriptiveProperty.objects.get(id=prop_num)
                prop_order = prop.order
                try:
                    row = '<tr><td>' + prop.property + '</td><td>' + value + '</td></tr>'
                except TypeError:
                    row = '<tr><td>' + prop.property + '</td><td>' + str(value) + '</td></tr>'
                
                #sloppy way of handling properties with same order number
                success = False
                while not success:
                    if prop_order in row_dict:
                        prop_order += 1
                    else:
                        success = True
                row_dict[prop_order] = row
                
            except DescriptiveProperty.DoesNotExist:
                continue

    ordered_dict = OrderedDict(sorted(row_dict.items()))
    
    for k, v in ordered_dict.iteritems():
        rowhtml += v
    
    return rowhtml
    
@register.simple_tag    
def get_img_thumb(object, type, size):

    if type == 'ms':
        relation = MediaSubjectRelations.objects.filter(subject = object.id, relation_type = 1)
    elif type == 'mpo':
        relation = MediaPersonOrgRelations.objects.filter(person_org = object.id, relation_type = 1)
    elif type == 'ml':
        relation = MediaLocationRelations.objects.filter(location = object.id, relation_type = 1)
    else:
        relation = MediaMediaRelations.objects.filter(media1 = object.id, relation_type = 1)
        if relation:
            first_rel = relation[0]
            rs_ids = first_rel.media2.mediaproperty_set.filter(property__property = 'Resource Space ID')
            if rs_ids:
                rs_id = rs_ids[0].property_value
                return 'http://ur.iaas.upenn.edu/resourcespace/plugins/ref_urls/file.php?ref=' + rs_id + '&size=' + size
        return 'http://ur.iaas.upenn.edu/static/img/no_img.jpg'
    
    if relation:
        first_rel = relation[0]
        rs_ids = first_rel.media.mediaproperty_set.filter(property__property = 'Resource Space ID')
        if rs_ids:
            rs_id = rs_ids[0].property_value
            return 'http://ur.iaas.upenn.edu/resourcespace/plugins/ref_urls/file.php?ref=' + rs_id + '&size=' + size
    
    return 'http://ur.iaas.upenn.edu/static/img/no_img.jpg'
    
@register.simple_tag    
def get_img_url(object, type):
    if type == 'ms':
        relation = MediaSubjectRelations.objects.filter(subject = object.id, relation_type = 1)
    elif type == 'mpo':
        relation = MediaPersonOrgRelations.objects.filter(person_org = object.id, relation_type = 1)
    elif type == 'ml':
        relation = MediaLocationRelations.objects.filter(location = object.id, relation_type = 1)
    else:
        relation = MediaMediaRelations.objects.filter(media1 = object.id, relation_type = 1)
        if relation:
            first_rel = relation[0]
            rs_ids = first_rel.media2.mediaproperty_set.filter(property__property = 'Resource Space ID')
            if rs_ids:
                rs_id = rs_ids[0].property_value
                return 'http://ur.iaas.upenn.edu/resourcespace/pages/view.php?ref=' + rs_id
        return 'http://ur.iaas.upenn.edu/static/img/no_img.jpg'
    
    if relation:
        first_rel = relation[0]
        rs_ids = first_rel.media.mediaproperty_set.filter(property__property = 'Resource Space ID')
        if rs_ids:
            rs_id = rs_ids[0].property_value
            return 'http://ur.iaas.upenn.edu/resourcespace/pages/view.php?ref=' + rs_id
            
    return ''
    
@register.simple_tag
def get_properties_dropdown():
    props = DescriptiveProperty.objects.filter(Q(primary_type='SO') | Q(primary_type='AL')).exclude(control_field=True).order_by('order')
    options = '<option value="0">Any</option>'
    for prop in props:
        option = '<option value="' + str(prop.id) + '">' + prop.property + '</option>'
        options += option
        
    return options
    
@register.simple_tag
def get_cntl_properties_dropdown():
    props = DescriptiveProperty.objects.filter(control_field=True).order_by('order')
    options = '<option value="0">Any</option>'
    for prop in props:
        option = '<option value="' + str(prop.id) + '">' + prop.property + '</option>'
        options += option
        
    return options

@register.simple_tag
def get_pub_dropdown():
    pubs = Media.objects.filter(type=2).order_by('title')
    options = '<option value="0">Any</option>'
    for pub in pubs:
        option = '<option value="' + str(pub.id) + '">' + pub.title + '</option>'
        options += option
        
    return options
    
@register.simple_tag
def load_last_query(query):
    types = {'icontains': 'contains', 'not_icontains': 'does not contain', 'istartswith': 'starts with', 'iendswith': 'ends with', 'blank': 'is blank', 'not_blank': 'is not blank', 'exact': 'equals', 'not_exact': 'is not equal', 'gt': 'is greater than', 'gte': 'is greater than or equal to', 'lt': 'is less than', 'lte': 'is less than or equal to'}

    query_rows = query.split('???')
    
    display_text = ''
    
    for row in query_rows:
        terms = row.split('___')
        
        if len(terms) >= 3:
        
            if terms[0].startswith('&'):
                display_text += (' '  + terms[0][1:])
                terms = terms[1:]
        
            # if a property is searched for that doesn't exist, set property to Any
            prop = 'Any'
            try:
                prop = DescriptiveProperty.objects.get(pk=terms[0])
            except DescriptiveProperty.DoesNotExist:
                pass
            display_text += (' (' + prop.property)
            display_text += (' ' + types[terms[1]])
            display_text += (' ' + terms[2] + ')')
        
    return display_text
    
@register.simple_tag
def advanced_obj_search(search_term):

    cleaned_search_term = search_term[2:]
    cleaned_search_term = urllib.unquote_plus(cleaned_search_term)

    query_rows = cleaned_search_term.split('???') #list of queries from search_term
    
    queryset = Subject.objects.all()

    # make sure we received list of queries
    if len(query_rows) > 0:
               
        for i, row in enumerate(query_rows):
           
            negate = False # whether the query will be negated
            connector = '' # AND/OR/NOTHING
            kwargs = {}
            current_query = Q()            
            
            terms = row.split('___')                

            if row.startswith('pub='):
                pub_filter = row[4:]
                if pub_filter == '':
                    continue
                elif pub_filter == '0':
                    current_query = Q(mediasubjectrelations__relation_type=2)
                else:
                    current_query = Q(mediasubjectrelations__media=pub_filter)

            elif row.startswith('img=true'):
                current_query = Q(mediasubjectrelations__relation_type=3)
                    
            elif len(terms) >= 3:
                # we got at least the number of terms we need

                # CURRENT TERMS FORMAT: ([&AND/OR,] PROPERTY, [not_]SEARCH_TYPE, [SEARCH_KEYWORDS])
            
                # remove and save the operator, if present
                if terms[0].startswith('&'): 
                    connector = terms[0][3:]
                    terms = terms[1:]

                # CURRENT TERMS FORMAT: (PROPERTY, [not_]SEARCH_TYPE, [SEARCH_KEYWORDS])
                    
                # remove and save the negation, if present
                if terms[1].startswith('not'):
                    negate = True
                    terms[1] = terms[1][4:]

                # CURRENT TERMS FORMAT: (PROPERTY, SEARCH_TYPE, [SEARCH_KEYWORDS])
                
                # if this row is blank, than skip
                if (terms[2] == '') and (terms[1] != 'blank'):
                    continue
                    
                ########### PROBLEM: THIS IS VERY DEPENDENT ON THE DATA AND UNUM REMAINING AT ID 23
                # if search is for U Number, remove any non-numbers at the beginning
                if terms[0] == '23':
                    d = re.search("\d", terms[2])
                    if d is not None:
                        start_index = d.start()
                        terms[2] = terms[2][start_index:]
                ###########
                
                # create current query
                if terms[1] == 'blank':
                    #if property is Any, then return all b/c query asks for doc with 'any' blank properties
                    if terms[0] == '0':
                        continue
                        
                    # BLANK is a special case negation (essentially a double negative), so handle differently
                    if negate:
                        current_query = Q(subjectproperty__property = terms[0])
                    else:
                        current_query = ~Q(subjectproperty__property = terms[0])                   
                
                else:
                    kwargs = {str('subjectproperty__property_value__%s' % terms[1]) : str('%s' % terms[2])}

                    # check if a property was selected and build the current query
                    if terms[0] == '0':
                        # if no property selected, than search thru ALL properties
                        # use negation
                        if negate:
                            current_query = ~Q(**kwargs)
                        else:
                            current_query = Q(**kwargs)
                    else:
                        # use negation
                        if negate:
                            current_query = Q(Q(subjectproperty__property = terms[0]) & ~Q(**kwargs))
                        else:
                            current_query = Q(Q(subjectproperty__property = terms[0]) & Q(**kwargs))
  
            # modify query set
            if connector == 'AND':
                queryset = queryset.filter(current_query)
            elif connector == 'OR':
                queryset = queryset | Subject.objects.filter(current_query)
            else:
                if i == 0:
                    # in this case, current query should be the first query, so no connector
                    queryset = Subject.objects.filter(current_query)
                else:
                    # if connector wasn't set, use &
                    queryset = queryset.filter(current_query)
        
    return queryset.order_by('id').distinct()
    
@register.filter
def get_next(value, arg):

    terms = value.GET.get('_changelist_filters')
    
    if terms:
        queryset = advanced_obj_search(terms)
    
        remaining_objects = queryset.filter(id__gt=arg).order_by('id')
    
        if remaining_objects:
            return remaining_objects[0].id
    
    return ''
    
@register.filter
def has_next(value, arg):
    
    terms = value.GET.get('_changelist_filters')

    if terms:
        queryset = advanced_obj_search(terms)
        
        remaining_objects = queryset.filter(id__gt = arg).order_by('id')[:1]
        
        if remaining_objects:
            return True
        else:
            return True

    return False
    
@register.filter
def get_prev(value, arg):

    terms = value.GET.get('_changelist_filters')
    
    if terms:
        queryset = advanced_obj_search(terms)
    
        remaining_objects = queryset.filter(id__lt=arg).order_by('-id')
    
        if remaining_objects:
            return remaining_objects[0].id
    
    return ''
    
@register.filter
def has_prev(value, arg):
    
    terms = value.GET.get('_changelist_filters')

    if terms:
        queryset = advanced_obj_search(terms)
        
        remaining_objects = queryset.filter(id__lt = arg).order_by('-id')[:1]
        
        if remaining_objects:
            return True
        else:
            return True

    return False
    
@register.filter
def get_filter_param(value):
    return value.GET.get('_changelist_filters')
    
@register.simple_tag
def get_params_list(query, index):
    
    params = re.split(r"\?{3}|_{3}", query)
    
    if len(params) >= index + 1:
        if (params[index].startswith('pub=')) or (params[index].startswith('img=')):
            return params[index][4:]
        return params[index]
    
    return ''
    
@register.inclusion_tag('admin/base/subject/search_form.html', takes_context=True)
def subject_search_form(context, cl):
    """ Displays an advanced search form for searching the list.
    
    Includes context. """
    return {
        'asf': context.get('asf'),
        'cl': cl,
        'show_result_count': cl.result_count != cl.full_result_count,
        'search_var': SEARCH_VAR
    }
    
@register.simple_tag
def custom_header_title(header):
    if header.startswith('title') or header.startswith('desc'):
        field = 'subj_' + header
        props = ResultProperty.objects.filter(display_field = field)
        return props[0].field_type.property
    return header.title()
    
@register.assignment_tag
def get_linked_data_url(property_id):
    urls = ControlFieldLinkedData.objects.filter(control_field_id=property_id)
    
    if urls:
        return urls
    else:
        return []
        
@register.assignment_tag
def get_visible_subj_props(subject):
    props = subject.subjectproperty_set.filter(property__visible=True)[:3]
    
    if props:
        return props
    else:
        return []
        
@register.simple_tag
def get_museum(subj):
    museum = SubjectProperty.objects.filter(subject=subj, property_id = 59)
    
    if museum:
        if museum[0]:
            return museum[0].property_value
    else:
        return ''
        
@register.assignment_tag
def get_control_fields():
    fields = DescriptiveProperty.objects.filter(control_field=True)
    if fields:
        return fields
    return []
    
@register.simple_tag
def get_control_prop_vals(control_prop, current_val, include_blank = 1):

    if control_prop == '':
        return ""  

    # build the set of control property values for this control property
    results = ControlField.objects.filter(type__id = control_prop)
    if include_blank:
        result_list = '<option value'
        if not current_val or current_val == '':
            result_list += ' selected'
        result_list += '>---------</option>'
    else:
        result_list = ''
    for result in results:
        # must build the indent because we aren't using a tree choice field
        indent = ""
        for i in range(result.level):
            indent = indent + "---"
        result_list += "<option value='" + str(result.id) + "'"
        if current_val == result.id:
            result_list += " selected"
        result_list += ">" + indent + result.title + "</option>"
    return result_list
    
@register.assignment_tag
def get_loc_ancestors(location):
    return location.get_ancestors(include_self = True)
    
@register.assignment_tag
def get_loc_siblings(location):
    types = location.get_siblings().values('type').annotate(count=Count('type'))
    siblings = []
    for type in types:
        siblings.append((ObjectType.objects.get(pk=type['type']), location.get_siblings().filter(type_id=type['type'])))
    return siblings

@register.assignment_tag
def get_loc_children(location):
    types = location.get_children().values('type').annotate(count=Count('type'))
    children = []
    for type in types:
        children.append((ObjectType.objects.get(pk=type['type']), location.get_children().filter(type_id=type['type'])))
    return children
    
@register.assignment_tag
def has_spec_context(location_tree):
    for location in location_tree:
        if location.type_id == 10:
            return 'Publication Context:'
        elif location.type_id == 12:
            return 'Excavation Context:'
    return None
    
@register.simple_tag
def get_bib_ref(media):
    ref = ""
    if media.bib_type_id == 4:
        author = MediaProperty.objects.filter(media_id = media.id, property_id = 77)
        if author:
            ref += author[0].property_value
            if not ref.endswith('.'):
                ref += '. '
            else:
                ref += ' '
        art_title = MediaProperty.objects.filter(media_id = media.id, property_id = 88)
        if art_title:
            ref += '"' + art_title[0].property_value + '." '                
        jtitle = MediaProperty.objects.filter(media_id = media.id, property_id = 80)
        if jtitle:
            ref += '<em>' + jtitle[0].property_value + '</em> '
        vol = MediaProperty.objects.filter(media_id = media.id, property_id = 81)
        if vol:
            ref += vol[0].property_value
        issue = MediaProperty.objects.filter(media_id = media.id, property_id = 87)
        if issue:
            ref += ':' + issue[0].property_value
        ref += ' '
        year = MediaProperty.objects.filter(media_id = media.id, property_id = 78)
        if year:
            ref += '(' + year[0].property_value + '): '
        pages = MediaProperty.objects.filter(media_id = media.id, property_id = 95)
        if pages:
            ref += pages[0].property_value

    else:
        author = MediaProperty.objects.filter(media_id = media.id, property_id = 77)
        if author:
            ref += author[0].property_value
            if not ref.endswith('.'):
                ref += '. '
            else:
                ref += ' '            
        year = MediaProperty.objects.filter(media_id = media.id, property_id = 78)
        if year:
            ref += '(' + year[0].property_value + ') '
        title = MediaProperty.objects.filter(media_id = media.id, property_id = 79)
        if title:
            ref += '<em>' + title[0].property_value + '</em>, '
        else:
            ref += '[title missing], '
        place = MediaProperty.objects.filter(media_id = media.id, property_id = 86)
        if place:
            ref += place[0].property_value + ': '
        pub = MediaProperty.objects.filter(media_id = media.id, property_id = 85)
        if pub:
            ref += pub[0].property_value
        
    return ref
    
@register.assignment_tag
def img_id_from_rsref(rsref):
    id = MediaProperty.objects.filter(property__property = 'Resource Space ID', property_value = rsref)
    if id and id[0]:
        return id[0].media_id
    return None
    
@register.assignment_tag
def get_facet_values(property):
    return ControlField.objects.filter(type_id = property)
        
@register.assignment_tag
def build_facet_counts(facets):
    totals = {}
    for facet in facets:
        try:
            node = ControlField.objects.get(pk=int(facet[0]))
            ancs = node.get_ancestors(include_self=True)
            for anc in ancs:
                if anc.id in totals:
                    totals[anc.id] += facet[1]
                else:
                    totals[anc.id] = facet[1]
        except ControlField.DoesNotExist:
            # if index is not up to date and a ControlField has been deleted, this will catch the error
            pass
    return totals
        
@register.assignment_tag
def get_node_facet_count(totals, node):
    if node.id in totals:
        return totals[node.id]
    return 0
    
@register.assignment_tag
def query_params_getlist(request, param):
    params = request.GET.getlist(param)
    if len(params) > 0:
        query_string = ""
        for p in params:
            query_string += p + '&'
        return query_string
    return 'None'
    
@register.simple_tag
def get_loci_details(loci_details, index):
    if index in loci_details:
        return loci_details[index]
    return ""
    
@register.assignment_tag
def adv_searchform_has_changed(request):
    """ Checking whether any advanced search form parameters are set.
    
    If any are set and this returns True, it will cause the collapsed adv search form to open. 
    """

    if (request.GET.get('q', '') == '' and request.GET.get('search_type', '') != 'blank') and (request.GET.get('q2', '') == '' and request.GET.get('search_type2', '') != 'blank') and (request.GET.get('q3', '') == '' and request.GET.get('search_type3', '') != 'blank'):
        return False
    return True