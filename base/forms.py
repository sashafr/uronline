from django import forms
from haystack.forms import ModelSearchForm, SearchForm
from base.models import DescriptiveProperty
from haystack.inputs import Raw
from haystack.query import SearchQuerySet
import re
from haystack.query import SQ

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

class PropertySelectorSearchForm(ModelSearchForm):
    property = forms.ModelChoiceField(required=False, label=('Property'), queryset=DescriptiveProperty.objects.all(), empty_label="Any")
    q = forms.CharField(required=False, label=(''), widget=forms.TextInput(attrs={'type': 'search'}))
    
    def __init__(self, *args, **kwargs):
        super(PropertySelectorSearchForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = [ 'property', 'q' , 'models']
        
    def no_query_found(self):
        return self.searchqueryset.all()
        
    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(PropertySelectorSearchForm, self).search()

        if not self.is_valid():
            return self.no_query_found()
            
        if self.cleaned_data['property'] != None:
            prop = self.cleaned_data['property']
        
            sqs = SearchQuerySet().filter(content=Raw('prop_' + str(prop.id) + ':' + self.cleaned_data['q']))
        
        return sqs
        
class AdvancedSearchForm(SearchForm):
    property = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(visible=True), empty_label="Any")
    search_type = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    q = forms.CharField(label='', required=False)
    op = forms.ChoiceField(label='', required=False, choices=OPERATOR)
    property2 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(visible=True), empty_label="Any")
    search_type2 = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    q2 = forms.CharField(label='', required=False)
    op2 = forms.ChoiceField(label='', required=False, choices=OPERATOR)
    property3 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(visible=True), empty_label="Any")
    search_type3 = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    q3 = forms.CharField(label='', required=False)
    
    def __init__(self, *args, **kwargs):
        super(AdvancedSearchForm, self).__init__(*args, **kwargs)    
        
    def search(self):
    
        sqs = SearchQuerySet().facet('prop_19_exact')   
        
        if not self.is_valid():
            return self.no_query_found()
            
        prop_list = [self.cleaned_data['property'], self.cleaned_data['property2'], self.cleaned_data['property3']]
        type_list = [self.cleaned_data['search_type'], self.cleaned_data['search_type2'], self.cleaned_data['search_type3']]
        query_list = [self.cleaned_data['q'], self.cleaned_data['q2'], self.cleaned_data['q3']]
        op_list = [self.cleaned_data['op'], self.cleaned_data['op2']]
        
        # query object for building full advanced query
        sq = SQ()

        for j in range(0, len(prop_list)):
        
            prop = 'content'
            type = type_list[j]
            query = query_list[j]
            operator = ''            
            negate = False
            kwargs = {}

            # Check for operator
            if j > 0:
                operator = op_list[j - 1]
            
            # Check for not
            if type.startswith('!'):
                negate = True
                type = type[1:]            
            
            # if this row of query builder is blank, skip
            if (query == '') and (type != 'blank'):
                continue
                
            # Check if a property was selected
            if prop_list[j] != None:
                prop = 'prop_'+ str(prop_list[j].id)
                
            # Check if search type was selected
            if type == '':
                type = 'contains'               
                
            # Determine the type of search
                
            # CONTAINS -> special case misspellings
            if type == 'contains':
            
                add_or = False
            
                query_text = '('
            
                # special misspellings
                if prop == 'prop_23':
                    #if doing a contains search for u number, get first instance of numbers followed by a 0 or 1 letter
                    match = re.search(r'(\d+[a-zA-Z]?)', query)
                    if match:
                        query = match.group(0)
                        query_text += ('' + query + '?')
                        add_or = True
                else:
                    query = re.sub(r'(\s*)([uU]\s*?\.?\s*)(\d+)([a-zA-Z]*)', r'\1u* *\3*', query)
                    query = re.sub(r'(\s*)([pP][gG]\s*?[\./]?\s*)(\w+)', r'\1pg* *\3*', query)
                
                keywords = query.split()
                
                if keywords:
                    
                    if add_or:
                        query_text += ' OR '
                
                    query_text += '('
                
                    for i, word in enumerate(keywords):
                        
                        if i > 0: 
                            query_text += ' AND '
                        query_text += word
                    
                    query_text += '))'
                    
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

        sqs = sqs.filter(sq)                
 
        return sqs
        
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
                sqs = sqs.narrow(u'%s:"%s"' % (field, sqs.query.clean(value)))

        return sqs