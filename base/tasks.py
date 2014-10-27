from __future__ import absolute_import

from celery import shared_task
import urllib2

@shared_task
def update():
    response = urllib2.urlopen('http://localhost:8983/solr/subjects/dataimport?command=full-import').read()
    print response