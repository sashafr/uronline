from django.contrib import admin
from base.models import *
from django.forms.formsets import formset_factory
from django.db.models import Q, Count
import re
from django.forms import Textarea, ModelChoiceField, ModelForm
from django.utils.translation import ugettext_lazy as _
from base.utils import update_display_fields
from mptt.admin import MPTTModelAdmin
from suit_ckeditor.widgets import CKEditorWidget
from mptt.forms import TreeNodeChoiceField
from django import forms
from django.contrib.admin.views.main import ChangeList
from django.utils.http import urlencode
from django.contrib import messages
from django.contrib.auth.models import User
from suit.widgets import SuitSplitDateTimeWidget, LinkedSelect
from django_select2 import AutoModelSelect2Field, AutoHeavySelect2Widget,AutoModelSelect2MultipleField, AutoHeavySelect2MultipleWidget
from django.utils.encoding import force_unicode
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.safestring import mark_safe
from datetime import datetime
import csv
import urllib2
from suit.admin import SortableModelAdmin, SortableTabularInline
from filer.fields.image import FilerFileField
from django.conf import settings
import sys

OPERATOR = (
    ('and', 'AND'),
    ('or', 'OR'),
)

SEARCH_TYPE = (
    ('icontains', 'contains'),
    ('not_icontains', 'does not contain'),
    ('exact', 'equals'),
    ('not_exact', 'does not equal'),
    ('blank', 'is blank'),
    ('not_blank', 'is not blank'),
    ('istartswith', 'starts with'),
    ('not_istartswith', 'does not start with'),
    ('iendswith', 'ends with'),
    ('not_iendswith', 'does not end with'),
    ('gt', 'is greater than'),
    ('gte', 'is greater than or equal to'),
    ('lt', 'is less than'),
    ('lte', 'is less than or equal to'),
)

CONTROL_SEARCH_TYPE = (
    ('exact', 'equals'),
    ('not_exact', 'does not equal'),
)

""" ADMIN ACTIONS """

def import_data(modeladmin, request, queryset):
    """ For importing data from a CSV file into any of the four entity tables. """

    for upload in queryset:
    
        # check if already uploaded
        if upload.imported:
            message_bit = "FILE ALREADY IMPORTED (" + upload.name + ")"
            modeladmin.message_user(request, message_bit, level=messages.ERROR)
            continue
    
        # check import status
        import_errors = Column.objects.filter(data_upload = upload, ready_for_import = False)
        if import_errors:
            message_bit = "IMPORT FAILED (" + upload.name + "): Following columns are not ready for upload: "
            for err in import_errors:
                message_bit += "[" + err.title + "]: " + err.import_error + "; "
            modeladmin.message_user(request, message_bit, level=messages.ERROR)
            continue
    
        create = upload.create_on_no_match
    
        # get columns for matching rows
        matchers = Column.objects.filter(data_upload = upload, matching_field = True).order_by('matching_order')
        
        # get entity
        entity = upload.entity
        
        # if no matchers identified, check if row should create new entity 
        if not matchers and not create:
            message_bit = "IMPORT FAILED (" + upload.name + "): You must identify at least one column as a matcher or check 'Create New If No Match'."
            modeladmin.message_user(request, message_bit, level=messages.ERROR)
            continue
        # we have everything we need for import    
        else:
        
            # create an import batch to track data added
            batch = UploadBatch(name = upload.name, data_upload = upload.pk)
            batch.save()
            
            url = upload.file.get_download()
            response = urllib2.urlopen(url)
            reader = csv.reader(response)            
            for row_index, row in enumerate(reader):
                error_check = ''
                # skip the column headers!!
                if row_index == 0:
                    continue
            
                # have to increment row_index because CSV rows are displayed in Excel as 1 based indexing
                # this has be accounted for later when handling the errors
                row_index = row_index + 1
            
                if entity == 'S':
                    matches = Subject.objects.all()
                elif entity == 'L':
                    matches = Location.objects.all()
                elif entity == 'M':
                    matches = Media.objects.all()
                elif entity == 'F':
                    matches = File.objects.all()
                else:
                    matches = PersonOrg.objects.all()               
            
                # GET ENTITY MATCHES
                if matchers:
                    
                    q = Q()
                    match_msg = "Tried to match on: "
                    
                    for matcher in matchers:
                        match_msg += matcher.title + ', '
                        if matcher.property.control_field:
                            if entity == 'S':
                                cq = Q(Q(subjectcontrolproperty__control_property = matcher.property) & Q(subjectcontrolproperty__control_property_value__title = row[matcher.column_index].strip()))
                            elif entity == 'L':
                                cq = Q(Q(locationcontrolproperty__control_property = matcher.property) & Q(locationcontrolproperty__control_property_value__title = row[matcher.column_index].strip()))
                            elif entity == 'M':
                                cq = Q(Q(mediacontrolproperty__control_property = matcher.property) & Q(mediacontrolproperty__control_property_value__title = row[matcher.column_index].strip()))
                            elif entity == 'F':
                                cq = Q(Q(filecontrolproperty__control_property = matcher.property) & Q(filecontrolproperty__control_property_value__title = row[matcher.column_index].strip()))                         
                            else:
                                cq = Q(Q(personorgcontrolproperty__control_property = matcher.property) & Q(personorgcontrolproperty__control_property_value__title = row[matcher.column_index].strip()))
                        else:
                            if entity == 'S':
                                cq = Q(Q(subjectproperty__property = matcher.property) & Q(subjectproperty__property_value = row[matcher.column_index].strip()))
                            elif entity == 'L':
                                cq = Q(Q(locationproperty__property = matcher.property) & Q(locationproperty__property_value = row[matcher.column_index].strip()))
                            elif entity == 'M':
                                cq = Q(Q(mediaproperty__property = matcher.property) & Q(mediaproperty__property_value = row[matcher.column_index].strip()))
                            elif entity == 'F':
                                cq = Q(Q(fileproperty__property = matcher.property) & Q(fileproperty__property_value = row[matcher.column_index].strip()))                                
                            else:
                                cq = Q(Q(personorgproperty__property = matcher.property) & Q(personorgproperty__property_value = row[matcher.column_index].strip()))
                                
                        if matcher.matching_required:
                            q &= cq
                        else:
                            q |= cq
                    
                    matches = matches.filter(q)
                    match_count = matches.count()
                    
                if match_count == 0 and not create:
                    match_error = MatchImportError(data_upload = upload, row = row_index, error_text = 'MATCH FAILED: ' + match_msg, batch = batch)
                    match_error.save()
                    continue
                elif match_count > 1 and not upload.allow_multiple:
                    match_error = MatchImportError(data_upload = upload, row = row_index, error_text = 'MATCH FAILED: Matched too many entities. ' + match_msg, batch = batch)
                    match_error.save()
                    continue
                elif match_count == 1:
                    # if we did get a match, then we don't need to worry about creating an entry
                    create = False
                        
                # CREATE ENTITY IF NO MATCH AND CREATE IS TRUE
                if create:
                    if entity == 'S':
                        new_match = Subject(last_mod_by = request.user, upload_batch = batch)
                        new_match.save()
                        matches = Subject.objects.filter(pk=new_match.id)
                    elif entity == 'L':
                        new_match = Location(last_mod_by = request.user, upload_batch = batch)
                        new_match.save()
                        matches = Location.objects.filter(pk=new_match.id)                            
                    elif entity == 'M':
                        new_match = Media(last_mod_by = request.user, upload_batch = batch)
                        new_match.save()
                        matches = Media.objects.filter(pk=new_match.id) 
                    elif entity == 'F':
                        # because files must have a physical file attached to them, you can't use this upload feature to create a new file
                        match_error = MatchImportError(data_upload = upload, row = row_index, error_text = 'CREATE FILE FAILED: You can not create a file using the Data Bulk Upload feature, this row MUST match an existing file', batch = batch)
                        match_error.save()
                        continue
                    else:
                        new_match = PersonOrg(last_mod_by = request.user, upload_batch = batch)
                        new_match.save()
                        matches = PersonOrg.objects.get(pk=new_match.id)                            
                
                # COLLECTION
                if upload.collection:
                    col = upload.collection
                    if entity == 'S':
                        last_order = 0
                        col_ordered = SubjectCollection.objects.filter(collection = col).order_by('-order')
                        if col_ordered:
                            last_order = col_ordered[0].order + 1
                        for match in matches:                    
                            new_col = SubjectCollection(subject = match, collection = col, order = last_order, upload_batch = batch)
                            new_col.save()
                            last_order = last_order + 1
                    elif entity == 'L':
                        last_order = 0
                        col_ordered = LocationCollection.objects.filter(collection = col).order_by('-order')
                        if col_ordered:
                            last_order = col_ordered[0].order + 1
                        for match in matches:                    
                            new_col = LocationCollection(location = match, collection = col, order = last_order, upload_batch = batch)
                            new_col.save()
                            last_order = last_order + 1
                    elif entity == 'M':
                        last_order = 0
                        col_ordered = MediaCollection.objects.filter(collection = col).order_by('-order')
                        if col_ordered:
                            last_order = col_ordered[0].order + 1
                        for match in matches:                    
                            new_col = MediaCollection(media = match, collection = col, order = last_order, upload_batch = batch)
                            new_col.save()
                            last_order = last_order + 1
                    elif entity == 'F':
                        last_order = 0
                        col_ordered = FileCollection.objects.filter(collection = col).order_by('-order')
                        if col_ordered:
                            last_order = col_ordered[0].order + 1
                        for match in matches:                    
                            new_col = FileCollection(file = match, collection = col, order = last_order, upload_batch = batch)
                            new_col.save()
                            last_order = last_order + 1
                    elif entity == 'PO':
                        last_order = 0
                        col_ordered = PersonOrgCollection.objects.filter(collection = col).order_by('-order')
                        if col_ordered:
                            last_order = col_ordered[0].order + 1
                        for match in matches:                    
                            new_col = PersonOrgCollection(personorg = match, collection = col, order = last_order, upload_batch = batch)
                            new_col.save()
                            last_order = last_order + 1                               
                
                # ITERATE THROUGH COLUMNS
                for index, cell in enumerate(row):
                
                    cell = cell.strip()                         
                
                    # CHECK COLUMN INDEX
                    columns = Column.objects.filter(data_upload = upload, column_index = index)
                    column_count = columns.count()
                    if not columns or column_count > 1:
                        continue                            
                    else:
                        column = columns[0]
                        
                        # LINKED DATA
                        if column.linked_data:
                            # if a source wasn't selected and it got past the checks somehow, then skip
                            if not column.linked_data_source:
                                continue
                            source = column.linked_data_source
                            for match in matches:
                                if entity == 'S':
                                    sld = SubjectLinkedData(subject = match, source = source, link = cell, upload_batch = batch)
                                    sld.save()
                                elif entity == 'M':
                                    mld = MediaLinkedData(media = match, source = source, link = cell, upload_batch = batch)
                                    mld.save
                                elif entity == 'L':
                                    lld = LocationLinkedData(location = match, source = source, link = cell, upload_batch = batch)
                                    lld.save()
                                elif entity == 'F':
                                    fld = FileLinkedData(file = match, source = source, link = cell, upload_batch = batch)
                                    fld.save()
                                else:
                                    pld = PersonOrgLinkedData(personorg = match, source = source, link = cell, upload_batch = batch)
                                    pld.save()   
                        else:
                            # DESCRIPTIVE PROPERTY
                            dp = column.property
                            if (column.matching_field and not create) or column.insert_as_inline or column.insert_as_footnote:
                                continue
                            
                            inline = ''
                            footnote = ''
                            
                            # GET ANY NOTES FOR COLUMN
                            matching_inlines = Column.objects.filter(data_upload = upload, insert_as_inline = True, title_for_note = column.title.strip())
                            if matching_inlines:
                                for idx, mi in enumerate(matching_inlines):
                                    if idx > 0:
                                        inline += '; '
                                    if len(row) >= mi.column_index:
                                        inline += row[mi.column_index]
                                        
                            matching_footnotes = Column.objects.filter(data_upload = upload, insert_as_footnote = True, title_for_note = column.title.strip())
                            if matching_footnotes:
                                for idx, mf in enumerate(matching_footnotes):
                                    if idx > 0:
                                        footnote += '; '
                                    if len(row) >= mf.column_index:
                                        footnote += row[mf.column_index]
                                        
                            rel_note = inline
                            if inline != '' and footnote != '':
                                rel_note += '; '
                            rel_note += footnote
                            
                            # HANDLE RELATIONS
                            if column.relation:
                                if column.rel_entity == 'S':
                                    if column.rel_match_property.control_field:
                                        rels = Subject.objects.filter(subjectcontrolproperty__control_property = column.rel_match_property, subjectcontrolproperty__control_property_value__title = cell)
                                    else:
                                        rels = Subject.objects.filter(subjectproperty__property = column.rel_match_property, subjectproperty__property_value = cell)
                                elif column.rel_entity == 'L':
                                    if column.rel_match_property.control_field:
                                        rels = Location.objects.filter(locationcontrolproperty__control_property = column.rel_match_property, locationcontrolproperty__control_property_value__title = cell)
                                    else:
                                        rels = Location.objects.filter(locationproperty__property = column.rel_match_property, locationproperty__property_value = cell)
                                elif column.rel_entity == 'M':
                                    if column.rel_match_property.control_field:
                                        rels = Media.objects.filter(mediacontrolproperty__control_property = column.rel_match_property, mediacontrolproperty__control_property_value__title = cell)
                                    else:
                                        rels = Media.objects.filter(mediaproperty__property = column.rel_match_property, mediaproperty__property_value = cell)
                                elif column.rel_entity == 'F':
                                    if column.rel_match_property.control_field:
                                        rels = File.objects.filter(filecontrolproperty__control_property = column.rel_match_property, filecontrolproperty__control_property_value__title = cell)
                                    else:
                                        rels = File.objects.filter(fileproperty__property = column.rel_match_property, fileproperty__property_value = cell)
                                else:
                                    if column.rel_match_property.control_field:
                                        rels = PersonOrg.objects.filter(personorgcontrolproperty__control_property = column.rel_match_property, personorgcontrolproperty__control_property_value__title = cell)
                                    else:
                                        rels = PersonOrg.objects.filter(personorgproperty__property = column.rel_match_property, personorgproperty__property_value = cell)
                                
                                rel_count = rels.count()
                                if not rels:
                                    if entity == 'S':
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, subjects = matches, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)
                                    elif entity == 'L':
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, locations = matches, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)
                                    elif entity == 'M':
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, medias = matches, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)
                                    elif entity == 'F':
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, files = matches, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)
                                    else:
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, people = matches, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)      
                                    relation_error.save()
                                    continue
                                elif rel_count > 1:
                                    if entity == 'S':
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, subjects = matches, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)
                                    elif entity == 'L':
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, locations = matches, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)
                                    elif entity == 'M':
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, medias = matches, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)
                                    elif entity == 'F':
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, files = matches, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)
                                    else:
                                        relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, people = matches, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)       
                                    relation_error.save()
                                    continue
                                else:
                                    if entity == 'S':
                                        if column.rel_entity == 'L':
                                            for match in matches:
                                                lsr = LocationSubjectRelations(location = rels[0], subject = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                lsr.save()
                                        elif column.rel_entity == 'M':
                                            for match in matches:
                                                msr = MediaSubjectRelations(media = rels[0], subject = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                msr.save()
                                        elif column.rel_entity == 'F':
                                            for match in matches:
                                                sf = SubjectFile(subject = match, rsid = rels[0], upload_batch = batch)
                                                sf.save()
                                        elif column.rel_entity == 'PO':
                                            for match in matches:
                                                posr = SubjectPersonOrgRelations(person_org = rels[0], subject = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                posr.save()
                                    elif entity == 'L':
                                        if column.rel_entity == 'S':
                                            for match in matches:
                                                lsr = LocationSubjectRelations(subject = rels[0], location = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                lsr.save()
                                        elif column.rel_entity == 'M':
                                            for match in matches:
                                                mlr = MediaLocationRelations(media = rels[0], location = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                mlr.save()
                                        elif column.rel_entity == 'F':
                                            for match in matches:
                                                lf = LocationFile(location = match, rsid = rels[0], upload_batch = batch)
                                                lf.save()                                                
                                        elif column.rel_entity == 'PO':
                                            for match in matches:
                                                polr = LocationPersonOrgRelations(person_org = rels[0], location = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                polr.save()
                                    elif entity == 'M':
                                        if column.rel_entity == 'S':
                                            for match in matches:
                                                msr = MediaSubjectRelations(subject = rels[0], media = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                msr.save()
                                        elif column.rel_entity == 'L':
                                            for match in matches:
                                                mlr = MediaLocationRelations(location = rels[0], media = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                mlr.save()
                                        elif column.rel_entity == 'F':
                                            for match in matches:
                                                mf = MediaFile(media = match, rsid = rels[0], upload_batch = batch)
                                                mf.save()                                                
                                        elif column.rel_entity == 'PO':
                                            for match in matches:
                                                pomr = MediaPersonOrgRelations(person_org = rels[0], media = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                pomr.save()
                                    elif entity == 'F':
                                        if column.rel_entity == 'S':
                                            for match in matches:
                                                sf = SubjectFile(subject = rels[0], rsid = match, upload_batch = batch)
                                                sf.save()
                                        elif column.rel_entity == 'L':
                                            for match in matches:
                                                lf = LocationFile(location = rels[0], rsid = match, upload_batch = batch)
                                                lf.save()
                                        elif column.rel_entity == 'M':
                                            for match in matches:
                                                mf = MediaFile(media = rels[0], rsid = match, upload_batch = batch)
                                                mf.save()                                                
                                        elif column.rel_entity == 'PO':
                                            for match in matches:
                                                pof = PersonOrgFile(person_org = rels[0], rsid = match, upload_batch = batch)
                                                pof.save()
                                    elif entity == 'PO':
                                        if column.rel_entity == 'S':
                                            for match in matches:
                                                posr = SubjectPersonOrgRelations(subject = rels[0], person_org = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                posr.save()
                                        elif column.rel_entity == 'L':
                                            for match in matches:
                                                polr = LocationPersonOrgRelations(location = rels[0], person_org = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                polr.save()
                                        elif column.rel_entity == 'M':
                                            for match in matches:
                                                pomr = MediaPersonOrgRelations(media = rels[0], person_org = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                pomr.save()
                                        elif column.rel_entity == 'F':
                                            for match in matches:
                                                pof = PersonOrgFile(person_org = match, rsid = rels[0], upload_batch = batch)
                                                pof.save()                                                
                            
                            # HANDLE CONTROL FIELDS
                            elif dp.control_field:
                                cf = ControlField.objects.filter(title = cell, type = dp)
                                if cf:
                                    if entity == 'S':
                                        for match in matches:
                                            scp = SubjectControlProperty(subject = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                            scp.save()
                                    elif entity == 'L':
                                        for match in matches:
                                            lcp = LocationControlProperty(location = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                            lcp.save()
                                    elif entity == 'M':
                                        for match in matches:
                                            mcp = MediaControlProperty(media = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                            mcp.save()
                                    elif entity == 'F':
                                        for match in matches:
                                            fcp = FileControlProperty(file = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                            fcp.save()                                            
                                    elif entity == 'PO':
                                        for match in matches:
                                            pocp = PersonOrgControlProperty(person_org = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                            pocp.save()
                                else:
                                    if entity == 'S':
                                        cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, subjects = matches, batch = batch)
                                    elif entity == 'L':
                                        cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, locations = matches, batch = batch)
                                    elif entity == 'M':
                                        cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, media = matches, batch = batch)
                                    elif entity == 'F':
                                        cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, files = matches, batch = batch)
                                    else:
                                        cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, people = matches, batch = batch)
                                    cf_error.save()
                                    
                            # HANDLE FREE FORM PROPERTY
                            else:
                                if entity == 'S':
                                    for match in matches:
                                        sp = SubjectProperty(subject = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                        sp.save()
                                elif entity == 'L':
                                    for match in matches:
                                        lp = LocationProperty(location = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                        lp.save()
                                elif entity == 'M':
                                    for match in matches:
                                        mp = MediaProperty(media = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                        mp.save()
                                elif entity == 'F':
                                    for match in matches:
                                        fp = FileProperty(file = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                        fp.save()                                        
                                elif entity == 'PO':
                                    for match in matches:
                                        pop = PersonOrgProperty(person_org = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                        pop.save()
        
            upload.imported = True
            upload.save()
            message_bit = "Import " + upload.name + " completed. Click on data upload file to view any errors generated by upload."
            modeladmin.message_user(request, message_bit, level=messages.SUCCESS)
            
import_data.short_description = "Import data from selected CSV files"

def rollback_import(modeladmin, request, queryset):
    """ Deletes all data added created by this upload """
    
    for upload in queryset:
        related_batches = UploadBatch.objects.filter(data_upload = upload.pk)
        for batch in related_batches:
            batch.delete()
        upload.imported = False
        upload.save()
        
rollback_import.short_description = "Rollback import - PERMANENTLY DELETE all data created by import"

""" SPECIAL FORM FIELDS """

class SubjectChoices(AutoModelSelect2Field):
    queryset = Subject.objects
    search_fields = ['title1__icontains', 'title2__icontains', 'title3__icontains',]
    
class MediaChoices(AutoModelSelect2Field):
    queryset = Media.objects
    search_fields = ['title1__icontains', 'title2__icontains', 'title3__icontains',]    

class LocationChoices(AutoModelSelect2Field):
    queryset = Location.objects
    search_fields = ['title1__icontains', 'title2__icontains', 'title3__icontains',] 
    
class PersonOrgChoices(AutoModelSelect2Field):
    queryset = PersonOrg.objects
    search_fields = ['title1__icontains', 'title2__icontains', 'title3__icontains',]
    
class FileChoices(AutoModelSelect2Field):
    queryset = File.objects
    search_fields = ['title1__icontains', 'title2__icontains', 'title3__icontains',]    

""" LIST FILTERS """

class ControlFieldTypeListFilter(admin.SimpleListFilter):
    """ Modified Descriptive Property filter that only includes Descriptive
    Properties marked as control_field = true """
    
    title = _('type')
    parameter_name = 'field_type'

    def lookups(self, request, model_admin):
        control_fields = tuple((prop.id, prop.property) for prop in DescriptiveProperty.objects.filter(control_field=True))
        return control_fields

    def queryset(self, request, queryset):
        if self.value():
            prop_id = self.value()
            return queryset.filter(type__id = prop_id)
            
class MediaCollectionListFilter(admin.SimpleListFilter):
    """ Many to many filter to filter based on collections """
    
    title = _('collection')
    parameter_name = 'collection'
    
    def lookups(self, request, model_admin):
        return tuple((col.id, col.title) for col in Collection.objects.all())
        
    def queryset(self, request, queryset):
        if self.value():
            coll_id = self.value()
            return queryset.filter(mediacollection__collection_id = coll_id)
            
class LegrainDoneListFilter(admin.SimpleListFilter):
    """ Checking if Legrain media is done TOO BE DELETED"""
    
    title = _('done')
    parameter_name = 'done'
    
    def lookups(self, request, model_admin):
        return (('yes', 'Yes'), ('no', 'No'))
        
    def queryset(self, request, queryset):
        if self.value():
            done = self.value()
            if done == 'yes':
                return queryset.filter(Q(legrainnotecards__done = True) | Q(legrainimages__done = True))
            elif done == 'no':
                return queryset.filter(~Q(legrainnotecards__done = True) & ~Q(legrainimages__done = True))
            else:
                return queryset            
            
""" FORMS """
        
class AdminAdvSearchForm(forms.Form):
    """ Used on the Subject Admin page to search objects by related Properties """
    
    # controlled properties
    cp1 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(control_field = True))
    cst1 = forms.ChoiceField(label='', required=False, choices=CONTROL_SEARCH_TYPE)
    cv1 = forms.ChoiceField(label='', required=False, choices=(('default', 'Select a Property'),))
    cp2 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(control_field = True))
    cst2 = forms.ChoiceField(label='', required=False, choices=CONTROL_SEARCH_TYPE)
    cv2 = forms.ChoiceField(label='', required=False, choices=(('default', 'Select a Property'),))
    cp3 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(control_field = True))
    cst3 = forms.ChoiceField(label='', required=False, choices=CONTROL_SEARCH_TYPE)
    cv3 = forms.ChoiceField(label='', required=False, choices=(('default', 'Select a Property'),))     
    
    # free-form properties
    fp1 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.all())
    fst1 = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    fv1 = forms.CharField(label='', required=False)
    op1 = forms.ChoiceField(label='', required=False, choices=OPERATOR)
    fp2 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.all())
    fst2 = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    fv2 = forms.CharField(label='', required=False)
    op2 = forms.ChoiceField(label='', required=False, choices=OPERATOR)
    fp3 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.all())
    fst3 = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    fv3 = forms.CharField(label='', required=False)
    
    # filters
    loc = TreeNodeChoiceField(label='Context', required=False, queryset=Location.objects.all())
    img = forms.ChoiceField(label='Has Image', required=False, choices=(('default', '---'), ('yes', 'Yes'), ('no', 'No')))
    pub = forms.ModelChoiceField(label='Published', required=False, queryset=Media.objects.filter(type_id=2).order_by('title'))
    last_mod = forms.ModelChoiceField(label='Last Editor', required=False, queryset=User.objects.all())
    col = forms.ModelChoiceField(label='Collection', required=False, queryset=Collection.objects.all())
    
    # utilities
    dup_prop = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.all(), empty_label = "Find Objects with Multiple...")
    
class FileAdminAdvSearchForm(forms.Form):
    
    # controlled properties
    cp1 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(control_field = True).filter(Q(primary_type='MF') | Q(primary_type='AL')))
    cst1 = forms.ChoiceField(label='', required=False, choices=CONTROL_SEARCH_TYPE)
    cv1 = forms.ChoiceField(label='', required=False, choices=(('default', 'Select a Property'),))
    cp2 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(control_field = True).filter(Q(primary_type='MF') | Q(primary_type='AL')))
    cst2 = forms.ChoiceField(label='', required=False, choices=CONTROL_SEARCH_TYPE)
    cv2 = forms.ChoiceField(label='', required=False, choices=(('default', 'Select a Property'),))
    cp3 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(control_field = True).filter(Q(primary_type='MF') | Q(primary_type='AL')))
    cst3 = forms.ChoiceField(label='', required=False, choices=CONTROL_SEARCH_TYPE)
    cv3 = forms.ChoiceField(label='', required=False, choices=(('default', 'Select a Property'),))     
    
    # free-form properties
    fp1 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(Q(primary_type='MF') | Q(primary_type='AL')))
    fst1 = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    fv1 = forms.CharField(label='', required=False)
    op1 = forms.ChoiceField(label='', required=False, choices=OPERATOR)
    fp2 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(Q(primary_type='MF') | Q(primary_type='AL')))
    fst2 = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    fv2 = forms.CharField(label='', required=False)
    op2 = forms.ChoiceField(label='', required=False, choices=OPERATOR)
    fp3 = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(Q(primary_type='MF') | Q(primary_type='AL')))
    fst3 = forms.ChoiceField(label='', required=False, choices=SEARCH_TYPE)
    fv3 = forms.CharField(label='', required=False)
    
    # filters
    sub = SubjectChoices(
        label = Subject._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Subject._meta.verbose_name
            }
        )
    )
    loc = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )
    med = MediaChoices(
        label = Media._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Media._meta.verbose_name
            }
        )
    )
    po = PersonOrgChoices(
        label = PersonOrg._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % PersonOrg._meta.verbose_name
            }
        )
    )
    col = forms.ModelChoiceField(label='Collection', required=False, queryset=Collection.objects.all())
    check_unrelated = forms.BooleanField(label='Unrelated Files Only', required=False)
    
    # utilities
    dup_prop = forms.ModelChoiceField(label='', required=False, queryset=DescriptiveProperty.objects.filter(Q(primary_type='MF') | Q(primary_type='AL')), empty_label = "Find Files with Multiple...")    

class ControlFieldForm(ModelForm):
    """ Used on Control Field Change Form page to edit what is displayed on Control Field value public pages """
    
    class Meta:
  
        _ck_editor_toolbar = [
            {'name': 'basicstyles', 'groups': ['basicstyles', 'cleanup']},
            {'name': 'paragraph',
             'groups': ['list', 'indent', 'blocks', 'align']},
            {'name': 'document', 'groups': ['mode']}, '/',
            {'name': 'styles'}, {'name': 'colors'},
            {'name': 'insert_custom',
             'items': ['Image', 'Flash', 'Table', 'HorizontalRule']},
            {'name': 'links'},
            {'name': 'about'}]

        _ck_editor_config = {'autoGrow_onStartup': True,
                             'autoGrow_minHeight': 100,
                             'autoGrow_maxHeight': 250,
                             'extraPlugins': 'autogrow',
                             'toolbarGroups': _ck_editor_toolbar}            
  
        widgets = {
            'notes': CKEditorWidget(editor_options=_ck_editor_config),
        }

class BlogPostForm(ModelForm):
    """ Used on Blog Post Change Form page to edit blog posts """
    
    class Meta:
  
        _ck_editor_toolbar = [
            {'name': 'basicstyles', 'groups': ['basicstyles', 'cleanup']},
            {'name': 'paragraph',
             'groups': ['list', 'indent', 'blocks', 'align']},
            {'name': 'document', 'groups': ['mode']}, '/',
            {'name': 'styles'}, {'name': 'colors'},
            {'name': 'insert_custom',
             'items': ['Image', 'Flash', 'Table', 'HorizontalRule']},
            {'name': 'links'},
            {'name': 'about'}]

        _ck_editor_config = {'autoGrow_onStartup': True,
                             'autoGrow_minHeight': 100,
                             'autoGrow_maxHeight': 250,
                             'extraPlugins': 'autogrow',
                             'toolbarGroups': _ck_editor_toolbar}            
  
        widgets = {
            'body': CKEditorWidget(editor_options=_ck_editor_config),
        }

class FileForm(ModelForm):
    
    rsid = FileChoices(        
        label = 'File',
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
            }
        ),
    ) 

    class Meta:
        model = File

class LocObjRelForm(ModelForm):
    location = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )

    class Meta:
        model = LocationSubjectRelations
        
class SubjectCollectionForm(ModelForm):
    subject = SubjectChoices(
        label = Subject._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Subject._meta.verbose_name
            }
        )
    )

    class Meta:
          model = SubjectCollection
          
class LocationCollectionForm(ModelForm):
    location = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )

    class Meta:
          model = LocationCollection

class MediaCollectionForm(ModelForm):
    media = MediaChoices(
        label = Media._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Media._meta.verbose_name
            }
        )
    )

    class Meta:
          model = MediaCollection

class PersonOrgCollectionForm(ModelForm):
    person_org = PersonOrgChoices(
        label = PersonOrg._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % PersonOrg._meta.verbose_name
            }
        )
    )

    class Meta:
          model = PersonOrgCollection          
        
class DataUploadForm(ModelForm):
    """ Used to make certain the uploaded file is CSV. """
    file = FileChoices(        
        label = 'File',
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
            }
        ),
    ) 

    class Meta:
        model = DataUpload
        
    def clean(self):
        if self.cleaned_data.get('file'):
            file = self.cleaned_data.get('file')
            if not file.title.endswith('.csv'):
                raise forms.ValidationError(u'Not a valid CSV file')        
        return self.cleaned_data
        
class MatchImportErrorForm(ModelForm):
    subject = SubjectChoices(
        label = Subject._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Subject._meta.verbose_name
            }
        )
    )
    location = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )
    media = MediaChoices(
        label = Media._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Media._meta.verbose_name
            }
        )
    )
    file = FileChoices(
        label = File._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % File._meta.verbose_name
            }
        )
    )    
    person = PersonOrgChoices(
        label = PersonOrg._meta.verbose_name.capitalize(),
        required = False,
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % PersonOrg._meta.verbose_name
            }
        )
    )    
    
    class Meta:
          model = MatchImportError

class RelationImportErrorForm(ModelForm):
    subject = SubjectChoices(
        label = Subject._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Subject._meta.verbose_name
            }
        )
    )
    location = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )
    media = MediaChoices(
        label = Media._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Media._meta.verbose_name
            }
        )
    )
    person = PersonOrgChoices(
        label = PersonOrg._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % PersonOrg._meta.verbose_name
            }
        )
    )    
    
    class Meta:
          model = RelationImportError

class SubjectFileAdminForm(ModelForm):
    subject = SubjectChoices(
        label = Subject._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Subject._meta.verbose_name
            }
        )
    )  
    
    class Meta:
          model = SubjectFile
          
class LocationFileAdminForm(ModelForm):
    location = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )     
    
    class Meta:
          model = LocationFile

class MediaFileAdminForm(ModelForm):
    media = MediaChoices(
        label = Media._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Media._meta.verbose_name
            }
        )
    )      
    
    class Meta:
          model = MediaFile

class PersonOrgFileAdminForm(ModelForm):
    person_org = PersonOrgChoices(
        label = PersonOrg._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % PersonOrg._meta.verbose_name
            }
        )
    )
    
    class Meta:
          model = PersonOrgFile          

""" INLINES """

""" LINKED DATA INLINES """

class ControlFieldLinkedDataInline(admin.TabularInline):
    model = ControlFieldLinkedData
    fields = ['source', 'link']    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    extra = 1
    
class PersonOrgLinkedDataInline(admin.TabularInline):
    model = PersonOrgLinkedData
    fields = ['source', 'link']    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    extra = 1 

class FileLinkedDataInline(admin.TabularInline):
    model = FileLinkedData
    fields = ['source', 'link']
    extra = 1 
    suit_classes = 'suit-tab suit-tab-linked'    

""" DESCRIPTIVE PROPERTY & CONTROLLED PROPERTY INLINES """

""" PROPERTY VALUE INLINES """

class SubjectControlPropertyInline(admin.TabularInline):
    
    model = SubjectControlProperty
    fields = ['control_property', 'control_property_value', 'notes', 'last_mod_by'] 
    readonly_fields = ('last_mod_by',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_classes = 'suit-tab suit-tab-general'
    extra = 3
    template = 'admin/base/subject/tabular.html'
    ordering = ('control_property__order',)
    
    # for control property form dropdown, only show descriptive properties marked as control_field = true
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'control_property':
            if request.user == User.objects.get(pk=7) or request.user == User.objects.get(pk=17):
                kwargs["queryset"] = DescriptiveProperty.objects.filter(Q(Q(pk = 170) | Q(pk = 121)))
            else:
                kwargs["queryset"] = DescriptiveProperty.objects.filter(control_field = True)
        return super(SubjectControlPropertyInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
    def queryset(self, request):
    
        qs = super(SubjectControlPropertyInline, self).queryset(request)
        
        if request.user == User.objects.get(pk=7) or request.user == User.objects.get(pk=17):
            qs = qs.filter(Q(Q(control_property_id = 170) | Q(control_property_id = 121)))
            
        return qs
        
class FilePropertyInline(admin.TabularInline):
    model = FileProperty
    fields = ['property', 'property_value', 'inline_notes', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    ordering = ('property__order',)
    suit_classes = 'suit-tab suit-tab-general'    
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'property':
            kwargs["queryset"] = DescriptiveProperty.objects.filter(Q(primary_type='MF') | Q(primary_type='AL')).exclude(control_field = True)
        return super(FilePropertyInline, self).formfield_for_foreignkey(db_field, request, **kwargs)        
        
class FileControlPropertyInline(admin.TabularInline):
    model = FileControlProperty
    fields = ['control_property', 'control_property_value', 'inline_notes', 'notes', 'last_mod_by'] 
    readonly_fields = ('last_mod_by',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    extra = 3
    template = 'admin/base/file/tabular.html'
    ordering = ('control_property__order',)
    suit_classes = 'suit-tab suit-tab-general'    
    
    # for control property form dropdown, only show descriptive properties marked as control_field = true
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'control_property':
            kwargs["queryset"] = DescriptiveProperty.objects.filter(control_field = True).filter(Q(primary_type='MF') | Q(primary_type='AL'))
        return super(FileControlPropertyInline, self).formfield_for_foreignkey(db_field, request, **kwargs) 

""" RELATION INLINES """

class FileSubjectRelationsInline(admin.TabularInline):
    model = SubjectFile
    fields = ['subject', 'thumbnail']
    suit_classes = 'suit-tab suit-tab-relations'
    extra = 1
    form = SubjectFileAdminForm

class FileLocationRelationsInline(admin.TabularInline):
    model = LocationFile
    fields = ['location', 'thumbnail']   
    suit_classes = 'suit-tab suit-tab-relations'
    extra = 1
    form = LocationFileAdminForm

class FileMediaRelationsInline(admin.TabularInline):
    model = MediaFile
    fields = ['media', 'thumbnail']  
    suit_classes = 'suit-tab suit-tab-relations'
    extra = 1
    form = MediaFileAdminForm

class FilePersonOrgRelationsInline(admin.TabularInline):
    model = PersonOrgFile
    fields = ['person_org', 'thumbnail']
    suit_classes = 'suit-tab suit-tab-relations'
    extra = 1
    form = PersonOrgFileAdminForm    
        
""" COLLECTION INLINES """

class SubjectCollectionInline(SortableTabularInline):
    model = SubjectCollection
    fields = ['get_thumbnail_admin', 'subject', 'notes', 'order']
    readonly_fields = ('get_thumbnail_admin',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    form = SubjectCollectionForm
    sortable = 'order'
    
class LocationCollectionInline(SortableTabularInline):
    model = LocationCollection
    fields = ['get_thumbnail_admin', 'location', 'notes', 'order']
    readonly_fields = ('get_thumbnail_admin',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    form = LocationCollectionForm
    sortable = 'order'

class MediaCollectionInline(SortableTabularInline):
    model = MediaCollection
    fields = ['get_thumbnail_admin', 'media', 'notes', 'order']
    readonly_fields = ('get_thumbnail_admin',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    form = MediaCollectionForm
    sortable = 'order'

class PersonOrgCollectionInline(SortableTabularInline):
    model = PersonOrgCollection
    fields = ['get_thumbnail_admin', 'person_org', 'notes', 'order']
    readonly_fields = ('get_thumbnail_admin',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    form = PersonOrgCollectionForm
    sortable = 'order'   

class SubjectCollectionEntityInline(admin.TabularInline):
    model = SubjectCollection
    fields = ['collection', 'notes', 'order']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    
class LocationCollectionEntityInline(admin.TabularInline):
    model = LocationCollection
    fields = ['collection', 'notes', 'order']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }

class MediaCollectionEntityInline(admin.TabularInline):
    model = MediaCollection
    fields = ['collection', 'notes', 'order']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }

class PersonOrgCollectionEntityInline(admin.TabularInline):
    model = PersonOrgCollection
    fields = ['collection', 'notes', 'order']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }     
    
class FileCollectionInline(admin.TabularInline):
    model = FileCollection
    fields = ['collection', 'notes', 'order']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_classes = 'suit-tab suit-tab-collections'    
    
""" SITE SETTINGS ETC INLINES """

class ColumnInline(admin.StackedInline):
    model = Column
    extra = 0
    readonly_fields = ('title', 'ready_for_import', 'import_error', 'column_index')
    fields = ('title', 'column_index', 'ready_for_import', 'import_error', 'property', 'matching_field', 'matching_order', 'matching_required', 'insert_as_inline', 'insert_as_footnote', 'title_for_note', 'relation', 'rel_entity', 'rel_match_property',  'linked_data', 'linked_data_source')
    suit_classes = 'suit-tab suit-tab-step1'
    
class UploadBatchInline(admin.TabularInline):
    model = UploadBatch
    extra = 0
    readonly_fields = ('name')
    fields = ('name', )
    suit_classes = 'suit-tab suit-tab-step1'    
    
class MatchImportErrorInline(admin.TabularInline):
    model = MatchImportError
    extra = 0
    readonly_fields = ('row', 'error_text')
    fields = ('row', 'error_text', 'subject', 'location', 'media', 'file', 'person')
    suit_classes = 'suit-tab suit-tab-step2'
    form = MatchImportErrorForm
    
class RelationImportErrorInline(admin.TabularInline):
    model = RelationImportError
    extra = 0
    readonly_fields = ('row', 'column', 'error_text')
    fields = ('row', 'column', 'error_text', 'subject', 'location', 'media', 'person')
    suit_classes = 'suit-tab suit-tab-step2'
    form = RelationImportErrorForm

class ControlFieldImportErrorInline(admin.TabularInline):
    model = ControlFieldImportError
    extra = 0
    readonly_fields = ('row', 'column', 'error_text')
    fields = ('row', 'column', 'error_text', 'control_field')
    suit_classes = 'suit-tab suit-tab-step2'

class MiscImportErrorInline(admin.TabularInline):
    model = MiscImportError
    extra = 0
    readonly_fields = ('row', 'column', 'error_text')
    fields = ('row', 'column', 'error_text')
    suit_classes = 'suit-tab suit-tab-step2'

""" ADMINS """

""" LINKED DATA ADMIN """

class LinkedDataSourceAdmin(admin.ModelAdmin):    
    search_fields = ['title']
    list_display = ('title', 'link')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    
admin.site.register(LinkedDataSource, LinkedDataSourceAdmin)   
    
""" HELPER ADMIN """

class PropertyTypeAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')    
    search_fields = ['type']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(PropertyType, PropertyTypeAdmin)    
    
""" DESCRIPTIVE PROPERTY & CONTROLLED PROPERTY ADMIN """    
 
class ControlFieldAdmin(MPTTModelAdmin, SortableModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')    
    inlines = [ControlFieldLinkedDataInline]
    search_fields = ['title', 'definition']
    list_display = ('ancestors', 'title', 'definition', 'type')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    list_filter = (ControlFieldTypeListFilter,)
    list_display_links = ('title',)
    change_form_template = 'admin/base/change_form_tree_models.html'
    suit_form_includes = (
        ('admin/base/control_field_search.html', 'bottom'),
    )
    form = ControlFieldForm
    fields = ('title', 'definition', 'notes', 'type', 'parent', 'created', 'modified', 'last_mod_by')
    sortable = 'order'
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        if not obj.pk:
            obj.order = 99
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, ControlFieldLinkedData): #Check if it is the correct type of inline
                instance.last_mod_by = request.user            
                instance.save()
                
    # limit types visible on change form to descriptive properties marked as control_field = true
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'type':
            kwargs["queryset"] = DescriptiveProperty.objects.filter(control_field = True)
        return super(ControlFieldAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(ControlField, ControlFieldAdmin)

""" ARCHAEOLOGICAL ENTITY ADMIN """

class FileAdmin(admin.ModelAdmin):
    fields = ['get_thumbnail_admin', 'get_download_admin', 'title', 'notes', 'public', 'uploaded', 'upload_batch']
    readonly_fields = ('get_thumbnail_admin', 'get_download_admin', 'title', 'uploaded', 'upload_batch')    
    inlines = [FilePropertyInline, FileControlPropertyInline, FileSubjectRelationsInline, FileLocationRelationsInline, FileMediaRelationsInline, FilePersonOrgRelationsInline, FileCollectionInline, FileLinkedDataInline]  
    search_fields = ['title', 'title1', 'title2', 'title3', 'desc1', 'desc2', 'desc3']
    list_display = ('get_thumbnail_admin', 'title1', 'title2', 'title3', 'desc1', 'desc2', 'desc3', 'filetype', 'public', 'uploaded', 'upload_batch')
    list_filter = ('filetype', 'public', 'upload_batch')
    list_display_links = ('title1', )
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    advanced_search_form = FileAdminAdvSearchForm()
    # actions = ['export_csv']
    suit_form_tabs = (('general', 'File'), ('relations', 'Relations'), ('collections', 'Collections'), ('linked', 'Linked Data'))
    fieldsets = [
        (None, {
            'classes': ('suit-tab', 'suit-tab-general'),
            'fields': ['get_thumbnail_admin', 'get_download_admin', 'title', 'notes', 'public', 'uploaded', 'upload_batch']
        }),
    ]    
    
    change_list_template = 'admin/base/file/change_list.html'
    change_form_template = 'admin/base/file/change_form.html'
    
    class Media:
        # the django-select2 styles have to be added manually for some reason, otherwise they don't work
        css = {
            "all": ("django_select2/css/select2.min.css",)
        }
        
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """ Added to allow browsing by collection """
    
        extra_context = extra_context or {}
        collections = FileCollection.objects.filter(file_id = object_id)
        collection_list = []
        for coll in collections:
            coll_info = {}
            current_order = coll.order
            lt = FileCollection.objects.filter(collection = coll.collection, order__lt = current_order).order_by('-order')
            if lt:
                coll_info['prev'] = lt[0].file_id
            gt = FileCollection.objects.filter(collection = coll.collection, order__gt = current_order).order_by('order')
            if gt:
                coll_info['next'] = gt[0].file_id
            if lt or gt:
                coll_info['name'] = coll.collection.title
            collection_list.append(coll_info)
        extra_context['collections'] = collection_list
        return super(FileAdmin, self).change_view(request, object_id, form_url, extra_context = extra_context)
        
    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        if request.POST.has_key("_viewnext"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            next = request.POST.get("next_id")
            if next:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % next)
        if request.POST.has_key("_viewprev"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            prev = request.POST.get("prev_id")
            if prev:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % prev)
        return super(FileAdmin, self).response_change(request, obj)     
        
    # def bulk_update(self, request, queryset):
        # """ Redirects to a bulk update form """
        
        # selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        # return HttpResponseRedirect("/bulk_update_subject/?ids=%s" % ",".join(selected))
        
    # def export_csv(self, request, queryset):
        # """ Temporary export solution while models are redesigned 
        
        # This is horribly hackish. If it isn't fixed by Dec 2015..... burn it all"""
        # response = HttpResponse(content_type='text/csv')
        # filename_str = '"admin_search_results_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S") + '.csv"'
        # response['Content-Disposition'] = 'attachment; filename=' + filename_str
        
        # writer = csv.writer(response)
        # titles = []
        # rows = []
        # for result in queryset:
            # row = []
            # row_dict = {}
            # control_properties = result.subjectcontrolproperty_set.all()
            # properties = result.subjectproperty_set.all()
            # for each_prop in properties:
                # prop_name = each_prop.property.property
                # prop_value = each_prop.property_value
                # if not (prop_name in titles):
                    # column_index = len(titles)                        
                    # titles.append(prop_name)
                # else:
                    # column_index = titles.index(prop_name)
                    # if column_index in row_dict:
                        # prop_value = row_dict[column_index] + '; ' + prop_value
                # row_dict[column_index] = prop_value
            # for each_prop in control_properties:
                # prop_name = each_prop.control_property.property
                # prop_value = each_prop.control_property_value.title
                # if not (prop_name in titles):
                    # column_index = len(titles)   
                    # titles.append(prop_name)
                # else:
                    # column_index = titles.index(prop_name)
                    # if column_index in row_dict:
                        # prop_value = row_dict[column_index] + '; ' + prop_value
                # row_dict[column_index] = prop_value
            # for i in range(len(titles)):
                # if i in row_dict:
                    # row.append(row_dict[i])
                # else:
                    # row.append('')
                    
            # rows.append(row)

        # writer.writerow(titles)
        # for each_row in rows:
            # writer.writerow([unicode(s).encode("utf-8") for s in each_row])
        # return response
        
    # export_csv.short_description = "Export current search results to CSV"
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, FileProperty) or isinstance(instance, FileControlProperty):
                instance.last_mod_by = request.user            
            instance.save()
                
            
    # advanced search form based on https://djangosnippets.org/snippets/2322/ and http://stackoverflow.com/questions/8494200/django-admin-custom-change-list-arguments-override-e-1 

    def get_changelist(self, request, **kwargs):
        adv_search_fields = {}
        asf = self.advanced_search_form
        for key in asf.fields.keys():
            temp = self.other_search_fields.get(key, None)
            if temp:
                adv_search_fields[key] = temp[0]
            else:
                adv_search_fields[key] = ''
        
        class AdvChangeList(ChangeList):
            
            def get_query_string(self, new_params=None, remove=None):
                """ Overriding get_query_string ensures that the admin still considers
                the additional search fields as parameters, even tho they are popped from 
                the request.GET """
                
                if new_params is None:
                    new_params = {}
                if remove is None:
                    remove = []
                p = self.params.copy()
                for r in remove:
                    for k in list(p):
                        if k.startswith(r):
                            del p[k]
                for k, v in new_params.items():
                    if v is None:
                        if k in p:
                            del p[k]
                    else:
                        p[k] = v
                
                extra_params = ''
                for field, val in adv_search_fields.items():
                    extra_params += '&' + field + '=' + val
                
                return '?%s%s' % (urlencode(sorted(p.items())), extra_params)
                
        return AdvChangeList
        
    def lookup_allowed(self, key, value):
        if key in self.advanced_search_form.fields.keys():
            return True
        if key == 'attach_type':
            return True
        return super(FileAdmin, self).lookup_allowed(key, value)
        
    def changelist_view(self, request, extra_context=None, **kwargs):
        self.other_search_fields = {}
        asf = self.advanced_search_form
        extra_context = {'asf': asf}
        
        request.GET._mutable = True
        
        for key in asf.fields.keys():
            try:
                temp = request.GET.pop(key)
            except KeyError:
                pass
            else:
                if temp != ['']:
                    self.other_search_fields[key] = temp
                    
        request.GET._mutable = False
        return super(FileAdmin, self).changelist_view(request, extra_context = extra_context)
        
    def get_search_results(self, request, queryset, search_term):
        """ Performs either a simple search using the search_term or an 
        advanced search using values taken from the AdvancedSearchForm """
        
        queryset, use_distinct = super(FileAdmin, self).get_search_results(request, queryset, search_term)
        
        # get all the fields from the adv search form
        adv_fields = {}
        asf = self.advanced_search_form
        for key in asf.fields.keys():
            temp = self.other_search_fields.get(key, None)
            if temp:
                adv_fields[key] = temp[0]
            else:
                adv_fields[key] = ''
        
        # NOTE: simple search has already been applied
        
        # RELATED TABLES FILTER
        check_unrelated = adv_fields['check_unrelated']
        if check_unrelated == 'on':
            queryset = queryset.filter(subjectfile__isnull = True)
            queryset = queryset.filter(locationfile__isnull = True)
            queryset = queryset.filter(mediafile__isnull = True)
            queryset = queryset.filter(personorgfile__isnull = True)

        else:
            # if check_unrelated in checked then they are looking for files with no relations so skip
            sub = adv_fields['sub']
            if sub != '':
                queryset = queryset.filter(subjectfile__subject_id=sub)        
            
            loc = adv_fields['loc']
            if loc != '':
                queryset = queryset.filter(locationfile__location_id=loc)
                
            med = adv_fields['med']
            if med != '':
                queryset = queryset.filter(mediafile__media_id=med)

            po = adv_fields['po']
            if po != '':
                queryset = queryset.filter(personorgfile__person_org_id=po)

        col = adv_fields['col']
        if col != '':
            queryset = queryset.filter(filecollection__collection_id = col)            
        
        # CONTROL PROPERTY FILTER
        for i in range(1, 4):
            cp = adv_fields['cp' + str(i)]
            cst = adv_fields['cst' + str(i)]
            cv = adv_fields['cv' + str(i)]
            
            if cp != '' and cv != 'default' and cv != '':
                cf = ControlField.objects.filter(pk = cv)
                cf_desc = cf[0].get_descendants(include_self=True)
                ccq = Q()
                for field in cf_desc:
                    if cst == 'exact':
                        ccq |= Q(filecontrolproperty__control_property_value = field.id)
                    else:
                        ccq &= ~Q(filecontrolproperty__control_property_value = field.id)
                        
                queryset = queryset.filter(ccq)
                
        # FREE FORM PROPERTY FILTER
        for i in range (1, 4):
            if i != 1:
                op = adv_fields['op' + str(i - 1)]
            else:
                op = ''
            fp = adv_fields['fp' + str(i)]
            fst = adv_fields['fst' + str(i)]
            fv = adv_fields['fv' + str(i)]

            negate = False # whether or not the query will be negated
            kwargs = {}
            cq = Q()
            
            # remove and save negation, if present
            if fst.startswith('not'):
                negate = True
                fst = fst[4:]
            
            if not(fv == '' and fst != 'blank'):
                
                if fst == 'blank':
                    #if property is Any, then skip all b/c query asks for doc with 'any' blank properties
                    if fp == '':
                        continue
                
                    # BLANK is a special case negation (essentially a double negative), so handle differently
                    if negate:
                        cq = Q(fileproperty__property = fp)
                    else:
                        cq = ~Q(fileproperty__property = fp)
                        
                else:
                    kwargs = {str('fileproperty__property_value__%s' % fst) : str('%s' % fv)}
                    
                    # check if a property was selected and build the current query
                    if fp == '':
                        # if no property selected, than search thru ALL properties
                        if negate:
                            cq = ~Q(**kwargs)
                        else:
                            cq = Q(**kwargs)
                    else:
                        if negate:
                            cq = Q(Q(fileproperty__property = fp) & ~Q(**kwargs))
                        else:
                            cq = Q(Q(fileproperty__property = fp) & Q(**kwargs))
                            
            # modify query set
            if op == 'or':
                queryset = queryset | self.model.objects.filter(cq)
            else:
                # if connector wasn't set, use &
                queryset = queryset.filter(cq)
        
        # UTILITY FILTER
        dup_prop = adv_fields['dup_prop']
        if dup_prop != '':
            dup_dp = DescriptiveProperty.objects.get(pk = dup_prop)
            if dup_dp.control_field:
                dups = FileControlProperty.objects.filter(control_property_id = dup_prop).values_list('file', flat = True).annotate(count = Count('control_property')).filter(count__gt = 1)
            else:
                dups = FileProperty.objects.filter(property_id = dup_prop).values_list('file', flat = True).annotate(count = Count('property')).filter(count__gt = 1)
            dups_list = list(dups) # forcing queryset evaluation so next line doesn't throw a MySQLdb error
            queryset = queryset.filter(id__in = dups_list)
          
        if col != '':
            return queryset.order_by('filecollection__order').distinct(), use_distinct
        elif queryset.ordered:
            return queryset.distinct(), use_distinct
        else:
            return queryset.order_by('-uploaded').distinct(), use_distinct

admin.site.register(File, FileAdmin)

""" COLLECTION ADMIN """    
    
class CollectionAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'owner')    
    inlines = [SubjectCollectionInline, LocationCollectionInline, MediaCollectionInline, PersonOrgCollectionInline]
    search_fields = ['title', 'notes']
    list_display = ('title', 'notes', 'created', 'modified', 'owner')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    fields = ['title', 'notes', 'created', 'modified', 'owner']
    
    change_form_template = 'admin/base/collection/change_form.html' 
    
    class Media:
        # the django-select2 styles have to be added manually for some reason, otherwise they don't work
        css = {
            "all": ("django_select2/css/select2.min.css",)
        }
        
    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.owner = request.user
        obj.save()

admin.site.register(Collection, CollectionAdmin)

""" SITE SETTINGS ETC ADMIN """    
    
class ResultPropertyAdmin(admin.ModelAdmin):
    readonly_fields = ('display_field',)
    search_fields = ['display_field', 'field_type']
    list_display = ('human_title', 'field_type')
    list_editable = ('field_type',)
    
admin.site.register(ResultProperty, ResultPropertyAdmin)

class DataUploadAdmin(admin.ModelAdmin):
    fields = ['name', 'file', 'notes', 'entity', 'imported', 'create_on_no_match', 'allow_multiple', 'collection', 'owner', 'upload_time']
    readonly_fields = ('name', 'imported', 'owner', 'upload_time')
    list_display = ['name', 'imported', 'owner', 'upload_time']
    list_filter = ['imported', 'owner', 'upload_time']
    search_fields = ['name', 'notes']
    date_hierarchy = 'upload_time'
    inlines = [ColumnInline, MatchImportErrorInline, RelationImportErrorInline, ControlFieldImportErrorInline, MiscImportErrorInline]
    actions = [import_data, rollback_import]
    form = DataUploadForm
    
    suit_form_tabs = (('step1', 'Step 1: Prepare Columns for Import'), ('step2', 'Step 2: Resolve Errors'))
    fieldsets = [
        (None, {
            'classes': ('suit-tab', 'suit-tab-step1'),
            'fields': ['name', 'file', 'notes', 'entity', 'imported', 'create_on_no_match', 'allow_multiple', 'collection', 'owner', 'upload_time']
        }),
    ]

    class Media:
        # the django-select2 styles have to be added manually for some reason, otherwise they don't work
        css = {
            "all": ("django_select2/css/select2.min.css",)
        }    
    
    def save_model(self, request, obj, form, change):
        
        # when file is uploaded, get the column headers
        if obj.pk is None:
            obj.owner = request.user
            obj.name = obj.file.title          
            obj.save()
            url = obj.file.get_download()
            response = urllib2.urlopen(url)
            reader = csv.reader(response)
            for row in reader:
                for index, cell in enumerate(row):
                    new_column = Column(data_upload = obj, title = cell.strip(), column_index = index)
                    new_column.save()
                break
        else:
            obj.name = obj.file.title           
            obj.save()
            
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, Column): #Check if it is the correct type of inline
                status = ''
                ready = True
                
                if not instance.property and not instance.linked_data and not instance.insert_as_inline and not instance.insert_as_footnote:
                    status += 'Please select a "Property" for this column or check "Insert Column as Inline Note", "Insert Column as Foot Note", or "Linked Data".'
                    ready = False
                
                if instance.matching_field or instance.matching_required:
                    if instance.insert_as_inline or instance.insert_as_footnote:
                        if status != '':
                            status += '; '
                        status += 'Column can not be both an Identifier and Note. Please select only one.'
                        instance.matching_field = False
                        instance.insert_as_inline = False
                        instance.insert_as_footnote = False
                        ready = False
                    instance.title_for_note = ''
                    if instance.relation:
                        if status != '':
                            status += '; '
                        status += 'Column can not be both an Identifier and Relation. Please select only one.'
                        instance.matching_field = False
                        instance.relation = False
                        ready = False
                    instance.rel_entity = ''
                    instance.rel_match_property = None
                
                if instance.matching_required and not instance.matching_field:
                    instance.matching_field = True
                    
                if instance.relation:
                    if instance.insert_as_inline or instance.insert_as_footnote:
                        if status != '':
                            status += '; '
                        status += 'Column not be both a Relation and Note. Please select only one.'
                        instance.relation = False
                        instance.insert_as_inline = False
                        instance.insert_as_footnote = False
                        ready = False
                    if instance.rel_entity == '':
                        if status != '':
                            status += '; '
                        status += 'If you select Relation, you must select the Related Entity.'
                        ready = False
                    if not instance.rel_match_property:
                        if status != '':
                            status += '; '
                        status += 'If you select Relation, you must select a Relation Identifier.'
                        ready = False
                        
                if (instance.rel_entity != '' or instance.rel_match_property) and not instance.relation:
                    if status != '':
                        status += '; '
                    status += 'You selected a Related Entity or Relation Identifier but did not check Relation. Please confirm this Column is a Relation.'
                    ready = False

                if instance.rel_entity == instance.data_upload.entity:
                    if status != '':
                        status += '; '
                    status += 'The Related Entity can not be the same as the parent Data Import File Entity. Please select a different Related Entity.' 
                    ready = False
                    
                if instance.linked_data and not instance.linked_data_source:
                    if status != '':
                        status += '; '
                    status += 'If you select Linked Data, you must select a Linked Data Source.'
                    ready = False             

                if status == '':
                    status = 'Column is ready for import.'
                    
                instance.import_error = status
                instance.ready_for_import = ready
                
                instance.save()

            elif isinstance(instance, MatchImportError):
                if instance.subject or instance.location or instance.media or instance.person or instance.file:
                    instance.save()
                    batch = instance.batch

                    if instance.subject:
                        match = instance.subject
                        entity = 'S'
                    elif instance.location:
                        match = instance.location
                        entity = 'L'
                    elif instance.media:
                        match = instance.media
                        entity = 'M'
                    elif instance.file:
                        match = instance.file
                        entity = 'F'
                    else:
                        match = instance.person
                        entity = 'PO'
                    url = instance.data_upload.file.get_download()
                    response = urllib2.urlopen(url)
                    reader = csv.reader(response)                    
                    for row_index, row in enumerate(reader):
                        if (row_index + 1) != instance.row:
                            continue
                        else:  

                            # have to increment row_index because CSV rows are displayed in Excel as 1 based indexing
                            # this has be accounted for later when handling the errors
                            row_index = row_index + 1
                        
                            # COLLECTION
                            if instance.data_upload.collection:
                                col = instance.data_upload.collection
                                if entity == 'S':
                                    last_order = 0
                                    col_ordered = SubjectCollection.objects.filter(collection = col).order_by('-order')
                                    if col_ordered:
                                        last_order = col_ordered[0].order + 1
                                    new_col = SubjectCollection(subject = match, collection = col, order = last_order, upload_batch = batch)
                                    new_col.save()
                                    last_order = last_order + 1
                                elif entity == 'L':
                                    last_order = 0
                                    col_ordered = LocationCollection.objects.filter(collection = col).order_by('-order')
                                    if col_ordered:
                                        last_order = col_ordered[0].order + 1                 
                                    new_col = LocationCollection(location = match, collection = col, order = last_order, upload_batch = batch)
                                    new_col.save()
                                    last_order = last_order + 1
                                elif entity == 'M':
                                    last_order = 0
                                    col_ordered = MediaCollection.objects.filter(collection = col).order_by('-order')
                                    if col_ordered:
                                        last_order = col_ordered[0].order + 1                   
                                    new_col = MediaCollection(media = match, collection = col, order = last_order, upload_batch = batch)
                                    new_col.save()
                                    last_order = last_order + 1
                                elif entity == 'F':
                                    last_order = 0
                                    col_ordered = FileCollection.objects.filter(collection = col).order_by('-order')
                                    if col_ordered:
                                        last_order = col_ordered[0].order + 1                
                                    new_col = FileCollection(file = match, collection = col, order = last_order, upload_batch = batch)
                                    new_col.save()
                                    last_order = last_order + 1
                                elif entity == 'PO':
                                    last_order = 0
                                    col_ordered = PersonOrgCollection.objects.filter(collection = col).order_by('-order')
                                    if col_ordered:
                                        last_order = col_ordered[0].order + 1                    
                                    new_col = PersonOrgCollection(personorg = match, collection = col, order = last_order, upload_batch = batch)
                                    new_col.save()
                                    last_order = last_order + 1  
                                        
                            # ITERATE THROUGH COLUMNS
                            for index, cell in enumerate(row):
                            
                                cell = cell.strip()
                                upload = instance.data_upload
                            
                                # CHECK COLUMN INDEX
                                columns = Column.objects.filter(data_upload = upload, column_index = index)
                                column_count = columns.count()
                                if not columns or column_count > 1:
                                    continue
                                else:
                                    column = columns[0]
                                    
                                    # LINKED DATA
                                    if column.linked_data:
                                        # if a source wasn't selected and it got past the checks somehow, then skip
                                        if not column.linked_data_source:
                                            continue
                                        source = column.linked_data_source
                                        if entity == 'S':
                                            sld = SubjectLinkedData(subject = match, source = source, link = cell, upload_batch = batch)
                                            sld.save()
                                        elif entity == 'M':
                                            mld = MediaLinkedData(media = match, source = source, link = cell, upload_batch = batch)
                                            mld.save
                                        elif entity == 'L':
                                            lld = LocationLinkedData(location = match, source = source, link = cell, upload_batch = batch)
                                            lld.save()
                                        elif entity == 'F':
                                            fld = FileLinkedData(file = match, source = source, link = cell, upload_batch = batch)
                                            fld.save()
                                        else:
                                            pld = PersonOrgLinkedData(personorg = match, source = source, link = cell, upload_batch = batch)
                                            pld.save()   
                                    else:                                    
                                        # DESCRIPTIVE PROPERTY
                                        dp = column.property 
                                        if column.matching_field or column.insert_as_inline or column.insert_as_footnote:
                                            continue
                                        
                                        inline = ''
                                        footnote = ''
                                        
                                        # GET ANY NOTES FOR COLUMN
                                        matching_inlines = Column.objects.filter(data_upload = upload, insert_as_inline = True, title_for_note = column.title.strip())
                                        if matching_inlines:
                                            for idx, mi in enumerate(matching_inlines):
                                                if idx > 0:
                                                    inline += '; '
                                                if len(row) >= mi.column_index:
                                                    inline += row[mi.column_index]
                                                    
                                        matching_footnotes = Column.objects.filter(data_upload = upload, insert_as_footnote = True, title_for_note = column.title.strip())
                                        if matching_footnotes:
                                            for idx, mf in enumerate(matching_footnotes):
                                                if idx > 0:
                                                    footnote += '; '
                                                if len(row) >= mf.column_index:
                                                    footnote += row[mf.column_index]
                                                    
                                        rel_note = inline
                                        if inline != '' and footnote != '':
                                            rel_note += '; '
                                        rel_note += footnote
                                        
                                        # HANDLE RELATIONS
                                        if column.relation:
                                            if column.rel_entity == 'S':
                                                if column.rel_match_property.control_field:
                                                    rels = Subject.objects.filter(subjectcontrolproperty__control_property = column.rel_match_property, subjectcontrolproperty__control_property_value__title = cell)
                                                else:
                                                    rels = Subject.objects.filter(subjectproperty__property = column.rel_match_property, subjectproperty__property_value = cell)
                                            elif column.rel_entity == 'L':
                                                if column.rel_match_property.control_field:
                                                    rels = Location.objects.filter(locationcontrolproperty__control_property = column.rel_match_property, locationcontrolproperty__control_property_value__title = cell)
                                                else:
                                                    rels = Location.objects.filter(locationproperty__property = column.rel_match_property, locationproperty__property_value = cell)
                                            elif column.rel_entity == 'M':
                                                if column.rel_match_property.control_field:
                                                    rels = Media.objects.filter(mediacontrolproperty__control_property = column.rel_match_property, mediacontrolproperty__control_property_value__title = cell)
                                                else:
                                                    rels = Media.objects.filter(mediaproperty__property = column.rel_match_property, mediaproperty__property_value = cell)
                                            elif column.rel_entity == 'F':
                                                if column.rel_match_property.control_field:
                                                    rels = File.objects.filter(filecontrolproperty__control_property = column.rel_match_property, filecontrolproperty__control_property_value__title = cell)
                                                else:
                                                    rels = File.objects.filter(fileproperty__property = column.rel_match_property, fileproperty__property_value = cell)
                                            else:
                                                if column.rel_match_property.control_field:
                                                    rels = PersonOrg.objects.filter(personorgcontrolproperty__control_property = column.rel_match_property, personorgcontrolproperty__control_property_value__title = cell)
                                                else:
                                                    rels = PersonOrg.objects.filter(personorgproperty__property = column.rel_match_property, personorgproperty__property_value = cell)
                                            
                                            rel_count = rels.count()
                                            if not rels:
                                                if entity == 'S':
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, subjects = match, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)
                                                elif entity == 'L':
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, locations = match, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)
                                                elif entity == 'M':
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, medias = match, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)
                                                elif entity == 'F':
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, files = match, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)
                                                else:
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, people = match, batch = batch, error_text = "No entity found matching " + column.rel_match_property + " : " + cell)      
                                                relation_error.save()
                                                continue
                                            elif rel_count > 1:
                                                if entity == 'S':
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, subjects = match, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)
                                                elif entity == 'L':
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, locations = match, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)
                                                elif entity == 'M':
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, medias = match, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)
                                                elif entity == 'F':
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, files = match, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)
                                                else:
                                                    relation_error = RelationImportError(data_upload = upload, row = row_index, column = column, people = match, batch = batch, error_text = "Multiple entities found matching " + column.rel_match_property + " : " + cell)  
                                                relation_error.save()
                                                continue
                                            else:
                                                if entity == 'S':
                                                    if column.rel_entity == 'L':
                                                        lsr = LocationSubjectRelations(location = rels[0], subject = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        lsr.save()
                                                    elif column.rel_entity == 'M':
                                                        msr = MediaSubjectRelations(media = rels[0], subject = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        msr.save()
                                                    elif column.rel_entity == 'F':
                                                        sf = SubjectFile(subject = match, rsid = rels[0], upload_batch = batch)
                                                        sf.save()
                                                    elif column.rel_entity == 'PO':
                                                        posr = SubjectPersonOrgRelations(person_org = rels[0], subject = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        posr.save()
                                                elif entity == 'L':
                                                    if column.rel_entity == 'S':
                                                        lsr = LocationSubjectRelations(subject = rels[0], location = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        lsr.save()
                                                    elif column.rel_entity == 'M':
                                                        mlr = MediaLocationRelations(media = rels[0], location = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        mlr.save()
                                                    elif column.rel_entity == 'F':
                                                        lf = LocationFile(location = match, rsid = rels[0], upload_batch = batch)
                                                        lf.save()
                                                    elif column.rel_entity == 'PO':
                                                        polr = LocationPersonOrgRelations(person_org = rels[0], location = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        polr.save()
                                                elif entity == 'M':
                                                    if column.rel_entity == 'S':
                                                        msr = MediaSubjectRelations(subject = rels[0], media = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        msr.save()
                                                    elif column.rel_entity == 'L':
                                                        mlr = MediaLocationRelations(location = rels[0], media = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        mlr.save()
                                                    elif column.rel_entity == 'F':
                                                        mf = MediaFile(media = match, rsid = rels[0], upload_batch = batch)
                                                        mf.save()
                                                    elif column.rel_entity == 'PO':
                                                        pomr = MediaPersonOrgRelations(person_org = rels[0], media = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        pomr.save()
                                                elif entity == 'F':
                                                    if column.rel_entity == 'S':
                                                        sf = SubjectFile(subject = rels[0], rsid = match, upload_batch = batch)
                                                        sf.save()
                                                    elif column.rel_entity == 'L':
                                                        lf = LocationFile(location = rels[0], rsid = match, upload_batch = batch)
                                                        lf.save()
                                                    elif column.rel_entity == 'M':
                                                        mf = MediaFile(media = rels[0], rsid = match, upload_batch = batch)
                                                        mf.save() 
                                                    elif column.rel_entity == 'PO':
                                                        pof = PersonOrgFile(person_org = rels[0], rsid = match, upload_batch = batch)
                                                        pof.save()
                                                elif entity == 'PO':
                                                    if column.rel_entity == 'S':
                                                        posr = SubjectPersonOrgRelations(subject = rels[0], person_org = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        posr.save()
                                                    elif column.rel_entity == 'L':
                                                        polr = LocationPersonOrgRelations(location = rels[0], person_org = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        polr.save()
                                                    elif column.rel_entity == 'M':
                                                        pomr = MediaPersonOrgRelations(media = rels[0], person_org = match, notes = rel_note, last_mod_by = request.user, upload_batch = batch)
                                                        pomr.save()
                                                    elif column.rel_entity == 'F':
                                                        pof = PersonOrgFile(person_org = match, rsid = rels[0], upload_batch = batch)
                                                        pof.save()
                                                        
                                        # HANDLE CONTROL FIELDS
                                        elif dp.control_field:
                                            cf = ControlField.objects.filter(title = cell, type = dp)
                                            if cf:
                                                if entity == 'S':
                                                    scp = SubjectControlProperty(subject = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                    scp.save()
                                                elif entity == 'L':
                                                    lcp = LocationControlProperty(location = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                    lcp.save()
                                                elif entity == 'M':
                                                    mcp = MediaControlProperty(media = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                    mcp.save()
                                                elif entity == 'F':
                                                    fcp = FileControlProperty(file = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                    fcp.save()
                                                elif entity == 'PO':
                                                    pocp = PersonOrgControlProperty(person_org = match, control_property = dp, control_property_value = cf[0], notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                    pocp.save()
                                            else:
                                                if entity == 'S':
                                                    cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, subjects = match, batch = batch)
                                                elif entity == 'L':
                                                    cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, locations = match, batch = batch)
                                                elif entity == 'M':
                                                    cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, media = match, batch = batch)
                                                elif entity == 'F':
                                                    cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, files = match, batch = batch)
                                                else:
                                                    cf_error = ControlFieldImportError(data_upload = upload, row = row_index, column = column, error_text = 'Could not find Controlled Term match for ' + dp.property + ' : ' + cell, people = match, batch = batch)
                                                cf_error.save()
                                                
                                        # HANDLE FREE FORM PROPERTY
                                        else:
                                            if entity == 'S':
                                                sp = SubjectProperty(subject = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                sp.save()
                                            elif entity == 'L':
                                                lp = LocationProperty(location = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                lp.save()
                                            elif entity == 'M':
                                                mp = MediaProperty(media = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                mp.save()
                                            elif entity == 'F':
                                                fp = FileProperty(file = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                fp.save()
                                            elif entity == 'PO':
                                                pop = PersonOrgProperty(person_org = match, property = dp, property_value = cell, notes = footnote, inline_notes = inline, last_mod_by = request.user, upload_batch = batch)
                                                pop.save()
                    instance.delete()
                else:
                    instance.save()

            elif isinstance(instance, RelationImportError):
                if instance.subject or instance.location or instance.media or instance.person or instance.file:
                    instance.save()
                    batch = instance.batch
                    
                    if instance.subject:
                        rel_match = instance.subject
                        rel_entity = 'S'
                    elif instance.location:
                        rel_match = instance.location
                        rel_entity = 'L'
                    elif instance.media:
                        rel_match = instance.media
                        rel_entity = 'M'
                    elif instance.file:
                        rel_match = instance.file
                        rel_entity = 'F'                        
                    else:
                        rel_match = instance.person
                        rel_entity = 'PO'
                        
                    if instance.subjects:
                        matches = instance.subjects
                        entity = 'S'                        
                    elif instance.locations:
                        matches = instance.locations
                        entity = 'L'                        
                    elif instance.medias:
                        matches = instance.medias
                        entity = 'M'
                    elif instance.files:
                        matches = instance.files
                        entity = 'F'                        
                    else:
                        matches = instance.people
                        entity = 'PO'                          
                    
                    # HANDLE RELATIONS
                    
                    if entity == 'S':
                        if rel_entity == 'L':
                            for match in matches:
                                lsr = LocationSubjectRelations(location = rel_match, subject = match, last_mod_by = request.user, upload_batch = batch)
                                lsr.save()
                        elif rel_entity == 'M':
                            for match in matches:
                                msr = MediaSubjectRelations(media = rel_match, subject = match, last_mod_by = request.user, upload_batch = batch)
                                msr.save()
                        elif rel_entity == 'F':
                            for match in matches:
                                sf = SubjectFile(subject = match, rsid = rel_match, upload_batch = batch)
                                sf.save()                                
                        elif rel_entity == 'PO':
                            for match in matches:
                                posr = SubjectPersonOrgRelations(person_org = rel_match, subject = match, last_mod_by = request.user, upload_batch = batch)
                                posr.save()
                    elif entity == 'L':
                        if rel_entity == 'S':
                            for match in matches:
                                lsr = LocationSubjectRelations(subject = rel_match, location = match, last_mod_by = request.user, upload_batch = batch)
                                lsr.save()
                        elif rel_entity == 'M':
                            for match in matches:
                                mlr = MediaLocationRelations(media = rel_match, location = match, last_mod_by = request.user, upload_batch = batch)
                                mlr.save()
                        elif rel_entity == 'F':
                            for match in matches:
                                lf = LocationFile(location = match, rsid = rel_match, upload_batch = batch)
                                lf.save()
                        elif rel_entity == 'PO':
                            for match in matches:
                                polr = LocationPersonOrgRelations(person_org = rel_match, location = match, last_mod_by = request.user, upload_batch = batch)
                                polr.save()
                    elif entity == 'M':
                        if rel_entity == 'S':
                            for match in matches:
                                msr = MediaSubjectRelations(subject = rel_match, media = match, last_mod_by = request.user, upload_batch = batch)
                                msr.save()
                        elif rel_entity == 'L':
                            for match in matches:
                                mlr = MediaLocationRelations(location = rel_match, media = match, last_mod_by = request.user, upload_batch = batch)
                                mlr.save()
                        elif rel_entity == 'F':
                            for match in matches:
                                mf = MediaFile(media = match, rsid = rel_match, upload_batch = batch)
                                mf.save()
                        elif rel_entity == 'PO':
                            for match in matches:
                                pomr = MediaPersonOrgRelations(person_org = rel_match, media = match, last_mod_by = request.user, upload_batch = batch)
                                pomr.save()
                    elif entity == 'F':
                        if rel_entity == 'S':
                            for match in matches:
                                sf = SubjectFile(subject = rel_match, rsid = match, upload_batch = batch)
                                sf.save()
                        elif rel_entity == 'L':
                            for match in matches:
                                lf = LocationFile(location = rel_match, rsid = match, upload_batch = batch)
                                lf.save()
                        elif rel_entity == 'M':
                            for match in matches:
                                mf = MediaFile(media = rel_match, rsid = match, upload_batch = batch)
                                mf.save() 
                        elif rel_entity == 'PO':
                            for match in matches:
                                pof = PersonOrgFile(person_org = rel_match, rsid = match, upload_batch = batch)
                                pof.save()
                    elif entity == 'PO':
                        if rel_entity == 'S':
                            for match in matches:
                                posr = SubjectPersonOrgRelations(subject = rel_match, person_org = match, last_mod_by = request.user, upload_batch = batch)
                                posr.save()
                        elif rel_entity == 'L':
                            for match in matches:
                                polr = LocationPersonOrgRelations(location = rel_match, person_org = match, last_mod_by = request.user, upload_batch = batch)
                                polr.save()
                        elif rel_entity == 'M':
                            for match in matches:
                                pomr = MediaPersonOrgRelations(media = rel_match, person_org = match, last_mod_by = request.user, upload_batch = batch)
                                pomr.save()
                        elif rel_entity == 'F':
                            for match in matches:
                                pof = PersonOrgFile(person_org = match, rsid = rel_match, upload_batch = batch)
                                pof.save()                                
                    instance.delete()
                else:
                    instance.save()
                        
            elif isinstance(instance, ControlFieldImportError):
                if instance.control_field:
                    instance.save()
                    batch = instance.batch
                        
                    if instance.subjects:
                        matches = instance.subjects
                        entity = 'S'                        
                    elif instance.locations:
                        matches = instance.locations
                        entity = 'L'                        
                    elif instance.medias:
                        matches = instance.medias
                        entity = 'M'
                    elif instance.files:
                        matches = instance.files
                        entity = 'F'
                    else:
                        matches = instance.people
                        entity = 'PO'                        
                            
                    column = instance.column
                    dp = column.property

                    # HANDLE CONTROL FIELDS
                    cf = instance.control_field
                    if entity == 'S':
                        for match in matches:
                            scp = SubjectControlProperty(subject = match, control_property = dp, control_property_value = cf, last_mod_by = request.user, upload_batch = batch)
                            scp.save()
                    elif entity == 'L':
                        for match in matches:
                            lcp = LocationControlProperty(location = match, control_property = dp, control_property_value = cf, last_mod_by = request.user, upload_batch = batch)
                            lcp.save()
                    elif entity == 'M':
                        for match in matches:
                            mcp = MediaControlProperty(media = match, control_property = dp, control_property_value = cf, last_mod_by = request.user, upload_batch = batch)
                            mcp.save()
                    elif entity == 'F':
                        for match in matches:
                            fcp = FileControlProperty(file = match, control_property = dp, control_property_value = cf, last_mod_by = request.user, upload_batch = batch)
                            fcp.save()                            
                    elif entity == 'PO':
                        for match in matches:
                            pocp = PersonOrgControlProperty(person_org = match, control_property = dp, control_property_value = cf, last_mod_by = request.user, upload_batch = batch)
                            pocp.save()                   

                    instance.delete()
                else:
                    instance.save()
                        
admin.site.register(DataUpload, DataUploadAdmin)

class StatusFilter(admin.SimpleListFilter):

    title = 'Status'
    
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        properties = tuple((prop.id, prop.property) for prop in DescriptiveProperty.objects.all())    
        return properties

    def queryset(self, request, queryset):
        if self.value():
            prop_id = self.value()
            return queryset.filter(subjectproperty__property = prop_id)

class SubjectPropertyInline(admin.TabularInline):
    model = SubjectProperty
    fields = ['property', 'property_value', 'inline_notes', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    ordering = ('property__order',)
    suit_classes = 'suit-tab suit-tab-general'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'property':
            if request.user == User.objects.get(pk=7) or request.user == User.objects.get(pk=17):
                kwargs["queryset"] = DescriptiveProperty.objects.filter(pk=145)
            else:
                kwargs["queryset"] = DescriptiveProperty.objects.filter(Q(primary_type='SO') | Q(primary_type='AL') | Q(primary_type='SL')).exclude(control_field = True)
        return super(SubjectPropertyInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
    def queryset(self, request):   
        qs = super(SubjectPropertyInline, self).queryset(request)
        if request.user == User.objects.get(pk=7) or request.user == User.objects.get(pk=17):
            qs = qs.filter(property_id = 145)
        return qs
        
class MediaSubjectRelationsInline(admin.TabularInline):
    model = MediaSubjectRelations
    fields = ['media', 'relation_type', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)        
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_classes = 'suit-tab suit-tab-general'
    extra = 1
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'media':
            kwargs["queryset"] = Media.objects.filter(type__type = 'publication').order_by('title')
        elif db_field.name == 'relation_type':
            kwargs["queryset"] = Relations.objects.filter(Q(pk=2) | Q(pk=5))
        return super(MediaSubjectRelationsInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
    def get_queryset(self, request):
        qs = super(MediaSubjectRelationsInline, self).get_queryset(request)
        return qs.filter(Q(relation_type=2) | Q(relation_type=5))

class LocationTreeChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        level = obj.level
        padding = ''
        while (level > 0):
            padding = padding + '+--'
            level = level - 1
        return padding + obj.title
        
class LocationRelationAdminForm(ModelForm):
    location = LocationChoices(
        label = Location._meta.verbose_name.capitalize(),
        widget = AutoHeavySelect2Widget(
            select2_options = {
                'width': '220px',
                'placeholder': 'Lookup %s ...' % Location._meta.verbose_name
            }
        )
    )
    
    class Meta:
          model = LocationSubjectRelations
        
class LocationSubjectRelationsInline(admin.TabularInline):
    model = LocationSubjectRelations
    fields = ['location', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)        
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_classes = 'suit-tab suit-tab-general'
    extra = 1
    form = LocationRelationAdminForm 
        
class FileInline(admin.TabularInline):
    model = SubjectFile
    fields = ['get_thumbnail_admin', 'rsid', 'thumbnail']
    readonly_fields = ('get_thumbnail_admin',)        
    suit_classes = 'suit-tab suit-tab-files'
    form = FileForm
        
class SubjectAdmin(admin.ModelAdmin):
    readonly_fields = ('title', 'created', 'modified', 'last_mod_by')    
    inlines = [SubjectPropertyInline, SubjectControlPropertyInline, MediaSubjectRelationsInline, LocationSubjectRelationsInline, SubjectCollectionEntityInline, FileInline]
    search_fields = ['title', 'title1', 'title2', 'title3', 'desc1', 'desc2', 'desc3']
    list_display = ('title1', 'title2', 'title3', 'desc1', 'desc2', 'desc3', 'created', 'modified')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    suit_form_tabs = (('general', 'General'), ('files', 'Files'))
    fieldsets = [
        (None, {
            'classes': ('suit-tab', 'suit-tab-general'),
            'fields': ['title', 'notes', 'created', 'modified', 'last_mod_by']
        }),
    ]
    advanced_search_form = AdminAdvSearchForm()
    actions = ['export_csv']
    save_as = True
    
    change_list_template = 'admin/base/subject/change_list.html'
    change_form_template = 'admin/base/subject/change_form.html'
    
    class Media:
        # the django-select2 styles have to be added manually for some reason, otherwise they don't work
        css = {
            "all": ("django_select2/css/select2.min.css",)
        }
        
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """ Added to allow browsing by collection """
    
        extra_context = extra_context or {}
        collections = SubjectCollection.objects.filter(subject_id = object_id)
        collection_list = []
        for coll in collections:
            coll_info = {}
            current_order = coll.order
            lt = SubjectCollection.objects.filter(collection = coll.collection, order__lt = current_order).order_by('-order')
            if lt:
                coll_info['prev'] = lt[0].subject_id
            gt = SubjectCollection.objects.filter(collection = coll.collection, order__gt = current_order).order_by('order')
            if gt:
                coll_info['next'] = gt[0].subject_id
            if lt or gt:
                coll_info['name'] = coll.collection.title
            collection_list.append(coll_info)
        extra_context['collections'] = collection_list
        return super(SubjectAdmin, self).change_view(request, object_id, form_url, extra_context = extra_context)
        
    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        if request.POST.has_key("_viewnext"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            next = request.POST.get("next_id")
            if next:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % next)
        if request.POST.has_key("_viewprev"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            prev = request.POST.get("prev_id")
            if prev:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % prev)
        return super(SubjectAdmin, self).response_change(request, obj)        
        
    def bulk_update(self, request, queryset):
        """ Redirects to a bulk update form """
        
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect("/bulk_update_subject/?ids=%s" % ",".join(selected))
        
    def export_csv(self, request, queryset):
        """ Temporary export solution while models are redesigned 
        
        This is horribly hackish. If it isn't fixed by Dec 2015..... burn it all"""
        response = HttpResponse(content_type='text/csv')
        filename_str = '"admin_search_results_' + datetime.now().strftime("%Y.%m.%d_%H.%M.%S") + '.csv"'
        response['Content-Disposition'] = 'attachment; filename=' + filename_str
        
        writer = csv.writer(response)
        titles = []
        rows = []
        for result in queryset:
            row = []
            row_dict = {}
            control_properties = result.subjectcontrolproperty_set.all()
            properties = result.subjectproperty_set.all()
            for each_prop in properties:
                prop_name = each_prop.property.property
                prop_value = each_prop.property_value
                if not (prop_name in titles):
                    column_index = len(titles)                        
                    titles.append(prop_name)
                else:
                    column_index = titles.index(prop_name)
                    if column_index in row_dict:
                        prop_value = row_dict[column_index] + '; ' + prop_value
                row_dict[column_index] = prop_value
            for each_prop in control_properties:
                prop_name = each_prop.control_property.property
                prop_value = each_prop.control_property_value.title
                if not (prop_name in titles):
                    column_index = len(titles)   
                    titles.append(prop_name)
                else:
                    column_index = titles.index(prop_name)
                    if column_index in row_dict:
                        prop_value = row_dict[column_index] + '; ' + prop_value
                row_dict[column_index] = prop_value
            for i in range(len(titles)):
                if i in row_dict:
                    row.append(row_dict[i])
                else:
                    row.append('')
                    
            rows.append(row)

        writer.writerow(titles)
        for each_row in rows:
            writer.writerow([unicode(s).encode("utf-8") for s in each_row])
        return response
        
    export_csv.short_description = "Export current search results to CSV"
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, SubjectProperty):
            
                # automatically adding museum control field value if museum number is entered
                prop_id = instance.property_id
                existing_museum = SubjectControlProperty.objects.filter(subject_id = instance.subject_id, control_property_id = 59)
                nums = []
                warning = 'You have added/updated/deleted a Museum Number. If a new type of museum number was added, the system has automatically updated the controlled Museum field. HOWEVER, the system does NOT delete existing Museum fields. If you are concerned, please double check that the Museum field for this object is correct.'
                if existing_museum:
                    for item in existing_museum:
                        nums.append(item.control_property_value_id)
                if (prop_id == 31 or prop_id == 33 or prop_id == 45 or prop_id == 43) and (401 not in nums):
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=401), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)
                elif prop_id == 32 and 402 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=402), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)                    
                elif (prop_id == 34 or prop_id == 36 or prop_id == 44) and (398 not in nums):
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=398), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)                    
                elif prop_id == 35 and 403 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=403), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)                    
                elif prop_id == 38 and 404 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=404), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)                    
                elif prop_id == 40 and 405 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=405), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)                    
                elif prop_id == 42 and 406 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=406), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)                    
                elif prop_id == 73 and 407 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=407), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)
                elif prop_id == 128 and 435 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=435), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)
                elif prop_id == 129 and 447 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=447), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)   
                elif prop_id == 130 and 448 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=448), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)   
                elif prop_id == 131 and 449 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=449), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)   
                elif prop_id == 132 and 450 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=450), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)   
                elif prop_id == 133 and 451 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=451), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)
                elif prop_id == 146 and 771 not in nums:
                    m = SubjectControlProperty(subject = instance.subject, control_property = DescriptiveProperty.objects.get(pk=59), control_property_value = ControlField.objects.get(pk=771), last_mod_by = request.user)
                    m.save()
                    messages.add_message(request, messages.WARNING, warning)                     
                
                instance.last_mod_by = request.user            
                instance.save()            

            if isinstance (instance, SubjectControlProperty):
                instance.last_mod_by = request.user            
                instance.save()
                
            if isinstance(instance, MediaSubjectRelations):
                instance.last_mod_by = request.user
                if isinstance(instance, File):
                    instance.relation_type = Relations.objects.get(pk=3)
                instance.save()

            if isinstance (instance, LocationSubjectRelations):
                instance.relation_type = Relations.objects.get(pk=4)
                instance.last_mod_by = request.user            
                instance.save() 

            if isinstance (instance, SubjectCollection):
                instance.save()
            
    # advanced search form based on https://djangosnippets.org/snippets/2322/ and http://stackoverflow.com/questions/8494200/django-admin-custom-change-list-arguments-override-e-1 

    def get_changelist(self, request, **kwargs):
        adv_search_fields = {}
        asf = self.advanced_search_form
        for key in asf.fields.keys():
            temp = self.other_search_fields.get(key, None)
            if temp:
                adv_search_fields[key] = temp[0]
            else:
                adv_search_fields[key] = ''
        
        class AdvChangeList(ChangeList):
            
            def get_query_string(self, new_params=None, remove=None):
                """ Overriding get_query_string ensures that the admin still considers
                the additional search fields as parameters, even tho they are popped from 
                the request.GET """
                
                if new_params is None:
                    new_params = {}
                if remove is None:
                    remove = []
                p = self.params.copy()
                for r in remove:
                    for k in list(p):
                        if k.startswith(r):
                            del p[k]
                for k, v in new_params.items():
                    if v is None:
                        if k in p:
                            del p[k]
                    else:
                        p[k] = v
                
                extra_params = ''
                for field, val in adv_search_fields.items():
                    extra_params += '&' + field + '=' + val
                
                return '?%s%s' % (urlencode(sorted(p.items())), extra_params)
                
        return AdvChangeList
        
    def lookup_allowed(self, key, value):
        if key in self.advanced_search_form.fields.keys():
            return True
        if key == 'attach_type':
            return True
        return super(SubjectAdmin, self).lookup_allowed(key, value)
        
    def changelist_view(self, request, extra_context=None, **kwargs):
        self.other_search_fields = {}
        asf = self.advanced_search_form
        extra_context = {'asf': asf}
        
        request.GET._mutable = True
        
        for key in asf.fields.keys():
            try:
                temp = request.GET.pop(key)
            except KeyError:
                pass
            else:
                if temp != ['']:
                    self.other_search_fields[key] = temp
                    
        request.GET._mutable = False
        return super(SubjectAdmin, self).changelist_view(request, extra_context = extra_context)
        
    def get_search_results(self, request, queryset, search_term):
        """ Performs either a simple search using the search_term or an 
        advanced search using values taken from the AdvancedSearchForm """
        
        queryset, use_distinct = super(SubjectAdmin, self).get_search_results(request, queryset, search_term)
        
        # get all the fields from the adv search form
        adv_fields = {}
        asf = self.advanced_search_form
        for key in asf.fields.keys():
            temp = self.other_search_fields.get(key, None)
            if temp:
                adv_fields[key] = temp[0]
            else:
                adv_fields[key] = ''
        
        # NOTE: simple search has already been applied
        
        # RELATED TABLES FILTER
        loc = adv_fields['loc']
        if loc != '':
            queryset = queryset.filter(locationsubjectrelations__location_id=loc)
            
        img = adv_fields['img']
        if img != 'default':
            if img == 'yes':
                queryset = queryset.filter(subjectfile__isnull = False)
            else:
                queryset = queryset.exclude(subjectfile__isnull = True)
                
        pub = adv_fields['pub']
        if pub != '':
            queryset = queryset.filter(mediasubjectrelations__media=pub)
            
        last_mod = adv_fields['last_mod']
        if last_mod != '':
            queryset = queryset.filter(last_mod_by = last_mod)

        col = adv_fields['col']
        if col != '':
            queryset = queryset.filter(subjectcollection__collection_id = col)
        
        # CONTROL PROPERTY FILTER
        for i in range(1, 4):
            cp = adv_fields['cp' + str(i)]
            cst = adv_fields['cst' + str(i)]
            cv = adv_fields['cv' + str(i)]
            
            if cp != '' and cv != 'default':
                cf = ControlField.objects.filter(pk = cv)
                cf_desc = cf[0].get_descendants(include_self=True)
                ccq = Q()
                for field in cf_desc:
                    if cst == 'exact':
                        ccq |= Q(subjectcontrolproperty__control_property_value = field.id)
                    else:
                        ccq &= ~Q(subjectcontrolproperty__control_property_value = field.id)
                        
                queryset = queryset.filter(ccq)
                
        # FREE FORM PROPERTY FILTER
        for i in range (1, 4):
            if i != 1:
                op = adv_fields['op' + str(i - 1)]
            else:
                op = ''
            fp = adv_fields['fp' + str(i)]
            fst = adv_fields['fst' + str(i)]
            fv = adv_fields['fv' + str(i)]

            negate = False # whether or not the query will be negated
            kwargs = {}
            cq = Q()
            
            # remove and save negation, if present
            if fst.startswith('not'):
                negate = True
                fst = fst[4:]
            
            if not(fv == '' and fst != 'blank'):
                
                if fst == 'blank':
                    #if property is Any, then skip all b/c query asks for doc with 'any' blank properties
                    if fp == '':
                        continue
                
                    # BLANK is a special case negation (essentially a double negative), so handle differently
                    if negate:
                        cq = Q(subjectproperty__property = fp)
                    else:
                        cq = ~Q(subjectproperty__property = fp)
                        
                else:
                    kwargs = {str('subjectproperty__property_value__%s' % fst) : str('%s' % fv)}
                    
                    # check if a property was selected and build the current query
                    if fp == '':
                        # if no property selected, than search thru ALL properties
                        if negate:
                            cq = ~Q(**kwargs)
                        else:
                            cq = Q(**kwargs)
                    else:
                        if negate:
                            cq = Q(Q(subjectproperty__property = fp) & ~Q(**kwargs))
                        else:
                            cq = Q(Q(subjectproperty__property = fp) & Q(**kwargs))
                            
            # modify query set
            if op == 'or':
                queryset = queryset | self.model.objects.filter(cq)
            else:
                # if connector wasn't set, use &
                queryset = queryset.filter(cq)
        
        # UTILITY FILTER
        dup_prop = adv_fields['dup_prop']
        if dup_prop != '':
            dups = SubjectProperty.objects.filter(property_id = dup_prop).values_list('subject', flat = True).annotate(count = Count('property')).filter(count__gt = 1)
            dups_list = list(dups) # forcing queryset evaluation so next line doesn't throw a MySQLdb error
            queryset = queryset.filter(id__in = dups_list)
          
        if col != '':
            return queryset.order_by('subjectcollection__order').distinct(), use_distinct
        elif queryset.ordered:
            return queryset.distinct(), use_distinct
        else:
            return queryset.order_by('-modified').distinct(), use_distinct

admin.site.register(Subject, SubjectAdmin)

class MediaPropertyInline(admin.TabularInline):
    model = MediaProperty
    fields = ['property', 'property_value', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    
    def queryset(self, request):
        qs = super(MediaPropertyInline, self).queryset(request)
        return qs.filter(Q(property__primary_type='MP') | Q(property__primary_type='AL'))    
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "property":
            kwargs["queryset"] = DescriptiveProperty.objects.filter(Q(primary_type='MP') | Q(primary_type='AL'))
        return super(MediaPropertyInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class MediaCollectionInline(admin.TabularInline):
    model = MediaCollection
    fields = ['collection', 'notes', 'order']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    extra = 1
    
class LegrainImagesInline(admin.StackedInline):
    model = LegrainImages
    fields = ['image_category', 'image_sub_category', 'image_description', 'done', 'last_mod_by']
    readonly_fields = ('last_mod_by',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    extra = 1
    max_num = 1
    
class LegrainNoteCardsInline(admin.StackedInline):
    model = LegrainNoteCards
    fields = ['field_number', 'context', 'catalogue_number', 'museum_number', 'field_photo_number', 'measurements', 'transcription', 'category', 'photo', 'drawing', 'done', 'last_mod_by']
    readonly_fields = ('last_mod_by',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    extra = 1
    max_num = 1
        
class LegrainImageTagAdminForm(ModelForm):
    tag = TreeNodeChoiceField(queryset=ControlField.objects.filter(type_id = 154))   

class LegrainImageTagsInline(admin.TabularInline):
    model = LegrainImageTags
    fields = ['tag', 'last_mod_by']
    readonly_fields = ('last_mod_by',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    form = LegrainImageTagAdminForm

class MediaAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['title', 'type', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['title', 'type', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    inlines = [MediaPropertyInline, MediaCollectionEntityInline]
    search_fields = ['title', 'notes']
    change_form_template = 'admin/base/media/change_form_media.html'
    suit_form_includes = (
        ('admin/base/media_img_display.html', 'middle'),
    )
    list_filter = (MediaCollectionListFilter,)
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, MediaProperty):
                instance.last_mod_by = request.user            
                instance.save()
            elif isinstance(instance, MediaCollection):
                instance.save()
                
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['rs_refs'] = MediaProperty.objects.filter(property_id = 94, media_id = object_id)
        collections = MediaCollection.objects.filter(media_id = object_id)
        collection_list = []
        for coll in collections:
            coll_info = {}
            current_order = coll.order
            lt = MediaCollection.objects.filter(collection = coll.collection, order__lt = current_order).order_by('-order')
            if lt:
                coll_info['prev'] = lt[0].media_id
            gt = MediaCollection.objects.filter(collection = coll.collection, order__gt = current_order).order_by('order')
            if gt:
                coll_info['next'] = gt[0].media_id
            if lt or gt:
                coll_info['name'] = coll.collection.title
            collection_list.append(coll_info)
        extra_context['collections'] = collection_list
        return super(MediaAdmin, self).change_view(request, object_id, form_url, extra_context = extra_context)
        
    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        if request.POST.has_key("_viewnext"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            next = request.POST.get("next_id")
            if next:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % next)
        if request.POST.has_key("_viewprev"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            prev = request.POST.get("prev_id")
            if prev:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % prev)
        return super(MediaAdmin, self).response_change(request, obj)         
    
admin.site.register(Media, MediaAdmin)

class LegrainImageAdmin(admin.ModelAdmin):
    readonly_fields = ('title', 'type', 'notes', 'created', 'modified', 'last_mod_by')
    fields = ['title', 'type', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['title', 'type', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    inlines = [LegrainImagesInline, LegrainImageTagsInline]
    search_fields = ['title', 'notes']
    change_form_template = 'admin/base/media/change_form_media.html'
    suit_form_includes = (
        ('admin/base/media_img_display.html', 'middle'),
    )
    list_filter = (LegrainDoneListFilter,)
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, LegrainImages) or isinstance(instance, LegrainImageTags):
                instance.last_mod_by = request.user            
                instance.save()
                
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['rs_refs'] = MediaProperty.objects.filter(property_id = 94, media_id = object_id)
        collections = MediaCollection.objects.filter(media_id = object_id)
        collection_list = []
        for coll in collections:
            coll_info = {}
            current_order = coll.order
            lt = MediaCollection.objects.filter(collection = coll.collection, order__lt = current_order).order_by('-order')
            if lt:
                coll_info['prev'] = lt[0].media_id
            gt = MediaCollection.objects.filter(collection = coll.collection, order__gt = current_order).order_by('order')
            if gt:
                coll_info['next'] = gt[0].media_id
            if lt or gt:
                coll_info['name'] = coll.collection.title
            collection_list.append(coll_info)
        extra_context['collections'] = collection_list
        return super(LegrainImageAdmin, self).change_view(request, object_id, form_url, extra_context = extra_context)
        
    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        if request.POST.has_key("_viewnext"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            next = request.POST.get("next_id")
            if next:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % next)
        if request.POST.has_key("_viewprev"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            prev = request.POST.get("prev_id")
            if prev:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % prev)                
        return super(LegrainImageAdmin, self).response_change(request, obj)         
    
admin.site.register(LegrainImage, LegrainImageAdmin)

class LegrainNotesAdmin(admin.ModelAdmin):
    readonly_fields = ('title', 'type', 'notes', 'created', 'modified', 'last_mod_by')
    fields = ['title', 'type', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['title', 'type', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    inlines = [LegrainNoteCardsInline]
    search_fields = ['title', 'notes']
    change_form_template = 'admin/base/media/change_form_media.html'
    suit_form_includes = (
        ('admin/base/media_img_display.html', 'middle'),
    )
    list_filter = (LegrainDoneListFilter,)
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, LegrainNoteCards):
                instance.last_mod_by = request.user            
                instance.save()
                
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['rs_refs'] = MediaProperty.objects.filter(property_id = 94, media_id = object_id)
        collections = MediaCollection.objects.filter(media_id = object_id)
        collection_list = []
        for coll in collections:
            coll_info = {}
            current_order = coll.order
            lt = MediaCollection.objects.filter(collection = coll.collection, order__lt = current_order).order_by('-order')
            if lt:
                coll_info['prev'] = lt[0].media_id
            gt = MediaCollection.objects.filter(collection = coll.collection, order__gt = current_order).order_by('order')
            if gt:
                coll_info['next'] = gt[0].media_id
            if lt or gt:
                coll_info['name'] = coll.collection.title
            collection_list.append(coll_info)
        extra_context['collections'] = collection_list
        return super(LegrainNotesAdmin, self).change_view(request, object_id, form_url, extra_context = extra_context)
        
    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        if request.POST.has_key("_viewnext"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            next = request.POST.get("next_id")
            if next:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % next)
        if request.POST.has_key("_viewprev"):
            msg = (_('The %(name)s "%(obj)s" was changed successfully.') %
                   {'name': force_unicode(obj._meta.verbose_name),
                    'obj': force_unicode(obj)})
            prev = request.POST.get("prev_id")
            if prev:
                self.message_user(request, msg)
                return HttpResponseRedirect("../%s/" % prev)               
        return super(LegrainNotesAdmin, self).response_change(request, obj)        
    
admin.site.register(LegrainNotes, LegrainNotesAdmin)

class MediaPersonOrgRelationsInline(admin.TabularInline):
    model = MediaPersonOrgRelations
    fields = ['media', 'relation_type', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)        
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    extra = 1
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'media':
            kwargs["queryset"] = Media.objects.filter(type__type = 'publication').order_by('title')
        elif db_field.name == 'relation_type':
            kwargs["queryset"] = Relations.objects.filter(Q(pk=2) | Q(pk=5))
        return super(MediaPersonOrgRelationsInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
    def get_queryset(self, request):
        qs = super(MediaPersonOrgRelationsInline, self).get_queryset(request)
        return qs.filter(Q(relation_type=2) | Q(relation_type=5))    

class PersonOrgPropertyInline(admin.TabularInline):
    model = PersonOrgProperty
    extra = 3
    fields = ['property', 'property_value', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',) 
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }    

class PersonOrgAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['title', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['title', 'notes', 'created', 'modified', 'last_mod_by']
    inlines = [PersonOrgPropertyInline, MediaPersonOrgRelationsInline, PersonOrgLinkedDataInline, PersonOrgCollectionEntityInline]
    search_fields = ['title']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    } 

    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, PersonOrgProperty) or isinstance(instance, MediaPersonOrgRelations) or isinstance(instance, PersonOrgLinkedData) : #Check if it is the correct type of inline
                instance.last_mod_by = request.user            
                instance.save()    

admin.site.register(PersonOrg, PersonOrgAdmin)

class GlobalVarsAdmin(admin.ModelAdmin):
    readonly_fields = ('human_title', 'variable')
    list_display = ['human_title', 'val']
    search_fields = ['human_title']
    fields = ['human_title', 'val']
    
admin.site.register(GlobalVars, GlobalVarsAdmin)

class SiteContentForm(ModelForm):
    class Meta:
  
        _ck_editor_toolbar = [
            {'name': 'basicstyles', 'groups': ['basicstyles', 'cleanup']},
            {'name': 'paragraph',
             'groups': ['list', 'indent', 'blocks', 'align']},
            {'name': 'document', 'groups': ['mode']}, '/',
            {'name': 'styles'}, {'name': 'colors'},
            {'name': 'insert_custom',
             'items': ['Image', 'Flash', 'Table', 'HorizontalRule']},
            {'name': 'links'},
            {'name': 'about'}]

        _ck_editor_config = {'autoGrow_onStartup': True,
                             'autoGrow_minHeight': 100,
                             'autoGrow_maxHeight': 250,
                             'extraPlugins': 'autogrow',
                             'toolbarGroups': _ck_editor_toolbar}            
  
        widgets = {
            'val': CKEditorWidget(editor_options=_ck_editor_config),
        }

class SiteContentAdmin(admin.ModelAdmin):
    readonly_fields = ('human_title', 'variable')
    list_display = ['human_title', 'val']
    search_fields = ['human_title']
    form = SiteContentForm
    fieldsets = [
        ('Edit Text', {
            'classes': ('full-width',),
            'fields': ['val']})        
    ]
    
admin.site.register(SiteContent, SiteContentAdmin)

admin.site.register(MediaType)

class DescriptivePropertyAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['property', 'primary_type', 'order', 'property_type', 'visible', 'solr_type', 'facet', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['property', 'primary_type', 'order', 'property_type', 'visible', 'solr_type', 'facet', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    search_fields = ['property']
    list_filter = ('primary_type', 'visible', 'solr_type', 'facet', 'property_type')
    list_editable = ('primary_type', 'order', 'visible', 'solr_type', 'facet', 'notes', 'property_type')
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(DescriptiveProperty, DescriptivePropertyAdmin)
admin.site.register(MediaProperty)

class SubjectPropertyAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['subject', 'property', 'property_value', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['subject', 'property', 'property_value', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(SubjectProperty, SubjectPropertyAdmin)
admin.site.register(Relations)

# class MediaSubjectRelationsForm(ModelForm):
    # class Meta:
        # widgets = {
            # 'subject': LinkedSelect
        # }

class MediaSubjectRelationsAdmin(admin.ModelAdmin):
    readonly_fields = ('subject', 'created', 'modified', 'last_mod_by')
    fields = ['media', 'subject', 'relation_type', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['media', 'subject', 'relation_type', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    search_fields = ['media__title', 'notes']
#    form = MediaSubjectRelationsForm
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(MediaSubjectRelations, MediaSubjectRelationsAdmin)

class LocationSubjectRelationsAdmin(admin.ModelAdmin):
    readonly_fields = ('created', 'modified', 'last_mod_by')
    fields = ['location', 'subject', 'relation_type', 'notes', 'created', 'modified', 'last_mod_by']
    list_display = ['location', 'subject', 'relation_type', 'notes', 'created', 'modified', 'last_mod_by']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2})},
    }
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()

admin.site.register(LocationSubjectRelations, LocationSubjectRelationsAdmin)

admin.site.register(MediaPersonOrgRelations)
admin.site.register(PersonOrgProperty)

class LocationPropertyInline(admin.TabularInline):
    model = LocationProperty
    fields = ['property', 'property_value', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    ordering = ('property__order',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'property':
            kwargs["queryset"] = DescriptiveProperty.objects.filter(Q(primary_type='AL') | Q(primary_type='SL'))
        return super(LocationPropertyInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
class MediaLocationRelationsInline(admin.TabularInline):
    model = MediaLocationRelations
    fields = ['media', 'relation_type', 'notes', 'last_mod_by']
    readonly_fields = ('last_mod_by',)        
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    extra = 1
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'media':
            kwargs["queryset"] = Media.objects.filter(type__type = 'publication').order_by('title')
        elif db_field.name == 'relation_type':
            kwargs["queryset"] = Relations.objects.filter(Q(pk=2) | Q(pk=5))
        return super(MediaLocationRelationsInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        
    def get_queryset(self, request):
        qs = super(MediaLocationRelationsInline, self).get_queryset(request)
        return qs.filter(Q(relation_type=2) | Q(relation_type=5))        

class LocationAdmin(MPTTModelAdmin):
    readonly_fields = ('title', 'created', 'modified', 'last_mod_by')    
    inlines = [LocationPropertyInline, MediaLocationRelationsInline, LocationCollectionEntityInline]
    search_fields = ['title']
    list_display = ('title', 'notes', 'type', 'ancestors')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    list_filter = ['type']
    fields = ['title', 'notes', 'type', 'parent', 'created', 'modified', 'last_mod_by']
    
    change_form_template = 'admin/base/location/change_form.html'    
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, LocationProperty) or isinstance(instance, MediaLocationRelations): #Check if it is the correct type of inline
                instance.last_mod_by = request.user            
                instance.save()

admin.site.register(Location, LocationAdmin)

class PostAdmin(admin.ModelAdmin):
    form = BlogPostForm
    list_display = ['title']
    list_filter = ['published', 'created']
    search_fields = ['title', 'body']
    date_hierarchy = 'created'
    save_on_top = True
    prepopulated_fields = {"slug": ("title",)}

admin.site.register(Post, PostAdmin)

class ObjectTypeAdmin(admin.ModelAdmin):
    readonly_fields = ('last_mod_by',)
    list_display = ('type', 'notes', 'control_field')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }
    
    def save_model(self, request, obj, form, change):
        obj.last_mod_by = request.user
        obj.save()
        
admin.site.register(ObjectType, ObjectTypeAdmin)

class LinkedDataAdmin(admin.ModelAdmin):
    list_display = ['control_field', 'source', 'show_url']
    search_fields = ['control_field']
    
    def show_url(self, obj):
        return '<a href="%s">%s</a>' % (obj.link, obj.link)
    show_url.allow_tags = True
    show_url.short_description = "Link"

admin.site.register(ControlFieldLinkedData, LinkedDataAdmin)

class UploadBatchAdmin(admin.ModelAdmin):
    fields = ['name']
    readonly_fields = ('name', )
    search_fields = ['name']
    
admin.site.register(UploadBatch, UploadBatchAdmin)

""" UPCOMING FEATURES """

class AdminForumPostForm(ModelForm):
    """ Used on Admin Post Change Form page to edit admin forum posts """
    
    subject = SubjectChoices(        
        label = 'Attached Objects',
        widget = AutoHeavySelect2MultipleWidget(
            select2_options = {
                'width': '220px',
            }
        ),
        required = False
    )
    
    class Meta:
  
        _ck_editor_toolbar = [
            {'name': 'basicstyles', 'groups': ['basicstyles', 'cleanup']},
            {'name': 'paragraph',
             'groups': ['list', 'indent', 'blocks', 'align']},
            {'name': 'document', 'groups': ['mode']}, '/',
            {'name': 'styles'}, {'name': 'colors'},
            {'name': 'insert_custom',
             'items': ['Image', 'Flash', 'Table', 'HorizontalRule']},
            {'name': 'links'},
            {'name': 'about'}]

        _ck_editor_config = {'autoGrow_onStartup': True,
                             'autoGrow_minHeight': 100,
                             'autoGrow_maxHeight': 250,
                             'extraPlugins': 'autogrow',
                             'toolbarGroups': _ck_editor_toolbar}            
  
        widgets = {
            'body': CKEditorWidget(editor_options=_ck_editor_config),
        }

class AdminCommentInline(admin.StackedInline):
    model = AdminComment
    extra = 0
    readonly_fields = ('author', 'created')
    template = 'admin/edit_inline/stacked_adminpost.html'
    
    def queryset(self, request):
        """ Returns only comments checked as published or written by the author (even if unpublished) """
        
        qs = super(AdminCommentInline, self).queryset(request)
        return qs.filter(Q(published = True) | Q(published = False, author = request.user))
        
""" class AdminPostAdmin(admin.ModelAdmin):
    form = AdminForumPostForm
    readonly_fields = ('author', 'created')
    inlines = [AdminCommentInline]
    list_display = ['title', 'author', 'created', 'published']
    list_filter = ['published', 'created']
    search_fields = ['title', 'body']
    date_hierarchy = 'created'
    save_on_top = True
    change_form_template = 'admin/base/adminpost/change_form_adminpost.html'
    
    class Media:
        # the django-select2 styles have to be added manually for some reason, otherwise they don't work
        css = {
            "all": ("django_select2/css/select2.min.css",)
        }
    
    def save_model(self, request, obj, form, change):
        if obj.pk is None:
            obj.author = request.user
            obj.save()
        else:
            obj.save()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, AdminComment): #Check if it is the correct type of inline
                instance.author = request.user            
                instance.save()        
        
    def queryset(self, request):
        qs = super(AdminPostAdmin, self).queryset(request)
        return qs.filter(Q(published = True) | Q(published = False, author = request.user))
        
    def has_delete_permission(self, request, obj = None):
        if obj is not None:
            if request.user == obj.author:
                return True
        return False

admin.site.register(AdminPost, AdminPostAdmin) """