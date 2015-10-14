from rest_framework.serializers import ModelSerializer, StringRelatedField, ListSerializer, CharField, HyperlinkedModelSerializer
from base.models import SubjectControlProperty, SubjectProperty, Subject

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

    class Meta:
        list_serializer_class = VisibleCPListSerializer
        model = SubjectControlProperty
        fields = ('property', 'value', 'footnote')
        
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