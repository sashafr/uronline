from rest_framework.serializers import ModelSerializer, StringRelatedField, ListSerializer, CharField, HyperlinkedModelSerializer
from base.models import SubjectControlProperty, SubjectProperty, Subject, LocationControlProperty, LocationProperty, Location, MediaControlProperty, MediaProperty, Media, PersonOrgControlProperty, PersonOrgProperty, PersonOrg

class VisibleCPListSerializer(ListSerializer):
    
    def to_representation(self, data):
        data = data.filter(control_property__visible = True)
        return super(VisibleCPListSerializer, self).to_representation(data)
        
class VisibleFFPListSerializer(ListSerializer):
    
    def to_representation(self, data):
        data = data.filter(property__visible = True)
        return super(VisibleFFPListSerializer, self).to_representation(data)        

class SubjectControlPropertySerializer(ModelSerializer):
    property = StringRelatedField(source='control_property')
    value = StringRelatedField(source='control_property_value')
    footnote = CharField(source='notes')
    inline = CharField(source='inline_notes')

    class Meta:
        list_serializer_class = VisibleCPListSerializer
        model = SubjectControlProperty
        fields = ('property', 'value', 'inline', 'footnote')
        
class SubjectPropertySerializer(ModelSerializer):
    prop = StringRelatedField(source='property')
    inline_note = CharField(source='inline_notes')
    footnote = CharField(source='notes')

    class Meta:
        list_serializer_class = VisibleFFPListSerializer
        model = SubjectProperty
        fields = ('prop', 'property_value', 'inline_note', 'footnote')        
        
class SubjectSerializer(HyperlinkedModelSerializer):
    url = CharField(source='get_full_absolute_url', read_only=True)
    control_properties = SubjectControlPropertySerializer(source='subjectcontrolproperty_set', many=True, read_only=True)
    free_form_properties = SubjectPropertySerializer(source='subjectproperty_set', many=True, read_only=True)
    
    class Meta:
        model = Subject
        fields = ('id', 'url', 'title', 'control_properties', 'free_form_properties')
        
class LocationControlPropertySerializer(ModelSerializer):
    property = StringRelatedField(source='control_property')
    value = StringRelatedField(source='control_property_value')
    footnote = CharField(source='notes')
    inline = CharField(source='inline_notes')    

    class Meta:
        list_serializer_class = VisibleCPListSerializer
        model = LocationControlProperty
        fields = ('property', 'value', 'inline', 'footnote')
        
class LocationPropertySerializer(ModelSerializer):
    prop = StringRelatedField(source='property')
    inline_note = CharField(source='inline_notes')
    footnote = CharField(source='notes')

    class Meta:
        list_serializer_class = VisibleFFPListSerializer
        model = LocationProperty
        fields = ('prop', 'property_value', 'inline_note', 'footnote')        
        
class LocationSerializer(HyperlinkedModelSerializer):
    url = CharField(source='get_full_absolute_url', read_only=True)
    control_properties = LocationControlPropertySerializer(source='locationcontrolproperty_set', many=True, read_only=True)
    free_form_properties = LocationPropertySerializer(source='locationproperty_set', many=True, read_only=True)
    
    class Meta:
        model = Location
        fields = ('id', 'url', 'title', 'control_properties', 'free_form_properties')
        
class MediaControlPropertySerializer(ModelSerializer):
    property = StringRelatedField(source='control_property')
    value = StringRelatedField(source='control_property_value')
    footnote = CharField(source='notes')
    inline = CharField(source='inline_notes')    

    class Meta:
        list_serializer_class = VisibleCPListSerializer
        model = MediaControlProperty
        fields = ('property', 'value', 'inline', 'footnote')
        
class MediaPropertySerializer(ModelSerializer):
    prop = StringRelatedField(source='property')
    inline_note = CharField(source='inline_notes')
    footnote = CharField(source='notes')

    class Meta:
        list_serializer_class = VisibleFFPListSerializer
        model = MediaProperty
        fields = ('prop', 'property_value', 'inline_note', 'footnote')        
        
class MediaSerializer(HyperlinkedModelSerializer):
    url = CharField(source='get_full_absolute_url', read_only=True)
    control_properties = MediaControlPropertySerializer(source='mediacontrolproperty_set', many=True, read_only=True)
    free_form_properties = MediaPropertySerializer(source='mediaproperty_set', many=True, read_only=True)
    
    class Meta:
        model = Media
        fields = ('id', 'url', 'title', 'control_properties', 'free_form_properties')

class PersonOrgControlPropertySerializer(ModelSerializer):
    property = StringRelatedField(source='control_property')
    value = StringRelatedField(source='control_property_value')
    footnote = CharField(source='notes')
    inline = CharField(source='inline_notes')    

    class Meta:
        list_serializer_class = VisibleCPListSerializer
        model = PersonOrgControlProperty
        fields = ('property', 'value', 'inline', 'footnote')
        
class PersonOrgPropertySerializer(ModelSerializer):
    prop = StringRelatedField(source='property')
    inline_note = CharField(source='inline_notes')
    footnote = CharField(source='notes')

    class Meta:
        list_serializer_class = VisibleFFPListSerializer
        model = PersonOrgProperty
        fields = ('prop', 'property_value', 'inline_note', 'footnote')        
        
class PersonOrgSerializer(HyperlinkedModelSerializer):
    url = CharField(source='get_full_absolute_url', read_only=True)
    control_properties = PersonOrgControlPropertySerializer(source='personorgcontrolproperty_set', many=True, read_only=True)
    free_form_properties = PersonOrgPropertySerializer(source='personorgproperty_set', many=True, read_only=True)
    
    class Meta:
        model = PersonOrg
        fields = ('id', 'url', 'title', 'control_properties', 'free_form_properties')        
        
""" ADMIN """

class SubjectControlPropertyAdminSerializer(ModelSerializer):
    property = StringRelatedField(source='control_property')
    value = StringRelatedField(source='control_property_value')
    footnote = CharField(source='notes')
    inline = CharField(source='inline_notes')

    class Meta:
        model = SubjectControlProperty
        fields = ('property', 'value', 'inline', 'footnote')
        
class SubjectPropertyAdminSerializer(ModelSerializer):
    prop = StringRelatedField(source='property')
    inline_note = CharField(source='inline_notes')
    footnote = CharField(source='notes')

    class Meta:
        model = SubjectProperty
        fields = ('prop', 'property_value', 'inline_note', 'footnote')        
        
class SubjectAdminSerializer(HyperlinkedModelSerializer):
    url = CharField(source='get_full_absolute_url', read_only=True)
    control_properties = SubjectControlPropertyAdminSerializer(source='subjectcontrolproperty_set', many=True, read_only=True)
    free_form_properties = SubjectPropertyAdminSerializer(source='subjectproperty_set', many=True, read_only=True)
    
    class Meta:
        model = Subject
        fields = ('id', 'url', 'title', 'control_properties', 'free_form_properties')
        
class LocationControlPropertyAdminSerializer(ModelSerializer):
    property = StringRelatedField(source='control_property')
    value = StringRelatedField(source='control_property_value')
    footnote = CharField(source='notes')
    inline = CharField(source='inline_notes')    

    class Meta:
        model = LocationControlProperty
        fields = ('property', 'value', 'inline', 'footnote')
        
class LocationPropertyAdminSerializer(ModelSerializer):
    prop = StringRelatedField(source='property')
    inline_note = CharField(source='inline_notes')
    footnote = CharField(source='notes')

    class Meta:
        model = LocationProperty
        fields = ('prop', 'property_value', 'inline_note', 'footnote')        
        
class LocationAdminSerializer(HyperlinkedModelSerializer):
    url = CharField(source='get_full_absolute_url', read_only=True)
    control_properties = LocationControlPropertyAdminSerializer(source='locationcontrolproperty_set', many=True, read_only=True)
    free_form_properties = LocationPropertyAdminSerializer(source='locationproperty_set', many=True, read_only=True)
    
    class Meta:
        model = Location
        fields = ('id', 'url', 'title', 'control_properties', 'free_form_properties')
        
class MediaControlPropertyAdminSerializer(ModelSerializer):
    property = StringRelatedField(source='control_property')
    value = StringRelatedField(source='control_property_value')
    footnote = CharField(source='notes')
    inline = CharField(source='inline_notes')    

    class Meta:
        model = MediaControlProperty
        fields = ('property', 'value', 'inline', 'footnote')
        
class MediaPropertyAdminSerializer(ModelSerializer):
    prop = StringRelatedField(source='property')
    inline_note = CharField(source='inline_notes')
    footnote = CharField(source='notes')

    class Meta:
        model = MediaProperty
        fields = ('prop', 'property_value', 'inline_note', 'footnote')        
        
class MediaAdminSerializer(HyperlinkedModelSerializer):
    url = CharField(source='get_full_absolute_url', read_only=True)
    control_properties = MediaControlPropertyAdminSerializer(source='mediacontrolproperty_set', many=True, read_only=True)
    free_form_properties = MediaPropertyAdminSerializer(source='mediaproperty_set', many=True, read_only=True)
    
    class Meta:
        model = Media
        fields = ('id', 'url', 'title', 'control_properties', 'free_form_properties')

class PersonOrgControlPropertyAdminSerializer(ModelSerializer):
    property = StringRelatedField(source='control_property')
    value = StringRelatedField(source='control_property_value')
    footnote = CharField(source='notes')
    inline = CharField(source='inline_notes')    

    class Meta:
        model = PersonOrgControlProperty
        fields = ('property', 'value', 'inline', 'footnote')
        
class PersonOrgPropertyAdminSerializer(ModelSerializer):
    prop = StringRelatedField(source='property')
    inline_note = CharField(source='inline_notes')
    footnote = CharField(source='notes')

    class Meta:
        model = PersonOrgProperty
        fields = ('prop', 'property_value', 'inline_note', 'footnote')        
        
class PersonOrgAdminSerializer(HyperlinkedModelSerializer):
    url = CharField(source='get_full_absolute_url', read_only=True)
    control_properties = PersonOrgControlPropertyAdminSerializer(source='personorgcontrolproperty_set', many=True, read_only=True)
    free_form_properties = PersonOrgPropertyAdminSerializer(source='personorgproperty_set', many=True, read_only=True)
    
    class Meta:
        model = PersonOrg
        fields = ('id', 'url', 'title', 'control_properties', 'free_form_properties')        