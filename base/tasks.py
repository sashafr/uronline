from __future__ import absolute_import
from datetime import datetime, timedelta
from celery import shared_task
import urllib2
from base.models import SubjectProperty, Subject

@shared_task
def update():
    response = urllib2.urlopen('http://localhost:8983/solr/subjects/dataimport?command=full-import').read()
    print response
    
@shared_task
def precomp_object_fields():
    time_threshold = datetime.now() - timedelta(hours=2)
    updated_subjects = Subject.objects.filter(modified__gt=time_threshold)