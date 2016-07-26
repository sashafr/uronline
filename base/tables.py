import django_tables2 as tables
from django_tables2.utils import A 
from base.models import Subject, Location, Media, PersonOrg, ResultProperty
from django.utils.safestring import mark_safe

class ThumbColumn(tables.Column):

    def render(self, value):
        return mark_safe('<img src="' + value + '" />')

class SubjectTable(tables.Table):
    get_thumbnail = ThumbColumn(verbose_name = "Object", orderable = False)
    title1 = tables.LinkColumn('subjectdetail', args=[A('pk')])

    class Meta:
    
        visible_fields = ("get_thumbnail", )
    
        # make sure all display columns are set to publically visible
        for x in range (1, 4):
            title_prop = ResultProperty.objects.filter(display_field = 'subj_title' + str(x))
            if title_prop[0].field_type and title_prop[0].field_type.visible:
                title_str = 'title' + str(x)
                visible_fields = visible_fields + (title_str, )
                
        for x in range (1, 4):
            desc_prop = ResultProperty.objects.filter(display_field = 'subj_desc' + str(x))
            if desc_prop[0].field_type and desc_prop[0].field_type.visible:
                desc_str = 'desc' + str(x)
                visible_fields = visible_fields + (desc_str, )
                
        model = Subject
        attrs = {"class": "paleblue"}
        fields = visible_fields
        
class LocationTable(tables.Table):
    get_thumbnail = ThumbColumn(verbose_name = "Location", orderable = False)
    title1 = tables.LinkColumn('locationdetail', args=[A('pk')])

    class Meta:
    
        visible_fields = ("get_thumbnail", )
    
        # make sure all display columns are set to publically visible
        for x in range (1, 4):
            title_prop = ResultProperty.objects.filter(display_field = 'loc_title' + str(x))
            if title_prop[0].field_type and title_prop[0].field_type.visible:
                title_str = 'title' + str(x)
                visible_fields = visible_fields + (title_str, )
                
        for x in range (1, 4):
            desc_prop = ResultProperty.objects.filter(display_field = 'loc_desc' + str(x))
            if desc_prop[0].field_type and desc_prop[0].field_type.visible:
                desc_str = 'desc' + str(x)
                visible_fields = visible_fields + (desc_str, )
                
        model = Location
        attrs = {"class": "paleblue"}
        fields = visible_fields
        
class MediaTable(tables.Table):
    get_thumbnail = ThumbColumn(verbose_name = "Media", orderable = False)
    title1 = tables.LinkColumn('mediadetail', args=[A('pk')])

    class Meta:
    
        visible_fields = ("get_thumbnail", )
    
        # make sure all display columns are set to publically visible
        for x in range (1, 4):
            title_prop = ResultProperty.objects.filter(display_field = 'med_title' + str(x))
            if title_prop[0].field_type and title_prop[0].field_type.visible:
                title_str = 'title' + str(x)
                visible_fields = visible_fields + (title_str, )
                
        for x in range (1, 4):
            desc_prop = ResultProperty.objects.filter(display_field = 'med_desc' + str(x))
            if desc_prop[0].field_type and desc_prop[0].field_type.visible:
                desc_str = 'desc' + str(x)
                visible_fields = visible_fields + (desc_str, )
                
        model = Media
        attrs = {"class": "paleblue"}
        fields = visible_fields

class PersonOrgTable(tables.Table):
    get_thumbnail = ThumbColumn(verbose_name = "People", orderable = False)
    title1 = tables.LinkColumn('personorgdetail', args=[A('pk')])

    class Meta:
    
        visible_fields = ("get_thumbnail", )
    
        # make sure all display columns are set to publically visible
        for x in range (1, 4):
            title_prop = ResultProperty.objects.filter(display_field = 'po_title' + str(x))
            if title_prop[0].field_type and title_prop[0].field_type.visible:
                title_str = 'title' + str(x)
                visible_fields = visible_fields + (title_str, )
                
        for x in range (1, 4):
            desc_prop = ResultProperty.objects.filter(display_field = 'po_desc' + str(x))
            if desc_prop[0].field_type and desc_prop[0].field_type.visible:
                desc_str = 'desc' + str(x)
                visible_fields = visible_fields + (desc_str, )
                
        model = PersonOrg
        attrs = {"class": "paleblue"}
        fields = visible_fields 