from __future__ import absolute_import
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task
import urllib, urllib2, pycurl, json
from base.models import *
from base.utils import *
from django.conf import settings
from os import listdir, remove
from os.path import isfile, join, splitext
from StringIO import StringIO

@shared_task
def update():
    response = urllib2.urlopen('http://localhost:8983/solr/subjects/dataimport?command=full-import').read()
    print response
    
@shared_task
def bulk_file_upload():
    """ This method presumes you are using ResourceSpace. If you are not, you will need to
    modify the method to properly make the API call and handle the response. """
    # get only files from directory
    files = [f for f in listdir(settings.FILE_UPLOAD_FOLDER) if isfile(join(settings.FILE_UPLOAD_FOLDER, f))]
    if files:
    
        # create new upload batch
        current_time = datetime.strftime(datetime.now(), '%Y-%m-%d_%H-%M-%S')
        upload_batch = UploadBatch(name = "File Upload " + current_time, data_upload = 0)
        upload_batch.save()
    
        for file in files:
            name_only, ext = splitext(file)
            upload_file_loc = settings.FILE_UPLOAD_FOLDER + '/' + file
            
            curl = pycurl.Curl()
            storage = StringIO()
            data = [ 
                ('userfile', (pycurl.FORM_FILE, upload_file_loc)),
                ('key', settings.FILE_UPLOAD_API_KEY),
                ('field8', "File Upload " + current_time) #this is very specific to UrOnline installation
            ]
            curl.setopt(pycurl.URL, settings.FILE_UPLOAD_API_URI)            
            curl.setopt(pycurl.HTTPPOST, data)
            curl.setopt(pycurl.WRITEFUNCTION, storage.write)
            curl.setopt(pycurl.USERAGENT, "API Client") 
            curl.perform()
            curl.close()
            content = storage.getvalue()
            json_content = json.loads(content)
            new_rsid = int(json_content['resource'][0]['ref'])
            
            # create new file in main db
            new_file = File(id = new_rsid, upload_batch = upload_batch, filetype = ext[1:])
            new_file.save()
            
            # create property for file name
            fn_prop_test = ResultProperty.objects.filter(display_field = 'file_name')
            
            # create a file name result property if one isn't designated
            if not (fn_prop_test and fn_prop_test[0].field_type):
                dp = DescriptiveProperty(property = 'Filename', last_mod_by = User.objects.get(pk=1), primary_type = 'MF', visible = 0)
                dp.save()
                fn_prop_test.field_type = dp
                fn_prop_test.save()
            else:
                dp = fn_prop_test[0].field_type
            
            new_fp = FileProperty(file = new_file, property = dp, property_value = file, last_mod_by = User.objects.get(pk=1), upload_batch = upload_batch)
            new_fp.save()
            
            # delete file from temp storage now that its uploaded
            remove(upload_file_loc)