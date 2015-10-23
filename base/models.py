from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from mptt.models import MPTTModel, TreeForeignKey
from django.core.urlresolvers import reverse
import re
from filer.fields.image import FilerImageField
from filer.fields.file import FilerFileField
from django.conf import settings

""" HELPER METHODS """

def get_new_title(obj, type):
    """ Returns the title of an object using the three Title display properties, or, 
    if there is no value for the three Title properties or they aren't set, uses the first
    property with a value, ordered by the Descriptive Property's order. 
    
    Called by the object's save method. """

    new_title = ""
    
    title1 = obj.title1
    title2 = obj.title2
    title3 = obj.title3
    
    if type == 'subject':
        cqs = obj.subjectcontrolproperty_set.all()
        qs = obj.subjectproperty_set.all()
    elif type == 'location':
        cqs = obj.locationcontrolproperty_set.all()
        qs = obj.locationproperty_set.all()
    elif type == 'media':
        cqs = obj.mediacontrolproperty_set.all()
        qs = obj.mediaproperty_set.all()
    elif type == 'people':
        cqs = obj.personorgcontrolproperty_set.all()
        qs = obj.personorgproperty_set.all()        
    else:
        return '(none)'
    
    # if there is no value for any of the Display Properties, check for other properties
    if title1 == "(none)" and title2 == "(none)" and title3 == "(none)":
        props = qs.order_by("property__order")
        cntl_props = cqs.order_by("control_property__order")
        # if there are both control and free-form properties, choose one with lowest order
        if props and cntl_props:
            if props[0].property.order <= cntl_props[0].control_property.order:
                new_title = props[0].property_value
            else:
                new_title = cntl_props[0].control_property_value.title
        # if there are only free form properties, select lowest order free form prop
        elif props:
            new_title = props[0].property_value
        # if there are only control properties, select lowest order control prop
        elif cntl_props:
            new_title = cntl_props[0].control_property_value.title
        # if there are no properties, then title is (none)
        else:
            new_title = "(none)"

    # if there are title Display Properties, combine them
    else:
        combiner = ""
        if title1 != "(none)":
            new_title += title1
            combiner += " | "
        if title2 != "(none)":
            new_title += combiner + title2
            if combiner == "":
                combiner += " | "
        if title3 != "(none)":
            new_title += combiner + title3
                    
    return new_title

def get_display_field(obj, object_type, result_prop):
    """ Returns the selected display field for an object with a concatenation
    of their object property values or (none) if they have not value for the selected
    property. """
    
    id_str = ''
    
    if object_type == 'subj':
        cqs = obj.subjectcontrolproperty_set.all()
        qs = obj.subjectproperty_set.all()
    elif object_type == 'loc':
        cqs = obj.locationcontrolproperty_set.all()
        qs = obj.locationproperty_set.all()
    elif object_type == 'med':
        cqs = obj.mediacontrolproperty_set.all()
        qs = obj.mediaproperty_set.all()
    elif object_type == 'po':
        cqs = obj.personorgcontrolproperty_set.all()
        qs = obj.personorgproperty_set.all()        
    else:
        return id_str   
 
    if result_prop.field_type:
        if result_prop.field_type.control_field:
            ids = cqs.filter(control_property=result_prop.field_type)
        else:
            ids = qs.filter(property=result_prop.field_type_id)
        if ids:
            for i, id in enumerate(ids):
                if i > 0:
                    id_str += ', '
                if result_prop.field_type.control_field:
                    id_str += id.control_property_value.title
                else:
                    id_str += id.property_value
    
    if id_str == '':
        id_str = '(none)'
    
    return id_str
    
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

def get_display_field_header(result_property):
    """ Returns the title of the Descriptive Property currently set as the given Result Property.
    
    If property is not set, returns Not Set. """
    
    title = ResultProperty.objects.filter(display_field = result_property)
    
    if title and title[0].field_type:
        return title[0].field_type.property
    else:
        return "Not Set"

""" HELPER MODELS """

class ObjectType(models.Model):
    """ Sub-groupings of Entities """
    
    type = models.CharField(max_length = 40)
    notes = models.TextField(blank = True)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User) 
    control_field = models.BooleanField(default = False)    

    def __unicode__(self):
        return self.type
        
    class Meta:
        verbose_name = 'Entity Type'
        verbose_name_plural = 'Entity Types'
        
class MediaType(models.Model):
    """ Types of Media, such as image/jpeg, text/html, etc """
    type = models.CharField(max_length = 40)

    def __unicode__(self):
        return self.type
        
class Collection(models.Model):
    """ Groupings of Entities """

    title = models.CharField(max_length=60)
    notes = models.TextField(blank = True)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)    
    owner = models.ForeignKey(User)
    
    def __unicode__(self):
        return self.title        

""" DESCRIPTIVE PROPERTY & CONTROLLED PROPERTY MODELS """

class DescriptiveProperty(models.Model):
    """ Types of descriptive properties (or variables to describe objects) """
    
    SUBJECT_OBJECT = 'SO'
    SUBJECT_LOC = 'SL'
    MEDIA_PUB = 'MP'
    MEDIA_FILE = 'MF'
    PERSON_ORGANIZATION = 'PO'
    ALL = 'AL'
    TYPE = (
        (SUBJECT_OBJECT, 'Object'),
        (SUBJECT_LOC, 'Location'),
        (MEDIA_PUB, 'Publication'),
        (MEDIA_FILE, 'File'),
        (PERSON_ORGANIZATION, 'Person/Organization'),
        (ALL, 'All'),
    )
    
    INT = '_i'
    STRING = '_s'
    LONG = '_l'
    TEXT = '_t'
    BOOLEAN = '_b'
    FLOAT = '_f'
    DOUBLE = '_d'
    DATE = '_dt'
    LOCATION = '_p'
    SOLR_TYPE = (
        (INT, 'Integer'),
        (STRING, 'String'),
        (LONG, 'Long'),
        (TEXT, 'Text'),
        (BOOLEAN, 'Boolean'),
        (DOUBLE, 'Double'),
        (FLOAT, 'Float'),
        (DATE, 'Date'),
        (LOCATION, 'Location'),
    )
    
    GEN = 'gen'
    CON = 'con'
    ARCH = 'arc'
    TEXT = 'txt'
    DATA_SOURCE_TYPE = (
        (GEN, 'General'),
        (CON, 'Conservation-Analytic'),
        (ARCH, 'Archival'),
        (TEXT, 'Textual'),
    )

    property = models.CharField(max_length = 60)
    notes = models.TextField(blank = True, help_text = "Please define this space to define the property.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)
    primary_type = models.CharField(max_length=2, choices=TYPE, default=ALL, blank = True)
    order = models.IntegerField(blank = True, default=99)
    visible = models.BooleanField(default = False)
    solr_type = models.CharField(max_length = 45, choices = SOLR_TYPE, default = TEXT, blank = True)
    facet = models.BooleanField(default = False)
    control_field = models.BooleanField(default = False)
    data_source_type = models.CharField(max_length=3, choices=DATA_SOURCE_TYPE, default = GEN, blank = True)

    def __unicode__(self):
        return self.property
        
    class Meta:
        verbose_name = 'Descriptive Property'
        verbose_name_plural = 'Descriptive Properties'
        ordering = ['order']

class ControlField(MPTTModel):
    """Controlled values for descriptive properties

    Mptt is used to allow for parent-child relationships
    in the values."""
    title = models.CharField(max_length = 60, blank = True)
    notes = models.TextField('Addtional Details Page (HTML)', blank = True, help_text = "This field will be used to generate 'Additional Information' section of this property's Details page. Please define the property and add any other useful information here.")
    definition = models.TextField(blank = True, help_text = "Please use this field to provide a short definition of the meaning of this term.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)
    type = models.ForeignKey(DescriptiveProperty, blank = True, null = True) #type is the descriptive property for which this control field can be a value
    parent = TreeForeignKey('self', null = True, blank = True, related_name = 'children')
    order = models.PositiveIntegerField()
    
    class MPTTMeta:
        order_insertion_by = ['order', 'title']
    
    def __unicode__(self):
        return self.title
        
    class Meta:
        verbose_name = 'Controlled Term'    
        verbose_name_plural = 'Controlled Terms'
        
    def save(self, *args, **kwargs):
        super(ControlField, self).save(*args, **kwargs)
        ControlField.objects.rebuild()
        
    def next(self):
        greaterpk = ControlField.objects.filter(id__gt=self.id, type = self.type).order_by('id')
        if greaterpk:
            return greaterpk[0]
        else:
            return None
            
    def previous(self):
        smallerpk = ControlField.objects.filter(id__lt=self.id).order_by('-id')
        if smallerpk:
            return smallerpk[0]
        else:
            return None
        
    def ancestors(self):
        """ Creates a string representing all the ancestors of this node in tree """
        ancs = self.get_ancestors()
        ancestor_string = ''
        for i, anc in enumerate(ancs):
            if i != 0:
                ancestor_string = ancestor_string + ' >> '                
            ancestor_string = ancestor_string + anc.title
        return ancestor_string
    ancestors.short_description = 'Parent Categories'
    
    def count_subj_instances(self):
        """ Returns the total of all instances of this Control Field as a value in the SubjectControlProperty table.
        
        The count is cumulative, so all descendants are included in the total. """
        tree = self.get_descendants(include_self=True)
        
        total = 0
        
        for node in tree:
            total += SubjectControlProperty.objects.filter(control_property_value = node).count()
            
        return total
        
    def get_siblings_same_type(self):
        """ Returns all the siblings of the current node which share the same "type" value """
        
        return self.get_siblings().filter(type = self.type)

    def get_children_same_type(self):
        """ Returns all the children of the current node which share the same "type" value """
        
        return self.get_children().filter(type = self.type)

class ResultProperty(models.Model):
    """ Descriptive properties used for displaying search results """

    display_field = models.CharField(max_length = 40)
    field_type = models.ForeignKey(DescriptiveProperty, blank = True, null = True)
    
    class Meta:
        verbose_name = 'Result Property'
        verbose_name_plural = 'Result Properties'
        ordering = ['display_field']
        
    def human_title(self):
        types = {'loc': 'Context', 'po': 'Person/Organization', 'subj': 'Object', 'med': 'Media'}
        fields = {'desc': 'Descriptor', 'title': 'Title'}
        
        if self.display_field:
            m = re.match(r"([a-z]+)_([a-z]+)(\d)", self.display_field)
        
            if m:
                return types[m.group(1)] + ' ' + fields[m.group(2)] + ' ' + m.group(3)
        return ''
    human_title.admin_order_field = 'display_field'

    def __unicode__(self):
        if self.field_type:
            return self.field_type.property
        else:
            return "None"            
        
""" ARCHAEOLOGICAL ENTITY MODELS """
       
class Subject(models.Model):
    """ Primary subjects of observation for a project, usually artifacts. """ 

    title = models.CharField(max_length = 100, default = '(none)')
    notes = models.TextField(blank = True, help_text = "This field is used INTERALLY ONLY for general notes on this object meant for project team members only.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)
    
    # the following fields are set using the Result Properties values
    title1 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('subj_title1'))
    title2 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('subj_title2'))
    title3 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('subj_title3'))
    desc1 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('subj_desc1'))
    desc2 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('subj_desc2'))
    desc3 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('subj_desc3')) 
    
    def __unicode__(self):
        return self.title
        
    def get_type(self):
        """ Used in templates in lieu of isInstance to tell which type of object is being referenced. """
        return 'subject';
        
    def get_absolute_url(self):
        return reverse('subjectdetail', args=[str(self.id)])
        
    def get_full_absolute_url(self):
        domain = settings.ALLOWED_HOSTS[0]
        
        if domain.startswith('.'):
            domain = domain[1:]

        return 'http://%s%s' % (domain, self.get_absolute_url())        
        
    def save(self, *args, **kwargs):
        """ Auto fills the main title field. If object does not have a value for title1, title2, or title3,
        it draws from any property, preferencing the property based on the Descriptive Property's order """
        
        # set the result properties
        result_props = get_display_fields(self, 'subj')
        self.title1 = result_props['title1']
        self.title2 = result_props['title2']
        self.title3 = result_props['title3']
        self.desc1 = result_props['desc1']
        self.desc2 = result_props['desc2']
        self.desc3 = result_props['desc3']
        
        # set the title
        self.title = get_new_title(self, 'subject')
        
        super(Subject, self).save(*args, **kwargs)
        
    def get_thumbnail(self):
        """ Returns thumbnail for this object, or if none is set, returns stock "no image". """
        
        resource_uri = GlobalVars.objects.get(pk=11)
        no_img = GlobalVars.objects.get(pk=12).val
        thumbs = SubjectFile.objects.filter(subject = self, thumbnail = True)
        if thumbs:
            return resource_uri.val + str(thumbs[0].rsid)
        else:
            return no_img
    get_thumbnail.short_description = 'Object'
    get_thumbnail.allow_tags = True
                
    class Meta:
        verbose_name = 'Object'    
        verbose_name_plural = 'Objects'
        ordering = ['title1']
        
class Location(MPTTModel):
    """ Geographic subjects of observation for a project, usually locations or contexts. """
    
    title = models.CharField(max_length = 100, default = '(none)')
    notes = models.TextField(blank = True, help_text = "This field is used INTERALLY ONLY for general notes on this location meant for project team members only.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)
    type = models.ForeignKey(ObjectType, blank = True, null = True)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')
    
    # the following fields are set using the Result Properties values
    title1 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('loc_title1'))
    title2 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('loc_title2'))
    title3 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('loc_title3'))
    desc1 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('loc_desc1'))
    desc2 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('loc_desc2'))
    desc3 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('loc_desc3'))     
    
    def __unicode__(self):
        return self.title
        
    def get_type(self):
        """ Used in templates in lieu of isInstance to tell which type of object is being referenced. """
        return 'location';

    def get_absolute_url(self):
        return reverse('locationdetail', args=[str(self.id)])

    def get_full_absolute_url(self):
        domain = settings.ALLOWED_HOSTS[0]
        
        if domain.startswith('.'):
            domain = domain[1:]

        return 'http://%s%s' % (domain, self.get_absolute_url())

    def save(self, *args, **kwargs):
        """ Auto fills the main title field. If l does not have a value for title1, title2, or title3,
        it draws from any property, preferencing the property based on the Descriptive Property's order """
        
        # set the result properties
        result_props = get_display_fields(self, 'loc')
        self.title1 = result_props['title1']
        self.title2 = result_props['title2']
        self.title3 = result_props['title3']
        self.desc1 = result_props['desc1']
        self.desc2 = result_props['desc2']
        self.desc3 = result_props['desc3']
        
        # set the title
        self.title = get_new_title(self, 'location')
        
        super(Location, self).save(*args, **kwargs)

    def get_thumbnail(self):
        """ Returns thumbnail for this object, or if none is set, returns stock "no image". """
        
        resource_uri = GlobalVars.objects.get(pk=11)
        no_img = GlobalVars.objects.get(pk=12).val
        thumbs = LocationFile.objects.filter(location = self, thumbnail = True)
        if thumbs:
            return resource_uri.val + str(thumbs[0].rsid)
        else:
            return no_img
    get_thumbnail.short_description = 'Location'
    get_thumbnail.allow_tags = True        
        
    def ancestors(self):
        ancients = self.get_ancestors(include_self=False)
        ancs = ''
        for ancient in ancients:
            ancs = ancs + ancient.title + '>>'
        return ancs
        
    def next(self):
        try:
            return Location.objects.get(pk=self.pk+1)
        except:
            return None
            
    def previous(self):
        try:
            return Location.objects.get(pk=self.pk-1)
        except:
            return None

    class Meta:
        verbose_name = 'Location'    
        verbose_name_plural = 'Locations'

    class MPTTMeta:
        order_insertion_by = ['title']
       
class Media(models.Model):
    """ Documentation for project. """
    
    title = models.CharField(max_length = 100, default = '(none)')
    notes = models.TextField(blank = True, help_text = "This field is used INTERALLY ONLY for general notes on this media item meant for project team members only.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)
    type = models.ForeignKey(MediaType, blank = True, null = True, related_name = "MIME_type")
    bib_type = models.ForeignKey(MediaType, blank = True, null = True, related_name = "citation_type")
    
    # the following fields are set using the Result Properties values
    title1 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('med_title1'))
    title2 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('med_title2'))
    title3 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('med_title3'))
    desc1 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('med_desc1'))
    desc2 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('med_desc2'))
    desc3 = models.TextField(blank = True, default = '(none)', verbose_name = get_display_field_header('med_desc3'))
    
    def __unicode__(self):
        return self.title
        
    def get_type(self):
        """ Used in templates in lieu of isInstance to tell which type of object is being referenced. """
        return 'media';         
        
    def get_properties(self):
        return self.mediaproperty_set.all()

    def get_absolute_url(self):
        return reverse('mediadetail', args=[str(self.id)])
        
    def get_full_absolute_url(self):
        domain = settings.ALLOWED_HOSTS[0]
        
        if domain.startswith('.'):
            domain = domain[1:]

        return 'http://%s%s' % (domain, self.get_absolute_url())        
        
    def save(self, *args, **kwargs):
        """ Auto fills the main title field. If object does not have a value for title1, title2, or title3,
        it draws from any property, preferencing the property based on the Descriptive Property's order """
        
        # set the result properties
        result_props = get_display_fields(self, 'med')
        self.title1 = result_props['title1']
        self.title2 = result_props['title2']
        self.title3 = result_props['title3']
        self.desc1 = result_props['desc1']
        self.desc2 = result_props['desc2']
        self.desc3 = result_props['desc3']
        
        # set the title
        self.title = get_new_title(self, 'media')
        
        super(Media, self).save(*args, **kwargs)
        
    def get_thumbnail(self):
        """ Returns thumbnail for this object, or if none is set, returns stock "no image". """
        
        resource_uri = GlobalVars.objects.get(pk=11)
        no_img = GlobalVars.objects.get(pk=12).val
        thumbs = MediaFile.objects.filter(media = self, thumbnail = True)
        if thumbs:
            return resource_uri.val + str(thumbs[0].rsid)
        else:
            return no_img
    get_thumbnail.short_description = 'Media'
    get_thumbnail.allow_tags = True

    class Meta:
        verbose_name = 'media'
        verbose_name_plural = 'media'
        ordering = ['title1']
        
""" DESCRIPTIVE PROPERTIES OF ARCHAEOLOGICAL ENTITY MODELS """        
        
class SubjectProperty(models.Model):
    """ Free-Form Properties of Subjects """

    subject = models.ForeignKey(Subject)
    property = models.ForeignKey(DescriptiveProperty)
    property_value = models.TextField()
    notes = models.TextField(blank = True, help_text = "This note will appear on the public site as a footnote. Please use this field for citations, notes on certainty, and attribution of this piece of information.", verbose_name = "Footnote Citation")
    inline_notes = models.TextField(blank = True, help_text = "This note will appear on the public site in line with the data. Please use this field for citations, notes on certainty, and attribution of this piece of information.", verbose_name = "Inline Citation")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    class Meta:
        verbose_name = 'Free-Form Object Property'    
        verbose_name_plural = 'Free-Form Object Properties'
        ordering = ['property__order']

    def __unicode__(self):
        return self.property.property + ": " + self.property_value
        
    def save(self, *args, **kwargs):
    
        # save the property first so that when the display fields are generated below,
        # it has the new property value
        super(SubjectProperty, self).save(*args, **kwargs)
        
        # this has to be called after every property save so that titles can be regenerated
        self.subject.save()
    
    def delete(self, *args, **kwargs):
        """ Resets all the titles and descriptors in case the deleted property was being used as a title. """
        
        super(SubjectProperty, self).delete(*args, **kwargs)
        
        self.subject.save()
        
class SubjectControlProperty(models.Model):
    """ Controlled Properties of Subjects """

    subject = models.ForeignKey(Subject)
    control_property = models.ForeignKey(DescriptiveProperty)
    control_property_value = models.ForeignKey(ControlField)
    notes = models.TextField(blank = True, help_text = "Please use this field for citations, notes on certainty, and attribution of this piece of information.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    class Meta:
        verbose_name = 'Controlled Object Property'    
        verbose_name_plural = 'Controlled Object Properties'    

    def __unicode__(self):
        return self.control_property.property + ': ' + self.control_property_value.title
        
    def save(self, *args, **kwargs):
    
        # save the property first so that when the display fields are generated below,
        # it has the new property value
        super(SubjectControlProperty, self).save(*args, **kwargs)
        
        # this has to be called after every property save so that titles can be regenerated
        self.subject.save()
    
    def delete(self, *args, **kwargs):
        """ Resets all the titles and descriptors in case the deleted property was being used as a title. """
        
        super(SubjectControlProperty, self).delete(*args, **kwargs)
        
        self.subject.save()
        
class LocationProperty(models.Model):
    """ Free-Form Properties of Locations """

    location = models.ForeignKey(Location)
    property = models.ForeignKey(DescriptiveProperty)
    property_value = models.TextField()
    notes = models.TextField(blank = True, help_text = "This note will appear on the public site as a footnote. Please use this field for citations, notes on certainty, and attribution of this piece of information.", verbose_name = "Footnote Citation")
    inline_notes = models.TextField(blank = True, help_text = "This note will appear on the public site in line with the data. Please use this field for citations, notes on certainty, and attribution of this piece of information.", verbose_name = "Inline Citation")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    class Meta:
        verbose_name = 'Free-Form Location Property'    
        verbose_name_plural = 'Free-Form Location Properties'
        ordering = ['property__order']   

    def __unicode__(self):
        return self.property.property + ": " + self.property_value

    def save(self, *args, **kwargs):
    
        # save the property first so that when the display fields are generated below,
        # it has the new property value
        super(LocationProperty, self).save(*args, **kwargs)
        
        # this has to be called after every property save so that titles can be regenerated
        self.location.save()
    
    def delete(self, *args, **kwargs):
        """ Resets all the titles and descriptors in case the deleted property was being used as a title. """
        
        super(LocationProperty, self).delete(*args, **kwargs)
        
        self.location.save()        

class LocationControlProperty(models.Model):
    """ Controlled Properties of Locations """

    location = models.ForeignKey(Location)
    control_property = models.ForeignKey(DescriptiveProperty)
    control_property_value = models.ForeignKey(ControlField)
    notes = models.TextField(blank = True, help_text = "Please use this field for citations, notes on certainty, and attribution of this piece of information.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    class Meta:
        verbose_name = 'Controlled Location Property'    
        verbose_name_plural = 'Controlled Location Properties'    

    def __unicode__(self):
        return self.control_property.property + ': ' + self.control_property_value.title
        
    def save(self, *args, **kwargs):
    
        # save the property first so that when the display fields are generated below,
        # it has the new property value
        super(LocationControlProperty, self).save(*args, **kwargs)
        
        # this has to be called after every property save so that titles can be regenerated
        self.location.save()
    
    def delete(self, *args, **kwargs):
        """ Resets all the titles and descriptors in case the deleted property was being used as a title. """
        
        super(LocationControlProperty, self).delete(*args, **kwargs)
        
        self.location.save()        

""" ENTITY MODEL FILE RELATIONS """

class SubjectFile(models.Model):
    subject = models.ForeignKey(Subject)
    rsid = models.IntegerField()
    thumbnail = models.BooleanField(default=False)
    filetype = models.ForeignKey(MediaType)
    collection = models.ForeignKey(Collection, blank = True, null = True)
    
class LocationFile(models.Model):
    location = models.ForeignKey(Location)
    rsid = models.IntegerField()
    thumbnail = models.BooleanField(default=False)
    filetype = models.ForeignKey(MediaType)
    collection = models.ForeignKey(Collection, blank = True, null = True)

""" SITE SETTINGS ETC MODELS """

class AdminPost(models.Model):
    """ Admin forum posts. """

    title = models.CharField(max_length=255)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=True)
    author = models.ForeignKey(User)
    subject = models.ManyToManyField(Subject, blank = True, verbose_name="attached objects")
        
    class Meta:
        ordering = ['-created']
        verbose_name = 'Admin Forum Post'
        verbose_name_plural = 'Admin Forum Posts'          
            
    def __unicode__(self):
        return self.title
        
class AdminComment(models.Model):
    """ Comments on admin forum posts """
    
    post = models.ForeignKey(AdminPost)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=True)
    author = models.ForeignKey(User)
        
    class Meta:
        ordering = ['-created']
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'          
            
    def __unicode__(self):
        return 'Comment on ' + self.post.title + ' by ' + self.author.username

"""Variables used by pages throughout the site"""
class GlobalVars(models.Model):
    variable = models.CharField(max_length = 200)
    val = models.TextField(verbose_name='Value')
    human_title = models.CharField(max_length = 200, verbose_name='Setting')
	
    class Meta:
        verbose_name = 'Site Setting'
        verbose_name_plural = 'Site Settings'
    
    def __unicode__(self):
        return self.human_title
        
class SiteContent(models.Model):
    variable = models.CharField(max_length = 200)
    val = models.TextField(verbose_name='Value')
    human_title = models.CharField(max_length = 200, verbose_name='Content Text')
	
    class Meta:
        verbose_name = 'Site Content'
        verbose_name_plural = 'Site Content'
    
    def __unicode__(self):
        return self.human_title        
        
"""Featured images for home page"""
# consider removing
class FeaturedImgs(models.Model):
    uri = models.URLField()
    description = models.CharField(max_length = 200)

    class Meta:
        verbose_name = 'Featured Image'
        verbose_name_plural = 'Featured Images'
        
    def __unicode__(self):
        return self.description
        
"""Types of relationships between objects"""
class Relations(models.Model):
    relation = models.CharField(max_length = 60)
    notes = models.TextField(blank = True)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)    

    def __unicode__(self):
        return self.relation
        
    class Meta:
        verbose_name_plural = 'relations'

"""Descriptive Properties of Media Files"""        
class MediaProperty(models.Model):
    media = models.ForeignKey(Media)
    property = models.ForeignKey(DescriptiveProperty)
    property_value = models.TextField()
    notes = models.TextField(blank = True, help_text = "Please use this field for citations, notes on certainty, and attribution of this piece of information.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)   

    def __unicode__(self):
        return self.property_value
        
    def get_properties(self):
        return self.media.get_properties()

    class Meta:
        verbose_name = 'Media Property'
        verbose_name_plural = 'Media Properties' 
                        
"""The people and institutions that participated in a project"""        
class PersonOrg(models.Model):
    title = models.CharField(max_length = 100)
    notes = models.TextField(blank = True, help_text = "This field is used INTERALLY ONLY for general notes on this person/organization meant for project team members only.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)
    
    class Meta:
        verbose_name = 'Person/Organization'
        verbose_name_plural = 'People/Organizations'    
    
    def __unicode__(self):
        return self.title
        
    def get_properties(self):
        return self.personorgproperty_set.all()
       
    def get_type(self):
        return 'person_org';       

"""Descriptive Properties of People and Organizations"""        
class PersonOrgProperty(models.Model):
    person_org = models.ForeignKey(PersonOrg)
    property = models.ForeignKey(DescriptiveProperty)
    property_value = models.TextField()
    notes = models.TextField(blank = True, help_text = "Please use this field for citations, notes on certainty, and attribution of this piece of information.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)

    class Meta:
        verbose_name = 'PersonOrg Property'
        verbose_name_plural = 'PersonOrg Properties'    

    def __unicode__(self):
        return self.property_value
        
    def get_properties(self):
        return self.person_org.get_properties()
                
"""Related media and subjects"""
class MediaSubjectRelations(models.Model):
    media = models.ForeignKey(Media)
    subject = models.ForeignKey(Subject)
    relation_type = models.ForeignKey(Relations)
    notes = models.TextField(blank = True, help_text = "Please use this field for specific page or plate information, etc, referring to where this object is mentioned in this media item.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    def __unicode__(self):
        return self.media.title + ":" + self.subject.title
        
    class Meta:
        verbose_name = 'Media-Object Relation'
        verbose_name_plural = 'Media-Object Relations'
        
"""Related media and people"""
class MediaPersonOrgRelations(models.Model):
    media = models.ForeignKey(Media)
    person_org = models.ForeignKey(PersonOrg)
    relation_type = models.ForeignKey(Relations)
    notes = models.TextField(blank = True, help_text = "Please use this field for specific page or plate information, etc, referring to where this Person/Organization is mentioned in this media item.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)

    def __unicode__(self):
        return self.media.title + ":" + self.person_org.title

    class Meta:
        verbose_name = 'Media-Person/Organization Relation'
        verbose_name_plural = 'Media-Person/Organization Relations'        
        
"""Related subjects"""
class SubjectSubjectRelations(models.Model):
    subject1 = models.ForeignKey(Subject, related_name='subject1')
    subject2 = models.ForeignKey(Subject, related_name='subject2')
    relation_type = models.ForeignKey(Relations)
    notes = models.TextField(blank = True)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)

    def __unicode__(self):
        return self.subject1.title + ":" + self.subject2.title 
        
    class Meta:
        verbose_name = 'Object-Object Relation'
        verbose_name_plural = 'Object-Object Relations'    
        
"""Related media"""
class MediaMediaRelations(models.Model):
    media1 = models.ForeignKey(Media, related_name='media1')
    media2 = models.ForeignKey(Media, related_name='media2')
    relation_type = models.ForeignKey(Relations)
    notes = models.TextField(blank = True)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)

    def __unicode__(self):
        return self.media1.title + ":" + self.media2.title

"""Related persons and organizations"""
class PersonOrgPersonOrgRelations(models.Model):
    person_org1 = models.ForeignKey(PersonOrg, related_name='person_org1')
    person_org2 = models.ForeignKey(PersonOrg, related_name='person_org2')
    relation_type = models.ForeignKey(Relations)
    notes = models.TextField(blank = True)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)

    def __unicode__(self):
        return self.person_org1.title + ":" + self.person_org2.title 
        
"""Object Status"""
class Status(models.Model):
    status = models.CharField(max_length = 60, blank = True)
    notes = models.TextField(blank = True)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    def __unicode__(self):
        return self.status 
    
    class Meta:
        verbose_name = 'Status'    
        verbose_name_plural = 'Status'        
        
class LinkedDataSource(models.Model):
    title = models.CharField(max_length = 60, blank = True)
    link = models.URLField(blank = True)

    def __unicode__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Linked Data Source'
        verbose_name_plural = 'Linked Data Sources'        

class ControlFieldLinkedData(models.Model):
    control_field = models.ForeignKey(ControlField)
    source = models.ForeignKey(LinkedDataSource)
    link = models.URLField(blank = True)
    
    class Meta:
        verbose_name = 'Linked Data'
        verbose_name_plural = 'Linked Data'
        
class DescPropertyLinkedData(models.Model):
    desc_prop = models.ForeignKey(DescriptiveProperty)
    source = models.ForeignKey(LinkedDataSource)
    link = models.URLField(blank = True)
    
    class Meta:
        verbose_name = 'Linked Data'
        verbose_name_plural = 'Linked Data'        

class SubjectLinkedData(models.Model):
    subject = models.ForeignKey(Subject)
    source = models.ForeignKey(LinkedDataSource)
    link = models.URLField(blank = True)
    
    class Meta:
        verbose_name = 'Linked Object Data'
        verbose_name_plural = 'Linked Object Data' 

class MediaLinkedData(models.Model):
    media = models.ForeignKey(Media)
    source = models.ForeignKey(LinkedDataSource)
    link = models.URLField(blank = True)
    
    class Meta:
        verbose_name = 'Linked Media Data'
        verbose_name_plural = 'Linked Media Data'  

class PersonOrgLinkedData(models.Model):
    personorg = models.ForeignKey(PersonOrg)
    source = models.ForeignKey(LinkedDataSource)
    link = models.URLField(blank = True)
    
    class Meta:
        verbose_name = 'Linked Person/Organization Data'
        verbose_name_plural = 'Linked Person/Organization Data'

class PublicationManager(models.Manager):
    def get_query_set(self):
        return super(PublicationManager, self).get_query_set().filter(relation_type=2)
        
class Publication(MediaSubjectRelations):
    objects = PublicationManager()
    
    class Meta:
        proxy = True
        
class FileManager(models.Manager):
    def get_query_set(self):
        return super(FileManager, self).get_query_set().filter(Q(relation_type=3))
        
class File(MediaSubjectRelations):
    objects = FileManager()
    
    def get_thumbnail(self):
        rs_ids = MediaProperty.objects.filter(media = self.media_id, property__property = 'Resource Space ID')
        if rs_ids:
            rs_id = rs_ids[0].property_value
            url = 'http://ur.iaas.upenn.edu/resourcespace/plugins/ref_urls/file.php?ref=' + rs_id
            return u'<a href="{0}" target="_blank"><img src="{0}&size=thm" /></a>'.format(url)        
        else:
            return u'<img src="http://ur.iaas.upenn.edu/static/img/no_img.jpg" />'            
    get_thumbnail.short_description = 'Thumbnail'
    get_thumbnail.allow_tags = True
    
    class Meta:
        proxy = True
        
class LocationSubjectRelations(models.Model):
    location = models.ForeignKey(Location)
    subject = models.ForeignKey(Subject)
    relation_type = models.ForeignKey(Relations)
    notes = models.TextField(blank = True, help_text = "Please use this field for more specific information about where this object was found within this context, as well as citations, notes on certainty, and attribution of this piece of information.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    def __unicode__(self):
        return self.location.title + ":" + self.subject.title
        
    class Meta:
        verbose_name = 'Location-Object Relation'
        verbose_name_plural = 'Location-Object Relations'        
        
class Post(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=True)
    author = models.ForeignKey(User)
        
    class Meta:
        ordering = ['-created']
        verbose_name = 'Public Blog Post'
        verbose_name_plural = 'Public Blog Posts'          
            
    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('base.views.post', args=[self.slug])
        
class MediaLocationRelations(models.Model):
    media = models.ForeignKey(Media)
    location = models.ForeignKey(Location)
    relation_type = models.ForeignKey(Relations)
    notes = models.TextField(blank = True, help_text = "Please use this field for specific page or plate information, etc, referring to where this location is mentioned in this media item.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    def __unicode__(self):
        return self.media.title + ":" + self.location.title
        
    class Meta:
        verbose_name = 'Media-Location Relation'
        verbose_name_plural = 'Media-Location Relations'
        
class SubjectCollection(models.Model):
    subject = models.ForeignKey(Subject)
    collection = models.ForeignKey(Collection)
    notes = models.TextField(blank = True)
    order = models.IntegerField(blank = True, default = 0)
    
    def __unicode__(self):
        return self.subject.title + " [Collection: " + self.collection.title + "]"
        
    class Meta:
        verbose_name = 'Collection Item (Object)'
        verbose_name_plural = 'Collection Items (Object)'
        
class LocationCollection(models.Model):
    location = models.ForeignKey(Location)
    collection = models.ForeignKey(Collection)
    notes = models.TextField(blank = True)
    order = models.IntegerField(blank = True, default = 0)
    
    def __unicode__(self):
        return self.location.title + " [Collection: " + self.collection.title + "]"
        
    class Meta:
        verbose_name = 'Collection Item (Location)'
        verbose_name_plural = 'Collection Items (Location)'        
        
class MediaCollection(models.Model):
    media = models.ForeignKey(Media)
    collection = models.ForeignKey(Collection)
    notes = models.TextField(blank = True)
    order = models.IntegerField(blank = True, default = 0)
    
    def __unicode__(self):
        return self.media.title + " [Collection: " + self.collection.title + "]"
        
    class Meta:
        verbose_name = 'Collection Item (Media)'
        verbose_name_plural = 'Collection Items (Media)'        
        
class FileUpload(models.Model):
    title = models.CharField(max_length = 255)
    file = FilerImageField(blank = True)
    attribution = models.TextField(blank = True)
    
class LegrainNoteCards(models.Model):
    media = models.ForeignKey(Media)
    field_number = models.TextField(blank = True)
    context = models.TextField(blank = True)
    catalogue_number = models.TextField(blank = True)
    museum_number = models.TextField(blank = True)
    field_photo_number = models.TextField(blank = True)
    measurements = models.TextField(blank = True)
    transcription = models.TextField(blank = True)
    category = models.TextField(blank = True)
    photo = models.BooleanField(default = False)
    drawing = models.BooleanField(default = False)
    done = models.BooleanField(default = False)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)
    
    class Meta:
        verbose_name = 'Legrain NoteCard Form'
        verbose_name_plural = 'Legrain NoteCard Form'     
    
class LegrainImages(models.Model):

    class Meta:
        verbose_name = 'Legrain Image Form'
        verbose_name_plural = 'Legrain Image Form'   

    UR = 'ur'
    TRAVEL = 'travel'
    CAT = (
        (UR, 'Ur'),
        (TRAVEL, 'Travel'),
    )
    
    LS = 'ls'
    PEOPLE = 'people'
    ARCH = 'arch'
    EX = 'ex'
    ILL = 'ill'
    CITY = 'city'
    SUB_CAT = (
        (LS, 'Landscape'),
        (PEOPLE, 'People'),
        (ARCH, 'Archaeology'),
        (EX, 'Excavation'),
        (ILL, 'Illustration'),
        (CITY, 'City-scape'),
    )
    
    media = models.ForeignKey(Media)
    image_category = models.CharField(max_length=6, choices=CAT, default = TRAVEL, blank = True)
    image_sub_category = models.CharField(max_length=6, choices=SUB_CAT, default = LS, blank = True)
    image_description = models.TextField(blank = True)
    done = models.BooleanField(default = False)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)    
    
class LegrainImageTags(models.Model):

    class Meta:
        verbose_name = 'Legrain Image Tag'
        verbose_name_plural = 'Legrain Image Tags' 

    media = models.ForeignKey(Media)
    tag = models.ForeignKey(ControlField)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)
    
class LegrainImageManager(models.Manager):
    def get_query_set(self):
        return super(LegrainImageManager, self).get_query_set().filter(mediacollection__collection_id = 3)
        
class LegrainImage(Media):
    objects = LegrainImageManager()
    
    class Meta:
        proxy = True
        verbose_name = 'Legrain Image'
        verbose_name_plural = 'Legrain Images'
        ordering = ['title']
        
class LegrainNotesManager(models.Manager):
    def get_query_set(self):
        return super(LegrainNotesManager, self).get_query_set().filter(mediacollection__collection_id = 4)
        
class LegrainNotes(Media):
    objects = LegrainNotesManager()
    
    class Meta:
        proxy = True
        verbose_name = 'Legrain Note Card'
        verbose_name_plural = 'Legrain Note Cards'
        ordering = ['title']