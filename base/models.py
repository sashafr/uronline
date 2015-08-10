from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from mptt.models import MPTTModel, TreeForeignKey
from django.core.urlresolvers import reverse
import re
from filer.fields.image import FilerImageField
from filer.fields.file import FilerFileField

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
        (FLOAT, 'Float'),
        (DOUBLE, 'Double'),
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
    
    class MPTTMeta:
        order_insertion_by = ['title']
    
    def __unicode__(self):
        return self.title
        
    class Meta:
        verbose_name = 'Controlled Term'    
        verbose_name_plural = 'Controlled Terms'
        
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
        
""" ARCHAEOLOGICAL ENTITY MODELS """
       
class Subject(models.Model):
    """ Primary subjects of observation for a project, usually objects or locations. """ 

    title = models.CharField(max_length = 100)
    notes = models.TextField(blank = True, help_text = "This field is used INTERALLY ONLY for general notes on this object meant for project team members only.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)
    type = models.ForeignKey(ObjectType, blank = True, null = True)
    
    # the following fields are populated by an auto task and is set using the Result Properties values
    title1 = models.TextField(blank = True)
    title2 = models.TextField(blank = True)
    title3 = models.TextField(blank = True)
    desc1 = models.TextField(blank = True)
    desc2 = models.TextField(blank = True)
    desc3 = models.TextField(blank = True)    
    
    def __unicode__(self):
        return self.title1 + ' | ' + self.title2 + ' | ' + self.title3
        
    def get_type(self):
        return 'subject';
        
    class Meta:
        verbose_name = 'Object'    
        verbose_name_plural = 'Objects' 

""" SITE SETTINGS ETC MODELS """

class AdminPost(models.Model):
    """ Admin forum posts. """

    title = models.CharField(max_length=255)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    published = models.BooleanField(default=True)
    author = models.ForeignKey(User)
    subject = models.ManyToManyField(Subject)
        
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
    
"""Types of Media, such as image/jpeg, text/html, etc"""
# consider removing
class MediaType(models.Model):
    type = models.CharField(max_length = 40)

    def __unicode__(self):
        return self.type

"""Descriptive properties used for displaying search results"""
class ResultProperty(models.Model):
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
        
"""Files that help make up documentation for project"""        
class Media(models.Model):
    title = models.CharField(max_length = 100)
    notes = models.TextField(blank = True, help_text = "This field is used INTERALLY ONLY for general notes on this media item meant for project team members only.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User)
    type = models.ForeignKey(MediaType, blank = True, null = True, related_name = "MIME_type")
    bib_type = models.ForeignKey(MediaType, blank = True, null = True, related_name = "citation_type")

    class Meta:
        verbose_name_plural = 'media'
    
    def __unicode__(self):
        return self.title
        
    def get_properties(self):
        return self.mediaproperty_set.all()
        
    def get_type(self):
        return 'media';

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
        
"""Descriptive Properties of Subjects"""        
class SubjectProperty(models.Model):
    subject = models.ForeignKey(Subject)
    property = models.ForeignKey(DescriptiveProperty)
    property_value = models.TextField()
    notes = models.TextField(blank = True, help_text = "This note will appear on the public site as a footnote. Please use this field for citations, notes on certainty, and attribution of this piece of information.", verbose_name = "Footnote Citation")
    inline_notes = models.TextField(blank = True, help_text = "This note will appear on the public site in line with the data. Please use this field for citations, notes on certainty, and attribution of this piece of information.", verbose_name = "Inline Citation")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    class Meta:
        verbose_name = 'Object Property'    
        verbose_name_plural = 'Object Properties'
        ordering = ['property__order']

    def __unicode__(self):
        return self.property_value
                
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
        
class SubjectControlProperty(models.Model):
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
        return self.control_property_value.title

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

class Location(MPTTModel):
    title = models.CharField(max_length = 100)
    notes = models.TextField(blank = True, help_text = "This field is used INTERALLY ONLY for general notes on this location meant for project team members only.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)
    type = models.ForeignKey(ObjectType, blank = True, null = True)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children')
    
    def __unicode__(self):
        return self.title
     
    class MPTTMeta:
        order_insertion_by = ['title']
        
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
        
class LocationProperty(models.Model):
    location = models.ForeignKey(Location)
    property = models.ForeignKey(DescriptiveProperty)
    property_value = models.TextField()
    notes = models.TextField(blank = True, help_text = "Please use this field for citations, notes on certainty, and attribution of this piece of information.")
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)
    last_mod_by = models.ForeignKey(User, blank = True)

    class Meta:
        verbose_name = 'Location Property'    
        verbose_name_plural = 'Location Properties'    

    def __unicode__(self):
        return self.property_value
        
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

class Collection(models.Model):
    title = models.CharField(max_length=60)
    notes = models.TextField(blank = True)
    created = models.DateTimeField(auto_now = False, auto_now_add = True)
    modified = models.DateTimeField(auto_now = True, auto_now_add = False)    
    owner = models.ForeignKey(User)
    
    def __unicode__(self):
        return self.title
        
class SubjectCollection(models.Model):
    subject = models.ForeignKey(Subject)
    collection = models.ForeignKey(Collection)
    notes = models.TextField(blank = True)
    
    def __unicode__(self):
        return self.subject.title + " [Collection: " + self.collection.title + "]"
        
    class Meta:
        verbose_name = 'Collection Item (Object)'
        verbose_name_plural = 'Collection Items (Object)'
        
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