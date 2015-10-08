from rest_framework.serializers import ModelSerializer, StringRelatedField
from base.models import SubjectControlProperty, Subject
        
class SubjectSerializer(ModelSerializer):
    control_property = StringRelatedField(source='subjectcontrolproperty_set', many=True)
    
    class Meta:
        model = Subject
        fields = ('id', 'title', 'control_property')