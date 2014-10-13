from django.contrib import admin
from base.models import *
from base.forms import AdvancedSearchForm
from django.forms.formsets import formset_factory
from django.db.models import Q
import re
from django.forms import Textarea

class StatusFilter(admin.SimpleListFilter):

    title = 'Status'
    
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        properties = tuple((prop.id, prop.property) for prop in DescriptiveProperty.objects.all())    
        return properties

    def queryset(self, request, queryset):
        if self.value():
            prop_id = self.value()
            return queryset.filter(subjectproperty__property = prop_id)

class SubjectPropertyInline(admin.TabularInline):
    model = SubjectProperty
    fields = ['property', 'property_value', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    ordering = ('property__order',)
    suit_classes = 'suit-tab suit-tab-general'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'property':
            kwargs["queryset"] = DescriptiveProperty.objects.filter(Q(primary_type='SO') | Q(primary_type='AL'))
        return super(SubjectPropertyInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
class MediaSubjectRelationsInline(admin.TabularInline):
    model = MediaSubjectRelations
    fields = ['media', 'relation_type', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)        
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_classes = 'suit-tab suit-tab-general'    
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'media':
            kwargs["queryset"] = Media.objects.filter(type__type = 'publication')
        return super(MediaSubjectRelationsInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
    def get_queryset(self, request):
        qs = super(MediaSubjectRelationsInline, self).get_queryset(request)
        return qs.filter(relation_type=2)
        
class SubjectSubjectRelationsInline(admin.TabularInline):
    model = SubjectSubjectRelations
    fk_name = "subject1"
    fields = ['subject2', 'relation_type', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)        
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_classes = 'suit-tab suit-tab-general'    
        
class FileInline(admin.TabularInline):
    model = File
    fields = ['get_thumbnail', 'media', 'relation_type', 'notes', 'last_mod_by']
    readonly_fields = ('get_thumbnail', 'last_mod_by',)        
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_classes = 'suit-tab suit-tab-files'    
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'media':
            kwargs["queryset"] = Media.objects.filter(type__type = 'image/jpeg')
        return super(FileInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
class SubjectAdmin(admin.ModelAdmin):
    readonly_fields = ('last_mod_by',)    
    inlines = [SubjectPropertyInline, MediaSubjectRelationsInline, FileInline]
    search_fields = ['title']
    list_display = ('id1', 'id2', 'id3', 'desc1', 'desc2', 'desc3')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_form_tabs = (('general', 'General'), ('files', 'Files'))
    fieldsets = [
        (None, {
            'classes': ('suit-tab', 'suit-tab-general'),
            'fields': ['title', 'notes', 'last_mod_by']
        }),
    ]
    
    change_list_template = 'admin/base/subject/change_list.html'
    change_form_template = 'admin/base/change_form.html'
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, SubjectProperty) or isinstance(instance, MediaSubjectRelations): #Check if it is the correct type of inline
                instance.last_mod_by = request.user            
                instance.save()
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['advanced_formset'] = 'test for context'
        return super(SubjectAdmin, self).changelist_view(request, extra_context=extra_context)
        
    def get_search_results(self, request, queryset, search_term):
        '''Override the regular keyword search to perform the advanced search
        
        Because of the modified search_form.html template, the search_term will be specially
        generated to work with this method. Each set of queries is delimited by ??? and takes
        the form [&AND/OR]PROPERTY___SEARCH_TYPE___[SEARCH_KEYWORDS]??? This search method will 
        return inaccurate results if someone searches ??? as a keyword
        '''
        queryset, use_distinct = super(SubjectAdmin, self).get_search_results(request, queryset, search_term)

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
                        queryset = queryset | self.model.objects.filter(current_query)
                    else:
                        if i == 0:
                            # in this case, current query should be the first query, so no connector
                            queryset = self.model.objects.filter(current_query)
                        else:
                            # if connector wasn't set, use &
                            queryset = queryset.filter(current_query)
            
        return queryset.order_by('id').distinct(), use_distinct

admin.site.register(Subject, SubjectAdmin)

class MediaPropertyInline(admin.TabularInline):
    model = MediaProperty
    fields = ['property', 'property_value', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "property":
            kwargs["queryset"] = DescriptiveProperty.objects.filter(Q(primary_type='MP') | Q(primary_type='AL'))
        return super(MediaPropertyInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class MediaAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['title', 'type', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['title', 'type', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    inlines = [MediaPropertyInline]
    search_fields = ['title', 'notes']
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, MediaProperty) : #Check if it is the correct type of inline
                instance.last_mod_by = request.user            
                instance.save()
    
admin.site.register(Media, MediaAdmin)

class PersonOrgPropertyInline(admin.TabularInline):
    model = PersonOrgProperty
    extra = 3
    fields = ['property', 'property_value', 'last_mod_by']

class PersonOrgAdmin(admin.ModelAdmin):
    fields = ['title', 'notes', 'last_mod_by']
    inlines = [PersonOrgPropertyInline]
    search_fields = ['title']

admin.site.register(PersonOrg, PersonOrgAdmin)

admin.site.register(GlobalVars)
admin.site.register(MediaType)

class DescriptivePropertyAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['property', 'primary_type', 'order', 'visible', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['property', 'primary_type', 'order', 'visible', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    search_fields = ['property']
    list_filter = ('primary_type', 'visible')
    list_editable = ('primary_type', 'order', 'visible', 'notes')
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(DescriptiveProperty, DescriptivePropertyAdmin)
admin.site.register(MediaProperty)
admin.site.register(FeaturedImgs)

class SubjectPropertyAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['subject', 'property', 'property_value', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['subject', 'property', 'property_value', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(SubjectProperty, SubjectPropertyAdmin)
admin.site.register(ResultProperty)
admin.site.register(Relations)

class MediaSubjectRelationsAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['media', 'subject', 'relation_type', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['media', 'subject', 'relation_type', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(MediaSubjectRelations, MediaSubjectRelationsAdmin)

class SubjectSubjectRelationsAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['subject1', 'subject2', 'relation_type', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['subject1', 'subject2', 'relation_type', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(SubjectSubjectRelations, SubjectSubjectRelationsAdmin)
admin.site.register(MediaPersonOrgRelations)
admin.site.register(PersonOrgProperty)

class StatusAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['status', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['status', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
    
admin.site.register(Status, StatusAdmin)