from __future__ import absolute_import
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task
import urllib2
from base.models import SubjectProperty, Subject, ResultProperty

@shared_task
def update():
    response = urllib2.urlopen('http://localhost:8983/solr/subjects/dataimport?command=full-import').read()
    print response
    
@shared_task
def precomp_object_fields(alltime):
    if alltime:
        updated_subjects = Subject.objects.all()
    else:
        time_threshold = timezone.now() - timedelta(hours=2)
        updated_subjects = Subject.objects.filter(modified__gt=time_threshold)
    
    for subject in updated_subjects:
        object_type = ''
        if subject.type.type == 'subject':
            object_type = 'subj'
        elif subject.type.type == 'location':
            object_type = 'loc'
        update_display_fields(subject.id, object_type)