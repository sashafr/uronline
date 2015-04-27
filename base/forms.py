from django import forms
from haystack.forms import SearchForm, model_choices
from base.models import DescriptiveProperty, ResultProperty, ControlField
from haystack.inputs import Raw
from haystack.query import SearchQuerySet, SQ
from django.db import models
import re
from mptt.forms import TreeNodeChoiceField

OPERATOR = (
    ('and', 'AND'),
    ('or', 'OR'),
)

SEARCH_TYPE = (
    ('contains', 'contains'),
    ('!contains', 'does not contain'),
    ('like', 'like'),
    ('!like', 'is not like'),
    ('exact', 'equals'),
    ('!exact', 'does not equal'),
    ('blank', 'is blank'),
    ('!blank', 'is not blank'),
    ('startswith', 'starts with'),
    ('!startswith', 'does not start with'),
    ('endswith', 'ends with'),
    ('!endswith', 'does not end with'),
    ('gt', 'is greater than'),
    ('gte', 'is greater than or equal to'),
    ('lt', 'is less than'),
    ('lte', 'is less than or equal to'),
)

class AdvancedSearchForm(SearchForm):
    """Search form allows user to search Solr index by property
    
    This allows the user to specify the property, type of search and
    AND/OR methods for combining searches"""
    
    # Selected Search Fields
    object_type = TreeNodeChoiceField(label='Object Type', required=False, queryset=ControlField.objects.filter(type_id = 19), empty_label='Any')
    material = TreeNodeChoiceField(label='Material', required=False, queryset=ControlField.objects.filter(type_id = 12), empty_label='Any')
    museum = TreeNodeChoiceField(label='Current Museum', required=False, queryset=ControlField.objects.filter(type_id = 59), empty_label='Any')
    keyword = forms.CharField(label='Keywords', required=False)
    museum_num = forms.CharField(label='Museum Number', required=False)
    unum = forms.CharField(label='U Number', required=False)
    
    # Advanced Search Fields
    property = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible=True, facet=False), empty_label="Any")
    search_type = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q = forms.CharField(label='Search Terms', required=False)
    op = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property2 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible=True, facet=False), empty_label="Any")
    search_type2 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q2 = forms.CharField(label='Search Terms', required=False)
    op2 = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property3 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible=True, facet=False), empty_label="Any")
    search_type3 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q3 = forms.CharField(label='Search Terms', required=False)
    order = forms.ModelChoiceField(label='', required=False, queryset=ResultProperty.objects.filter(display_field__startswith='subj_title'))
    
    def __init__(self, *args, **kwargs):
        super(AdvancedSearchForm, self).__init__(*args, **kwargs)    

    def search(self):
        """This search method starts from a new query of all documents
        in the index instead of getting the existing SearchQuerySet from the super class. This is mainly to clear the default
        query of the index for the value of q. HOWEVER, this requires
        redoing any actions normally taken before the SearchForm 
        is called, such as faceting the SearchQuerySet."""
        
        # faceting must be done here manually b/c we are creating a new SearchQuerySet
        sqs = SearchQuerySet().facet('facet_prop_19')   
        
        if not self.is_valid():
            return self.no_query_found()
            
        prop_list = [self.cleaned_data['property'], self.cleaned_data['property2'], self.cleaned_data['property3']]
        type_list = [self.cleaned_data['search_type'], self.cleaned_data['search_type2'], self.cleaned_data['search_type3']]
        query_list = [self.cleaned_data['q'], self.cleaned_data['q2'], self.cleaned_data['q3']]
        op_list = [self.cleaned_data['op'], self.cleaned_data['op2']]
        
        # SELECTED FIELDS SEARCH
        if self.cleaned_data['object_type']:
            value_tree = self.cleaned_data['object_type'].get_descendants(include_self=True)
            tsq = SQ()
            for index, node in enumerate(value_tree):
                if index == 0:
                    tsq = SQ(facet_prop_19 = node.id)
                else:
                    tsq = tsq | SQ(facet_prop_19 = node.id)
            sqs = sqs.filter(tsq)
        if self.cleaned_data['material']:
            value_tree = self.cleaned_data['material'].get_descendants(include_self=True)
            tsq = SQ()
            for index, node in enumerate(value_tree):
                if index == 0:
                    tsq = SQ(facet_prop_12 = node.id)
                else:
                    tsq = tsq | SQ(facet_prop_12 = node.id)
            sqs = sqs.filter(tsq)
        if self.cleaned_data['museum']:
            sqs = sqs.filter(facet_prop_59 = self.cleaned_data['museum'].id)
        if self.cleaned_data['keyword']:
            sqs = sqs.filter(content = self.cleaned_data['keyword'])
        if self.cleaned_data['museum_num']:
            mus_sq = SQ()
            mus_nums = ['31', '32', '33', '34', '35', '36', '38', '40', '41', '42', '43', '44', '45', '73', '128']
            for index, num in enumerate(mus_nums):
                kwargs = {str('prop_%s' % (num)) : self.cleaned_data['museum_num']}
                if index == 0:
                    mus_sq = SQ(**kwargs)
                else:
                    mus_sq = mus_sq | SQ(**kwargs)
            sqs = sqs.filter(mus_sq)
        if self.cleaned_data['unum']:
            sqs = sqs.filter(prop_23 = self.cleaned_data['unum']) 
        
        # ADVANCED SEARCH
        
        # query object for building full advanced query
        sq = SQ()
        modified = False

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
            else:
                modified = True
                
            # check if a property was selected
            if prop_list[j] != None:
                if prop_list[j].facet:
                    prop = 'facet_prop_'+ str(prop_list[j].id)
                else:   
                    prop = 'prop_'+ str(prop_list[j].id)

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

        if modified:
            sqs = sqs.filter(sq)                
        
        if self.cleaned_data['order']:
            prop_order = self.cleaned_data['order'].display_field[5:]
            return sqs.order_by(prop_order)
        else:
            return sqs.order_by('-django_ct')
        
class AdvFacetedSearchForm(AdvancedSearchForm):
    def __init__(self, *args, **kwargs):
        self.selected_facets = kwargs.pop("selected_facets", [])
        super(AdvFacetedSearchForm, self).__init__(*args, **kwargs)

    def search(self):
        sqs = super(AdvFacetedSearchForm, self).search()

        # We need to process each facet to ensure that the field name and the
        # value are quoted correctly and separately:
        for facet in self.selected_facets:
            if ":" not in facet:
                continue

            field, value = facet.split(":", 1)

            if value:
                try:
                    control_value = ControlField.objects.filter(pk=sqs.query.clean(value))
                    if control_value:
                        value_tree = control_value[0].get_descendants(include_self=True)
                        sq = SQ()
                        for index, node in enumerate(value_tree):
                            kwargs = {str("%s" % (field)) : str("%s" % (node.id))}
                            if index == 0:
                                sq = SQ(**kwargs)
                            else:
                                sq = sq | SQ(**kwargs)
                        sqs = sqs.filter(sq)                    
                except ValueError:
                   pass
        return sqs
        
class AdvModelSearchForm(AdvFacetedSearchForm):
    def __init__(self, *args, **kwargs):
        super(AdvModelSearchForm, self).__init__(*args, **kwargs)
        self.fields['models'] = forms.MultipleChoiceField(choices=model_choices(), required=False, label='Limit Search To:', widget=forms.CheckboxSelectMultiple)

    def get_models(self):
        """Return an alphabetical list of model classes in the index."""
        search_models = []

        if self.is_valid():
            for model in self.cleaned_data['models']:
                search_models.append(models.get_model(*model.split('.')))

        return search_models

    def search(self):
        sqs = super(AdvModelSearchForm, self).search()
        return sqs.models(*self.get_models())        