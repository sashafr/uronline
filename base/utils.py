""" Utility functions for the base application """

import csv
from base.models import *
from django.utils.encoding import smart_str
from haystack.inputs import Raw
from haystack.query import SearchQuerySet, SQ
import re
from django.contrib.auth.models import User

def export_csv(results):
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=results.csv'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8')) # BOM (optional...Excel needs it to open UTF-8 file properly)
    for result in results:
        new_row = []
        for field, value in result.get_additional_fields():
            new_row.append(smart_str(value))
        writer.writerow(new_row)
    return response

def load_globals():
    """ Returns a dictionary of globals for this app """

    globals = GlobalVars.objects.all()

    global_dict = {}
	
    for global_var in globals:
        global_dict[global_var.variable] = global_var.val
		
    return global_dict

def advanced_search(search_term, model):
    queryset = model.objects.all()

    query_rows = search_term.split('???') #list of queries from search_term

    # make sure we received list of queries
    if len(query_rows) > 0:
               
        for i, row in enumerate(query_rows):
        
            negate = False # whether the query will be negated
            connector = '' # AND/OR/NOTHING
            kwargs = {}
            current_query = Q()
            
            terms = row.split('___')                
            
            if len(terms) >= 3:
                # we got at least the number of terms we need

                # CURRENT TERMS FORMAT: ([&AND/OR,] PROPERTY, [not_]SEARCH_TYPE, [SEARCH_KEYWORDS])
            
                # remove and save the operator, if present
                if terms[0].startswith('&'): 
                    connector = terms[0][1:]
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
                    queryset = queryset | model.objects.filter(current_query)
                else:
                    if i == 0:
                        # in this case, current query should be the first query, so no connector
                        queryset = queryset.filter(current_query)
                    else:
                        # if connector wasn't set, use &
                        queryset = queryset.filter(current_query)
        
    return queryset.order_by('id').distinct()
 
def update_display_fields(object_id, object_type):
 
    result_props = {}
    result_props['title1'] = ResultProperty.objects.get(display_field=(object_type+'_title1'))
    result_props['title2'] = ResultProperty.objects.get(display_field=(object_type+'_title2'))
    result_props['title3'] = ResultProperty.objects.get(display_field=(object_type+'_title3'))
    result_props['desc1'] = ResultProperty.objects.get(display_field=(object_type+'_desc1'))
    result_props['desc2'] = ResultProperty.objects.get(display_field=(object_type+'_desc2'))
    result_props['desc3'] = ResultProperty.objects.get(display_field=(object_type+'_desc3'))
    
    subjects = Subject.objects.filter(pk=object_id)
    
    if subjects and len(subjects) > 0:
        subject = subjects[0]
        for key, prop in result_props.iteritems():
            id_str = ''
            ids = subject.subjectproperty_set.filter(property=prop.field_type_id)
            if ids:
                for i, id in enumerate(ids):
                    if i > 0:
                        id_str += ', '
                    id_str += id.property_value
            
            if id_str == '':
                id_str = '(none)'
            
            kwargs = {key : id_str}
            Subject.objects.filter(id=subject.id).update(**kwargs)
            
def get_img_ids(object, type):
    imgs = []

    if type == 'ms':
        relations = MediaSubjectRelations.objects.filter(subject = object.id, relation_type = 3)
    elif type == 'mpo':
        relations = MediaPersonOrgRelations.objects.filter(person_org = object.id, relation_type = 3)
    elif type == 'ml':
        relations = MediaLocationRelations.objects.filter(location = object.id, relation_type = 3)
    elif type == 'mf':
        prop = MediaProperty.objects.filter(media_id = object.id, property__property = 'Resource Space ID')
        if prop and prop[0]:
            imgs.append(prop[0].property_value)
        return imgs
    else:
        relations = MediaMediaRelations.objects.filter(media1 = object.id, relation_type = 3)
        for relation in relations:
            rs_ids = relation.media2.mediaproperty_set.filter(property__property = 'Resource Space ID')
            if rs_ids:
                for rs_id in rs_ids:
                    imgs.append(rs_id.property_value)
        return imgs
        
    if relations:
        for relation in relations:
            rs_ids = relation.media.mediaproperty_set.filter(property__property = 'Resource Space ID')
            if rs_ids:
                for rs_id in rs_ids:
                    imgs.append(rs_id.property_value)
    
    return imgs            

def get_img_ids_spec(object, type, img_type):
    imgs = []

    if type == 'ms':
        relations = MediaSubjectRelations.objects.filter(subject = object.id, relation_type = img_type)
    elif type == 'mpo':
        relations = MediaPersonOrgRelations.objects.filter(person_org = object.id, relation_type = img_type)
    elif type == 'ml':
        relations = MediaLocationRelations.objects.filter(location = object.id, relation_type = img_type)
    else:
        relations = MediaMediaRelations.objects.filter(media1 = object.id, relation_type = img_type)
        for relation in relations:
            rs_ids = relation.media2.mediaproperty_set.filter(property__property = 'Resource Space ID')
            if rs_ids:
                for rs_id in rs_ids:
                    imgs.append(rs_id.property_value)
        return imgs
        
    if relations:
        for relation in relations:
            rs_ids = relation.media.mediaproperty_set.filter(property__property = 'Resource Space ID')
            if rs_ids:
                for rs_id in rs_ids:
                    imgs.append(rs_id.property_value)
    
    return imgs      
    
def search_for_export (p1, st1, q1, op1, p2, st2, q2, op2, p3, st3, q3, order):
        
    prop_list = [p1, p2, p3]
    type_list = [st1, st2, st3]
    query_list = [q1, q2, q3]
    op_list = [op1, op2]
    
    prop_type_list = ['_t', '_t', '_t']
    for i, prop_list_item in enumerate(prop_list):
        if prop_list_item != '':
            dp = DescriptiveProperty.objects.filter(id=prop_list_item)
            if dp[0]:
                prop_type_list[i] = dp.solr_type    
    
    # query object for building full advanced query
    sq = SQ()

    for j in range(0, len(prop_list)):
    
        prop = 'content'
        type = type_list[j]
        query = query_list[j]
        operator = ''            
        negate = False
        kwargs = {}

        # check for operator
        if j > 0:
            operator = op_list[j - 1]
        
        # check for not
        if type.startswith('!'):
            negate = True
            type = type[1:]            
        
        # if this row of query builder is blank, skip
        if (query == '') and (type != 'blank'):
            continue
            
        # check if a property was selected
        if prop_list[j] != '':
            if prop_type_list[j] != '_t':
                prop = 'sprop_' + str(prop_list[j]) + prop_type_list[j]
            else:
                prop = 'prop_'+ str(prop_list[j])

        # check if search type was selected
        if type == '':
            type = 'contains'               
            
        # determine the type of search
            
        # CONTAINS -> special case misspellings
        if type == 'contains':
        
            query_text = '('
        
            # special misspellings
            if prop == 'prop_23':
                #if doing a contains search for u number, get first instance of numbers followed by a 0 or 1 letter
                match = re.search(r'(\d+[a-zA-Z]?)', query)
                if match:
                    query = match.group(0)
                    query_text += (' ' + query + '? OR ')
            else:
                query = re.sub(r'(\s*)([uU]\s*?\.?\s*)(\d+)([a-zA-Z]*)', r'\1u* *\3*', query)
                query = re.sub(r'(\s*)([pP][gG]\s*?[\./]?\s*)(\w+)', r'\1pg* *\3*', query)
            
            query_text += '(' + query + '))'

            kwargs = {str('%s' % prop) : Raw(query_text)}            
        
        # LIKE -> 'a*b' or 'a?b'
        elif type == 'like':
        
            keywords = query.split()
            
            if keywords:
                query_text = '('
            
                for i, word in enumerate(keywords):
                    
                    if i > 0: 
                        query_text += ' AND '
                    query_text += word
                
                query_text += ')'
                
                kwargs = {str('%s' % prop) : Raw(query_text)}
        
        # BLANK -> returns all subjects that don't have a value for given property
        elif type == 'blank':
            
            #if property is Any, then return all b/c query asks for doc with 'any' blank properties
            if self.cleaned_data['property'] == None:
                continue
                
            # BLANK is a special case negation (essentially a double negative), so handle differently
            if negate:
                kwargs = {str('%s' % prop) : Raw('[1 TO *]')}
                negate = False
            else:
                kwargs = {str('-%s' % prop) : Raw('[* TO *]')}
            
        # ENDSWITH -> '*abc'
        elif type == 'endswith':
        
            keywords = query.split()
            
            if keywords:
                query_text = '('
            
                for i, word in enumerate(keywords):
                    
                    if i > 0: 
                        query_text += ' AND '
                    query_text += ('*' + word)
                
                query_text += ')'
                
                kwargs = {str('%s' % prop) : Raw(query_text)}
                                
        else:
            
            kwargs = {str('%s__%s' % (prop, type)) : str('%s' % query)}
        
        if operator == 'or':
            if negate:
                sq = sq | ~SQ(**kwargs)
            else:
                sq = sq | SQ(**kwargs)
        elif operator == 'and':
            if negate:
                sq = sq & ~SQ(**kwargs)
            else:
                sq = sq & SQ(**kwargs)
        else:
            if negate:
                sq = ~SQ(**kwargs)
            else:
                sq = SQ(**kwargs)                

    sqs = SearchQuerySet().filter(sq)                
    
    if order != '':
        prop_order = order
        return sqs.order_by(prop_order)
    else:
        return sqs
        
def single_context_in_ah():
    ''' Currently not available on website, used internally by project team. 
    
    Checks for objects in AH that have only one location relation (looking for 
    objects that do not have both a publication & excavation context). Returns a list of ids.'''
    
    ids = []
    
    #get all locations within AH
    ah = Location.objects.get(pk = 5)
    ah_tree = ah.get_descendants(include_self = True)
    
    # iterate through locations, get all related subjects, and check if those subjects have only a single relation to locations
    for loc_node in ah_tree:
        subs_related_to_node = LocationSubjectRelations.objects.filter(location_id = loc_node.id)
        for sub in subs_related_to_node:
            relation_count = sub.subject.locationsubjectrelations_set.all().count()
            if relation_count < 2 and sub.subject.id not in ids:
                ids.append(sub.subject.id)       
                
    return ids
    
def update_pgs(min, max, parent_id):
    """ Used for fast updates from command line, not used anywhere on website """
    
    for i in range(min, max):
        par = Location.objects.get(pk = 25)
        loc = Location.objects.filter(title = ('PG/' + str(i)), parent = par)
        if loc:
            if len(loc) > 1:
                print 'Multiple Locations labelled PG/' + str(i)
                continue
            loc[0].parent = Location.objects.get(pk=parent_id)
            loc[0].save()
        else:
            new_title = 'PG/' + str(i)
            new_notes = 'Added to complete full range of PG'
            new_type = ObjectType.objects.get(pk=8)
            new_parent = Location.objects.get(pk=parent_id)
            last_mod = User.objects.get(pk=1)
            new_loc = Location(title = new_title, notes = new_notes, type = new_type, parent = new_parent, last_mod_by = last_mod)
            new_loc.save()
            
            loc_prop = LocationProperty(location = new_loc, property = DescriptiveProperty.objects.get(pk = 96), property_value = new_title, last_mod_by = last_mod)
            loc_prop.save()
            
def clean_dups():
    """ Used for fast updates from command line, not used anywhere on website """

    props = ControlField.objects.exclude(level = 0)
    
    for prop in props:
        ancs = prop.get_ancestors()
        for anc in ancs:
            prob_subj = Subject.objects.filter(subjectcontrolproperty__control_property_value = anc).filter(subjectcontrolproperty__control_property_value = prop)
            for prob in prob_subj:
                dups = SubjectControlProperty.objects.filter(subject = prob, control_property_value = anc)
                for dup in dups:
                    print "Removing " + dup.subject.title + ": " + dup.control_property_value.title
                    dup.delete()
                    
def clean_dup_locs():
    """ Used for fast updates from command line, not used anywhere on website """

    props = Location.objects.exclude(level = 0)
    
    for prop in props:
        ancs = prop.get_ancestors()
        for anc in ancs:
            prob_subj = Subject.objects.filter(locationsubjectrelations__location = anc).filter(locationsubjectrelations__location = prop)
            for prob in prob_subj:
                dups = LocationSubjectRelations.objects.filter(subject = prob, location = anc)
                for dup in dups:
                    print "Removing " + dup.subject.title + ": " + dup.location.title
                    dup.delete()
                    
def fix_bm_nums():
    """ Used for fast updates from command line, not used anywhere on website """
    
    bmnums = SubjectProperty.objects.filter(property_id = 33)
    
    for bmnum in bmnums:
        num = bmnum.property_value
        match = re.match(r"[^\d]*(\d+)[^\d]+(\d+)[^\d]+(\d+)[^\d]*", num)
        if match:
            regyr = match.group(1)
            regcol = match.group(2)
            regnum = match.group(3)
            for i in range (0, (4-len(regcol))):
                regcol = '0' + regcol
            fixed_num = regyr + ',' + regcol + '.' + regnum
            bmnum.property_value = fixed_num
            bmnum.save()
        else:
            print "BAD MATCH: " + num + "; ID: " + str(bmnum.subject_id)
            
def quickfix():
    seals = Subject.objects.filter(subjectcontrolproperty__control_property_value__in = ControlField.objects.get(pk=42).get_descendants(include_self=True))
    seals = seals.filter(subjectcontrolproperty__control_property_value_id = 398).order_by("title")
    ord = 1
    for seal in seals:
        new_col = SubjectCollection(subject = seal, collection = Collection.objects.get(pk=5), order = ord)
        new_col.save()
        ord += 1
    
def get_display_fields(obj, object_type):
    """ Returns the Title and Descriptor display fields for an object (as dict) with a concatenation
    of their object property values or (none) if they have not value for the selected
    property. """
 
    result_props = {'title1': '',
                    'title2': '',
                    'title3': '',
                    'desc1': '',
                    'desc2': '',
                    'desc3': ''}

    for key, new_property in result_props.iteritems():
        result_prop = ResultProperty.objects.get(display_field = (object_type + '_' + key))
        result_props[key] = get_display_field(obj, object_type, result_prop)
    
    return result_props            