from haystack import indexes
from base.models import Media, Subject, PersonOrg, Location

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

    def get_model(self):
        return Location