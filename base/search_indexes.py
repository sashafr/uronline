from haystack import indexes
from base.models import *

class MediaPropertyIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.MultiValueField(document=True)

    def get_model(self):
        return Media

class SubjectPropertyIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.MultiValueField(document=True)

    def get_model(self):
        return Subject
        
class PersonOrgPropertyIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.MultiValueField(document=True)

    def get_model(self):
        return PersonOrg
        
class LocationPropertyIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.MultiValueField(document=True)
    rel_sub = indexes.MultiValueField(null=True)
    rel_med = indexes.MultiValueField(null=True)
    rel_po = indexes.MultiValueField(null=True)
    collection = indexes.MultiValueField(null=True)
    has_image = indexes.BooleanField(null=True)
    
    def prepare_rel_sub(self,obj):
        return [rel.pk for rel in obj.locationsubjectrelations_set.all()]
        
    def prepare_rel_med(self,obj):
        return [rel.pk for rel in obj.medialocationrelations_set.all()]

    def prepare_rel_po(self,obj):
        return [rel.pk for rel in obj.locationpersonorgrelations_set.all()]

    def prepare_collection(self,obj):
        return [rel.pk for rel in obj.locationcollection_set.all()]

    def prepare_has_image(self,obj):
        return obj.has_image()        

    def get_model(self):
        return Location