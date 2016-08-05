from django import forms
from haystack.forms import SearchForm, model_choices
from base.models import *
from haystack.inputs import Raw
from haystack.query import SearchQuerySet, SQ, RelatedSearchQuerySet
from django.db import models
import re
from mptt.forms import TreeNodeChoiceField
from django_select2 import AutoModelSelect2Field, AutoHeavySelect2Widget,AutoModelSelect2MultipleField, AutoHeavySelect2MultipleWidget

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

class SubjectChoices(AutoModelSelect2Field):
    queryset = Subject.objects
    search_fields = ['title__icontains', 'title1__icontains', 'title2__icontains', 'title3__icontains',]
    
class MediaChoices(AutoModelSelect2Field):
    queryset = Media.objects
    search_fields = ['title__icontains', 'title1__icontains', 'title2__icontains', 'title3__icontains',]    

class LocationChoices(AutoModelSelect2Field):
    queryset = Location.objects
    search_fields = ['title__icontains', 'title1__icontains', 'title2__icontains', 'title3__icontains',] 
    
class PersonOrgChoices(AutoModelSelect2Field):
    queryset = PersonOrg.objects
    search_fields = ['title__icontains', 'title1__icontains', 'title2__icontains', 'title3__icontains',]
    
class FileChoices(AutoModelSelect2Field):
    queryset = File.objects
    search_fields = ['title__icontains', 'title1__icontains', 'title2__icontains', 'title3__icontains',]

class AdvancedSearchForm(SearchForm):
    """Search form allows user to search Solr index by property
    
    This allows the user to specify the property, type of search and
    AND/OR methods for combining searches"""
    
    keyword = forms.CharField(label='Keywords', required=False)    
    
    # Dynamic Search Fields
    def __init__(self, *args, **kwargs):
        super(AdvancedSearchForm, self).__init__(*args, **kwargs)
        
        custom_fields = ResultProperty.objects.filter(display_field__startswith = 'subj', field_type__visible = True)
        
        if custom_fields:
            for i, custom_field in enumerate(custom_fields):
                if custom_field.field_type:
                    cus_lab = custom_field.field_type.property
                    if custom_field.field_type.control_field:
                        self.fields['custom_' + custom_field.display_field] = forms.TreeNodeChoiceField(label=cus_lab, required = False, queryset = ControlField.objects.filter(type = custom_field.field_type), empty_label='Any')
                    else:
                        self.fields['custom_' + custom_field.display_field] = forms.CharField(label = cus_lab, required = False)    
    
    # Advanced Search Fields
    property = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible=True).filter(Q(primary_type='SO') | Q(primary_type='AL')), empty_label="Any")
    search_type = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q = forms.CharField(label='Search Terms', required=False)
    op = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property2 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible=True).filter(Q(primary_type='SO') | Q(primary_type='AL')), empty_label="Any")
    search_type2 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q2 = forms.CharField(label='Search Terms', required=False)
    op2 = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property3 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible=True).filter(Q(primary_type='SO') | Q(primary_type='AL')), empty_label="Any")
    search_type3 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q3 = forms.CharField(label='Search Terms', required=False)
    order = forms.ModelChoiceField(label='', required=False, queryset=ResultProperty.objects.filter(display_field__startswith='subj_title'))
    
    # filters
    loc = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )
    med = MediaChoices(
        label = Media._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Media._meta.verbose_name
            }
        )
    )
    po = PersonOrgChoices(
        label = PersonOrg._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % PersonOrg._meta.verbose_name
            }
        )
    )    
    # img = forms.ChoiceField(label='Image', required=False, choices=(('default', '---'), ('yes', 'Yes'), ('no', 'No')))
    col = forms.ModelChoiceField(label='Collection', required=False, queryset=Collection.objects.all())         

    def search(self):
        """This search method starts from a new query of all documents
        in the index instead of getting the existing SearchQuerySet from the super class. This is mainly to clear the default
        query of the index for the value of q. HOWEVER, this requires
        redoing any actions normally taken before the SearchForm 
        is called, such as faceting the SearchQuerySet."""
        
        sqs = SearchQuerySet()
        
        sqs = sqs.filter(django_ct = 'base.subject')        
        
        # faceting must be done here manually b/c we are creating a new SearchQuerySet
        facet_fields = DescriptiveProperty.objects.filter(control_field = True, visible = True)
        for facet_field in facet_fields:
            sqs = sqs.facet('facet_prop_' + str(facet_field.pk))
        
        if not self.is_valid():
            return self.no_query_found()
            
        prop_list = [self.cleaned_data['property'], self.cleaned_data['property2'], self.cleaned_data['property3']]
        type_list = [self.cleaned_data['search_type'], self.cleaned_data['search_type2'], self.cleaned_data['search_type3']]
        query_list = [self.cleaned_data['q'], self.cleaned_data['q2'], self.cleaned_data['q3']]
        op_list = [self.cleaned_data['op'], self.cleaned_data['op2']]
        
        # KEYWORD SEARCH
        if self.cleaned_data['keyword']:
            pg_fix = re.sub(r'(\s*)([pPlL][gG]?)(\s*?[\./]?\s*)(\d+)', r'\1\2* *\4*', self.cleaned_data['keyword'])
            sqs = sqs.filter(content = pg_fix)        
        
        # SELECTED FIELDS SEARCH
        custom_fields = ResultProperty.objects.filter(display_field__startswith = 'sub')
        
        if custom_fields:
            for custom_field in custom_fields:
                if 'custom_' + custom_field.display_field in self.cleaned_data:
                    if custom_field.field_type and custom_field.field_type.control_field and self.cleaned_data['custom_' + custom_field.display_field] != None:
                        value_tree = self.cleaned_data['custom_' + custom_field.display_field].get_descendants(include_self=True)
                        tsq = SQ()
                        for index, node in enumerate(value_tree):
                            kwargs = {'facet_prop_' + str(custom_field.field_type.pk) : node.id}                    
                            if index == 0:
                                tsq = SQ(**kwargs)
                            else:
                                tsq = tsq | SQ(**kwargs)
                        sqs = sqs.filter(tsq)
                    elif self.cleaned_data['custom_' + custom_field.display_field] != '':
                        kwargs = {'prop_' + str(custom_field.field_type.pk) : self.cleaned_data['custom_' + custom_field.display_field]}
                        sqs = sqs.filter(**kwargs)

        # RELATED TABLES FILTER
        loc = self.cleaned_data['loc']
        if loc != None and loc != '':
            loc_rels = Subject.objects.filter(locationsubjectrelations__location_id=loc).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = loc_rels)
            
        med = self.cleaned_data['med']
        if med != None and med != '':
            med_rels = Subject.objects.filter(mediasubjectrelations__media_id=med).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = med_rels)

        po = self.cleaned_data['po']
        if po != None and po != '':
            po_rels = Subject.objects.filter(subjectpersonorgrelations__person_org_id=po).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = po_rels)
            
        # img = self.cleaned_data['img']
        # if img != None and img != '':
            # imgs = ['jpg', 'jpeg', 'png', 'tif', 'JPG', 'JPEG', 'PNG', 'TIF']
            # if img == 'yes':
                # img_subs = Subject.objects.filter(subjectfile__rsid__filetype__in = imgs).values_list('id', flat=True)
            # else:
                # img_subs = Subject.objects.exclude(subjectfile__rsid__filetype__in = imgs).values_list('id', flat=True)
            # sqs = sqs.filter(django_id__in = img_subs)
            
        col = self.cleaned_data['col']
        if col != None and col != '':
            sub_cols = Subject.objects.filter(subjectcollection__collection_id = col).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = sub_cols)                        
        
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
            prop_order = 'prop_' + str(self.cleaned_data['order'].field_type.id)
            return sqs.order_by(prop_order)
        else:
            return sqs.order_by('-django_ct')
            
class LocationAdvancedSearchForm(SearchForm):
    """Search form allows user to search Solr index by property
    
    This allows the user to specify the property, type of search and
    AND/OR methods for combining searches"""   
    
    keyword = forms.CharField(label='Keywords', required=False)    
    
    # Dynamic Search Fields
    def __init__(self, *args, **kwargs):
        super(LocationAdvancedSearchForm, self).__init__(*args, **kwargs)
        
        custom_fields = ResultProperty.objects.filter(display_field__startswith = 'loc', field_type__visible = True)
        
        if custom_fields:
            for i, custom_field in enumerate(custom_fields):
                if custom_field.field_type:
                    cus_lab = custom_field.field_type.property
                    if custom_field.field_type.control_field:
                        self.fields['custom_' + custom_field.display_field] = forms.TreeNodeChoiceField(label=cus_lab, required = False, queryset = ControlField.objects.filter(type = custom_field.field_type), empty_label='Any')
                    else:
                        self.fields['custom_' + custom_field.display_field] = forms.CharField(label = cus_lab, required = False)
    
    # Advanced Search Fields
    property = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='SL') | Q(primary_type='AL')), empty_label="Any")
    search_type = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q = forms.CharField(label='Search Terms', required=False)
    op = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property2 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='SL') | Q(primary_type='AL')), empty_label="Any")
    search_type2 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q2 = forms.CharField(label='Search Terms', required=False)
    op2 = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property3 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='SL') | Q(primary_type='AL')), empty_label="Any")
    search_type3 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q3 = forms.CharField(label='Search Terms', required=False)
    order = forms.ModelChoiceField(label='', required=False, queryset=ResultProperty.objects.filter(display_field__startswith='loc'))

    # filters
    sub = SubjectChoices(
        label = Subject._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Subject._meta.verbose_name
            }
        )
    )
    med = MediaChoices(
        label = Media._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Media._meta.verbose_name
            }
        )
    )
    po = PersonOrgChoices(
        label = PersonOrg._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % PersonOrg._meta.verbose_name
            }
        )
    )    
    # img = forms.ChoiceField(label='Image', required=False, choices=(('default', '---'), ('yes', 'Yes'), ('no', 'No')))
    col = forms.ModelChoiceField(label='Collection', required=False, queryset=Collection.objects.all())   

    def search(self):
        """This search method starts from a new query of all documents
        in the index instead of getting the existing SearchQuerySet from the super class. This is mainly to clear the default
        query of the index for the value of q. HOWEVER, this requires
        redoing any actions normally taken before the SearchForm 
        is called, such as faceting the SearchQuerySet."""
              
        sqs = SearchQuerySet()
        
        sqs = sqs.filter(django_ct = 'base.location')
        
        # faceting must be done here manually b/c we are creating a new SearchQuerySet
        facet_fields = DescriptiveProperty.objects.filter(control_field = True, visible = True)
        for facet_field in facet_fields:
            sqs = sqs.facet('facet_prop_' + str(facet_field.pk))
        
        if not self.is_valid():
            return self.no_query_found()
            
        prop_list = [self.cleaned_data['property'], self.cleaned_data['property2'], self.cleaned_data['property3']]
        type_list = [self.cleaned_data['search_type'], self.cleaned_data['search_type2'], self.cleaned_data['search_type3']]
        query_list = [self.cleaned_data['q'], self.cleaned_data['q2'], self.cleaned_data['q3']]
        op_list = [self.cleaned_data['op'], self.cleaned_data['op2']]

        # KEYWORD SEARCH
        if self.cleaned_data['keyword']:
            pg_fix = re.sub(r'(\s*)([pPlL][gG]?)(\s*?[\./]?\s*)(\d+)', r'\1\2* *\4*', self.cleaned_data['keyword'])
            sqs = sqs.filter(content = pg_fix)
        
        # SELECTED FIELDS SEARCH
        custom_fields = ResultProperty.objects.filter(display_field__startswith = 'loc')
        
        if custom_fields:
            for custom_field in custom_fields:
                if 'custom_' + custom_field.display_field in self.cleaned_data:
                    if custom_field.field_type and custom_field.field_type.control_field and self.cleaned_data['custom_' + custom_field.display_field] != None:
                        value_tree = self.cleaned_data['custom_' + custom_field.display_field].get_descendants(include_self=True)
                        tsq = SQ()
                        for index, node in enumerate(value_tree):
                            kwargs = {'facet_prop_' + str(custom_field.field_type.pk) : node.id}                    
                            if index == 0:
                                tsq = SQ(**kwargs)
                            else:
                                tsq = tsq | SQ(**kwargs)
                        sqs = sqs.filter(tsq)
                    elif self.cleaned_data['custom_' + custom_field.display_field] != '':
                        kwargs = {'prop_' + str(custom_field.field_type.pk) : self.cleaned_data['custom_' + custom_field.display_field]}
                        sqs = sqs.filter(**kwargs)

        # RELATED TABLES FILTER
        sub = self.cleaned_data['sub']
        if sub != None and sub != '':
            sub_rels = Location.objects.filter(locationsubjectrelations__subject_id=sub).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = sub_rels)
            
        med = self.cleaned_data['med']
        if med != None and med != '':
            med_rels = Location.objects.filter(medialocationrelations__media_id=med).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = med_rels)

        po = self.cleaned_data['po']
        if po != None and po != '':
            po_rels = Location.objects.filter(locationpersonorgrelations__person_org_id=po).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = po_rels)
            
        # img = self.cleaned_data['img']
        # if img != None and img != '':
            # imgs = ['jpg', 'jpeg', 'png', 'tif', 'JPG', 'JPEG', 'PNG', 'TIF']
            # if img == 'yes':
                # img_locs = Location.objects.filter(locationfile__rsid__filetype__in = imgs).values_list('id', flat=True)
            # else:
                # img_locs = Location.objects.exclude(locationfile__rsid__filetype__in = imgs).values_list('id', flat=True)
            # sqs = sqs.filter(django_id__in = img_locs)
            
        col = self.cleaned_data['col']
        if col != None and col != '':
            loc_cols = Location.objects.filter(locationcollection__collection_id = col).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = loc_cols)
        
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
                if prop_list[j].control_field:
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
            prop_order = 'prop_' + str(self.cleaned_data['order'].field_type.id)
            return sqs.order_by(prop_order)
        else:
            return sqs.order_by('-django_ct')

class MediaAdvancedSearchForm(SearchForm):
    """Search form allows user to search Solr index by property
    
    This allows the user to specify the property, type of search and
    AND/OR methods for combining searches"""   
    
    keyword = forms.CharField(label='Keywords', required=False)    
    
    # Dynamic Search Fields
    def __init__(self, *args, **kwargs):
        super(MediaAdvancedSearchForm, self).__init__(*args, **kwargs)
        
        custom_fields = ResultProperty.objects.filter(display_field__startswith = 'med', field_type__visible = True)
        
        if custom_fields:
            for i, custom_field in enumerate(custom_fields):
                if custom_field.field_type:
                    cus_lab = custom_field.field_type.property
                    if custom_field.field_type.control_field:
                        self.fields['custom_' + custom_field.display_field] = forms.TreeNodeChoiceField(label=cus_lab, required = False, queryset = ControlField.objects.filter(type = custom_field.field_type), empty_label='Any')
                    else:
                        self.fields['custom_' + custom_field.display_field] = forms.CharField(label = cus_lab, required = False)
    
    # Advanced Search Fields
    property = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='MP') | Q(primary_type='AL')), empty_label="Any")
    search_type = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q = forms.CharField(label='Search Terms', required=False)
    op = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property2 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='MP') | Q(primary_type='AL')), empty_label="Any")
    search_type2 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q2 = forms.CharField(label='Search Terms', required=False)
    op2 = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property3 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='MP') | Q(primary_type='AL')), empty_label="Any")
    search_type3 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q3 = forms.CharField(label='Search Terms', required=False)
    order = forms.ModelChoiceField(label='', required=False, queryset=ResultProperty.objects.filter(display_field__startswith='med'))

    # filters
    sub = SubjectChoices(
        label = Subject._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Subject._meta.verbose_name
            }
        )
    )
    loc = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )
    po = PersonOrgChoices(
        label = PersonOrg._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % PersonOrg._meta.verbose_name
            }
        )
    )    
    # img = forms.ChoiceField(label='Image', required=False, choices=(('default', '---'), ('yes', 'Yes'), ('no', 'No')))
    col = forms.ModelChoiceField(label='Collection', required=False, queryset=Collection.objects.all())   

    def search(self):
        """This search method starts from a new query of all documents
        in the index instead of getting the existing SearchQuerySet from the super class. This is mainly to clear the default
        query of the index for the value of q. HOWEVER, this requires
        redoing any actions normally taken before the SearchForm 
        is called, such as faceting the SearchQuerySet."""
              
        sqs = SearchQuerySet()
        
        sqs = sqs.filter(django_ct = 'base.media')
        
        # faceting must be done here manually b/c we are creating a new SearchQuerySet
        facet_fields = DescriptiveProperty.objects.filter(control_field = True, visible = True)
        for facet_field in facet_fields:
            sqs = sqs.facet('facet_prop_' + str(facet_field.pk))
        
        if not self.is_valid():
            return self.no_query_found()
            
        prop_list = [self.cleaned_data['property'], self.cleaned_data['property2'], self.cleaned_data['property3']]
        type_list = [self.cleaned_data['search_type'], self.cleaned_data['search_type2'], self.cleaned_data['search_type3']]
        query_list = [self.cleaned_data['q'], self.cleaned_data['q2'], self.cleaned_data['q3']]
        op_list = [self.cleaned_data['op'], self.cleaned_data['op2']]
        
        # KEYWORD SEARCH
        if self.cleaned_data['keyword']:
            pg_fix = re.sub(r'(\s*)([pPlL][gG]?)(\s*?[\./]?\s*)(\d+)', r'\1\2* *\4*', self.cleaned_data['keyword'])
            sqs = sqs.filter(content = pg_fix)        
        
        # SELECTED FIELDS SEARCH
        custom_fields = ResultProperty.objects.filter(display_field__startswith = 'med')
        
        if custom_fields:
            for custom_field in custom_fields:
                if 'custom_' + custom_field.display_field in self.cleaned_data:
                    if custom_field.field_type and custom_field.field_type.control_field and self.cleaned_data['custom_' + custom_field.display_field] != None:
                        value_tree = self.cleaned_data['custom_' + custom_field.display_field].get_descendants(include_self=True)
                        tsq = SQ()
                        for index, node in enumerate(value_tree):
                            kwargs = {'facet_prop_' + str(custom_field.field_type.pk) : node.id}                    
                            if index == 0:
                                tsq = SQ(**kwargs)
                            else:
                                tsq = tsq | SQ(**kwargs)
                        sqs = sqs.filter(tsq)
                    elif self.cleaned_data['custom_' + custom_field.display_field] != '':
                        kwargs = {'prop_' + str(custom_field.field_type.pk) : self.cleaned_data['custom_' + custom_field.display_field]}
                        sqs = sqs.filter(**kwargs)

        # RELATED TABLES FILTER
        sub = self.cleaned_data['sub']
        if sub != None and sub != '':
            sub_rels = Media.objects.filter(mediasubjectrelations__subject_id=sub).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = sub_rels)
            
        loc = self.cleaned_data['loc']
        if loc != None and loc != '':
            loc_rels = Media.objects.filter(medialocationrelations__location_id=loc).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = loc_rels)

        po = self.cleaned_data['po']
        if po != None and po != '':
            po_rels = Media.objects.filter(mediapersonorgrelations__person_org_id=po).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = po_rels)
            
        # img = self.cleaned_data['img']
        # if img != None and img != '':
            # imgs = ['jpg', 'jpeg', 'png', 'tif', 'JPG', 'JPEG', 'PNG', 'TIF']
            # if img == 'yes':
                # img_med = Media.objects.filter(mediafile__rsid__filetype__in = imgs).values_list('id', flat=True)
            # else:
                # img_med = Media.objects.exclude(mediafile__rsid__filetype__in = imgs).values_list('id', flat=True)
            # sqs = sqs.filter(django_id__in = img_med)
            
        col = self.cleaned_data['col']
        if col != None and col != '':
            med_cols = Media.objects.filter(mediacollection__collection_id = col).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = med_cols)
        
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
                if prop_list[j].control_field:
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
            prop_order = 'prop_' + str(self.cleaned_data['order'].field_type.id)
            return sqs.order_by(prop_order)
        else:
            return sqs.order_by('-django_ct')
        
class PeopleAdvancedSearchForm(SearchForm):
    """Search form allows user to search Solr index by property
    
    This allows the user to specify the property, type of search and
    AND/OR methods for combining searches"""   
    
    keyword = forms.CharField(label='Keywords', required=False)    
    
    # Dynamic Search Fields
    def __init__(self, *args, **kwargs):
        super(PeopleAdvancedSearchForm, self).__init__(*args, **kwargs)
        
        custom_fields = ResultProperty.objects.filter(display_field__startswith = 'po', field_type__visible = True)
        
        if custom_fields:
            for i, custom_field in enumerate(custom_fields):
                if custom_field.field_type:
                    cus_lab = custom_field.field_type.property
                    if custom_field.field_type.control_field:
                        self.fields['custom_' + custom_field.display_field] = forms.TreeNodeChoiceField(label=cus_lab, required = False, queryset = ControlField.objects.filter(type = custom_field.field_type), empty_label='Any')
                    else:
                        self.fields['custom_' + custom_field.display_field] = forms.CharField(label = cus_lab, required = False)
    
    # Advanced Search Fields
    property = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='PO') | Q(primary_type='AL')), empty_label="Any")
    search_type = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q = forms.CharField(label='Search Terms', required=False)
    op = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property2 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='PO') | Q(primary_type='AL')), empty_label="Any")
    search_type2 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q2 = forms.CharField(label='Search Terms', required=False)
    op2 = forms.ChoiceField(label='And/Or', required=False, choices=OPERATOR)
    property3 = forms.ModelChoiceField(label='Field', required=False, queryset=DescriptiveProperty.objects.filter(visible = True).filter(Q(primary_type='PO') | Q(primary_type='AL')), empty_label="Any")
    search_type3 = forms.ChoiceField(label='Search Type', required=False, choices=SEARCH_TYPE)
    q3 = forms.CharField(label='Search Terms', required=False)
    order = forms.ModelChoiceField(label='', required=False, queryset=ResultProperty.objects.filter(display_field__startswith='po'))

    # filters
    sub = SubjectChoices(
        label = Subject._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Subject._meta.verbose_name
            }
        )
    )
    med = MediaChoices(
        label = Media._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Media._meta.verbose_name
            }
        )
    )
    loc = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )    
    # img = forms.ChoiceField(label='Image', required=False, choices=(('default', '---'), ('yes', 'Yes'), ('no', 'No')))
    col = forms.ModelChoiceField(label='Collection', required=False, queryset=Collection.objects.all())   

    def search(self):
        """This search method starts from a new query of all documents
        in the index instead of getting the existing SearchQuerySet from the super class. This is mainly to clear the default
        query of the index for the value of q. HOWEVER, this requires
        redoing any actions normally taken before the SearchForm 
        is called, such as faceting the SearchQuerySet."""
              
        sqs = SearchQuerySet()
        
        sqs = sqs.filter(django_ct = 'base.personorg')
        
        # faceting must be done here manually b/c we are creating a new SearchQuerySet
        facet_fields = DescriptiveProperty.objects.filter(control_field = True, visible = True)
        for facet_field in facet_fields:
            sqs = sqs.facet('facet_prop_' + str(facet_field.pk))
        
        if not self.is_valid():
            return self.no_query_found()
            
        prop_list = [self.cleaned_data['property'], self.cleaned_data['property2'], self.cleaned_data['property3']]
        type_list = [self.cleaned_data['search_type'], self.cleaned_data['search_type2'], self.cleaned_data['search_type3']]
        query_list = [self.cleaned_data['q'], self.cleaned_data['q2'], self.cleaned_data['q3']]
        op_list = [self.cleaned_data['op'], self.cleaned_data['op2']]

        # KEYWORD SEARCH
        if self.cleaned_data['keyword']:
            pg_fix = re.sub(r'(\s*)([pPlL][gG]?)(\s*?[\./]?\s*)(\d+)', r'\1\2* *\4*', self.cleaned_data['keyword'])
            sqs = sqs.filter(content = pg_fix)
        
        # SELECTED FIELDS SEARCH
        custom_fields = ResultProperty.objects.filter(display_field__startswith = 'po')
        
        if custom_fields:
            for custom_field in custom_fields:
                if 'custom_' + custom_field.display_field in self.cleaned_data:
                    if custom_field.field_type and custom_field.field_type.control_field and self.cleaned_data['custom_' + custom_field.display_field] != None:
                        value_tree = self.cleaned_data['custom_' + custom_field.display_field].get_descendants(include_self=True)
                        tsq = SQ()
                        for index, node in enumerate(value_tree):
                            kwargs = {'facet_prop_' + str(custom_field.field_type.pk) : node.id}                    
                            if index == 0:
                                tsq = SQ(**kwargs)
                            else:
                                tsq = tsq | SQ(**kwargs)
                        sqs = sqs.filter(tsq)
                    elif self.cleaned_data['custom_' + custom_field.display_field] != '':
                        kwargs = {'prop_' + str(custom_field.field_type.pk) : self.cleaned_data['custom_' + custom_field.display_field]}
                        sqs = sqs.filter(**kwargs)

        # RELATED TABLES FILTER
        sub = self.cleaned_data['sub']
        if sub != None and sub != '':
            sub_rels = PersonOrg.objects.filter(subjectpersonorgrelations__subject_id=sub).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = sub_rels)
            
        med = self.cleaned_data['med']
        if med != None and med != '':
            med_rels = PersonOrg.objects.filter(mediapersonorgrelations__media_id=med).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = med_rels)

        loc = self.cleaned_data['loc']
        if loc != None and loc != '':
            loc_rels = PersonOrg.objects.filter(locationpersonorgrelations__location_id=po).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = loc_rels)
            
        # img = self.cleaned_data['img']
        # if img != None and img != '':
            # imgs = ['jpg', 'jpeg', 'png', 'tif', 'JPG', 'JPEG', 'PNG', 'TIF']
            # if img == 'yes':
                # img_po = PersonOrg.objects.filter(personorgfile__rsid__filetype__in = imgs).values_list('id', flat=True)
            # else:
                # img_po = PersonOrg.objects.exclude(personorgfile__rsid__filetype__in = imgs).values_list('id', flat=True)
            # sqs = sqs.filter(django_id__in = img_po)
            
        col = self.cleaned_data['col']
        if col != None and col != '':
            po_cols = PersonOrg.objects.filter(personorgcollection__collection_id = col).values_list('id', flat=True)
            sqs = sqs.filter(django_id__in = po_cols)
        
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
                if prop_list[j].control_field:
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
            prop_order = 'prop_' + str(self.cleaned_data['order'].field_type.id)
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
        
class LocationFacetedSearchForm(LocationAdvancedSearchForm):
    def __init__(self, *args, **kwargs):
        self.selected_facets = kwargs.pop("selected_facets", [])
        super(LocationFacetedSearchForm, self).__init__(*args, **kwargs)

    def search(self):
        sqs = super(LocationFacetedSearchForm, self).search()

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

class MediaFacetedSearchForm(MediaAdvancedSearchForm):
    def __init__(self, *args, **kwargs):
        self.selected_facets = kwargs.pop("selected_facets", [])
        super(MediaFacetedSearchForm, self).__init__(*args, **kwargs)

    def search(self):
        sqs = super(MediaFacetedSearchForm, self).search()

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

class PeopleFacetedSearchForm(PeopleAdvancedSearchForm):
    def __init__(self, *args, **kwargs):
        self.selected_facets = kwargs.pop("selected_facets", [])
        super(PeopleFacetedSearchForm, self).__init__(*args, **kwargs)

    def search(self):
        sqs = super(PeopleFacetedSearchForm, self).search()

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
        self.fields['models'] = forms.MultipleChoiceField(choices=model_choices(), required=False, label='Limit Search To:', widget=forms.SelectMultiple)

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
        
class FileUploadForm(forms.Form):
    """Simple form used to upload files via the admin interface"""
    
    file = forms.FileField(label='File', required=True)
    
class BulkAddCollectionForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    collection = forms.ModelChoiceField(queryset=Collection.objects.all())
    notes = forms.CharField(required=False)
    
class BulkEditForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    property = forms.ModelChoiceField(queryset = DescriptiveProperty.objects.all())
    cf_value = TreeNodeChoiceField(required = False, queryset = ControlField.objects.all(), label = 'Controlled Term')
    ff_value = forms.CharField(required = False, label = 'Free-Form Value')
    inline_notes = forms.CharField(required = False)
    footnotes = forms.CharField(required = False)
    overwrite = forms.BooleanField(required = False)
    delete_only = forms.BooleanField(required = False, label = 'Delete Only - Do Not Add')