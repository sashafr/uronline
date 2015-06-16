from __future__ import absolute_import
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task
import urllib2
from base.models import SubjectProperty, Subject, ResultProperty
from base.utils import update_display_fields

@shared_task
def update():
    response = urllib2.urlopen('http://localhost:8983/solr/subjects/dataimport?command=full-import').read()
    print response
    
@shared_task
def precomp_object_fields():
#    updated_subjects = Subject.objects.all()
    time_threshold = timezone.now() - timedelta(hours=2)
    updated_subjects = Subject.objects.filter(modified__gt=time_threshold)
    
    for subject in updated_subjects:
        update_display_fields(subject.id, 'subj')