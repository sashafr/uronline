""" Utility functions for the base application """

from base.models import *

def load_globals():
    """ Returns a dictionary of globals for this app """

    globals = GlobalVars.objects.all()

    global_dict = {}
	
    for global_var in globals:
        global_dict[global_var.variable] = global_var.val
		
    return global_dict
    
    
def admin_column(obj, column):
    """ Gets the values for an admin change_list column based on which column is requested 
    
    Returns empty string if object does not have values for requested column
    """

    id_str = ''    
    
    fields = ResultProperty.objects.filter(display_field = column)

    if fields and fields[0]:
    
        field = fields[0]
    
        # get all the property values of a subject that are of the specified property
        ids = obj.subjectproperty_set.filter(property=field.field_type_id)
        
        # iterate through property values to make them a single, comma separated string
        if ids:
            for i, id in enumerate(ids):
                if i > 0:
                    id_str += ', '
                id_str += id.property_value

    return id_str     
    
def admin_column_name(column):
    """ Get the name for the admin change_list column based on which column is requested 
    
    Returns an empty string if column does not exist in Result Properties table
    """

    fields = ResultProperty.objects.filter(display_field = column)
    if fields:
        return field.field_type # this is the name of the requested descriptive property
    return ''

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