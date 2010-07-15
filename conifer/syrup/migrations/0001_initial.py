# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'UserProfile'
        db.create_table('syrup_userprofile', (
            ('last_email_notice', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('wants_email_notices', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('ils_userid', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('syrup', ['UserProfile'])

        # Adding model 'ServiceDesk'
        db.create_table('syrup_servicedesk', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('external_id', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('syrup', ['ServiceDesk'])

        # Adding model 'Term'
        db.create_table('syrup_term', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('finish', self.gf('django.db.models.fields.DateField')()),
            ('start', self.gf('django.db.models.fields.DateField')()),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('syrup', ['Term'])

        # Adding model 'Department'
        db.create_table('syrup_department', (
            ('service_desk', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.ServiceDesk'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('syrup', ['Department'])

        # Adding model 'Course'
        db.create_table('syrup_course', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('department', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Department'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('syrup', ['Course'])

        # Adding model 'Z3950Target'
        db.create_table('syrup_z3950target', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('database', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('syntax', self.gf('django.db.models.fields.CharField')(default='USMARC', max_length=10)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('host', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('port', self.gf('django.db.models.fields.IntegerField')(default=210)),
        ))
        db.send_create_signal('syrup', ['Z3950Target'])

        # Adding model 'Config'
        db.create_table('syrup_config', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=8192)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal('syrup', ['Config'])

        # Adding model 'Site'
        db.create_table('syrup_site', (
            ('term', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Term'])),
            ('service_desk', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.ServiceDesk'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('passkey', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=256, null=True, blank=True)),
            ('access', self.gf('django.db.models.fields.CharField')(default='CLOSE', max_length=5)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Course'])),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('syrup', ['Site'])

        # Adding unique constraint on 'Site', fields ['course', 'term', 'owner']
        db.create_unique('syrup_site', ['course_id', 'term_id', 'owner_id'])

        # Adding model 'Group'
        db.create_table('syrup_group', (
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Site'])),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('external_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=2048, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('syrup', ['Group'])

        # Adding model 'Membership'
        db.create_table('syrup_membership', (
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Group'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('role', self.gf('django.db.models.fields.CharField')(default='STUDT', max_length=6)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('syrup', ['Membership'])

        # Adding unique constraint on 'Membership', fields ['group', 'user']
        db.create_unique('syrup_membership', ['group_id', 'user_id'])

        # Adding model 'Item'
        db.create_table('syrup_item', (
            ('parent_heading', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Item'], null=True, blank=True)),
            ('publisher', self.gf('django.db.models.fields.CharField')(max_length=8192, null=True, blank=True)),
            ('itemtype', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=1, null=True, blank=True)),
            ('marcxml', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('author', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=8192, null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=8192, db_index=True)),
            ('fileobj_mimetype', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Site'])),
            ('item_type', self.gf('django.db.models.fields.CharField')(max_length=7)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('fileobj', self.gf('django.db.models.fields.files.FileField')(default=None, max_length=255, null=True, blank=True)),
            ('published', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('bib_id', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
        ))
        db.send_create_signal('syrup', ['Item'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'UserProfile'
        db.delete_table('syrup_userprofile')

        # Deleting model 'ServiceDesk'
        db.delete_table('syrup_servicedesk')

        # Deleting model 'Term'
        db.delete_table('syrup_term')

        # Deleting model 'Department'
        db.delete_table('syrup_department')

        # Deleting model 'Course'
        db.delete_table('syrup_course')

        # Deleting model 'Z3950Target'
        db.delete_table('syrup_z3950target')

        # Deleting model 'Config'
        db.delete_table('syrup_config')

        # Deleting model 'Site'
        db.delete_table('syrup_site')

        # Removing unique constraint on 'Site', fields ['course', 'term', 'owner']
        db.delete_unique('syrup_site', ['course_id', 'term_id', 'owner_id'])

        # Deleting model 'Group'
        db.delete_table('syrup_group')

        # Deleting model 'Membership'
        db.delete_table('syrup_membership')

        # Removing unique constraint on 'Membership', fields ['group', 'user']
        db.delete_unique('syrup_membership', ['group_id', 'user_id'])

        # Deleting model 'Item'
        db.delete_table('syrup_item')
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'syrup.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '8192'})
        },
        'syrup.course': {
            'Meta': {'object_name': 'Course'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'department': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Department']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        },
        'syrup.department': {
            'Meta': {'object_name': 'Department'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'service_desk': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.ServiceDesk']"})
        },
        'syrup.group': {
            'Meta': {'object_name': 'Group'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'external_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Site']"})
        },
        'syrup.item': {
            'Meta': {'object_name': 'Item'},
            'author': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '8192', 'null': 'True', 'blank': 'True'}),
            'bib_id': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'fileobj': ('django.db.models.fields.files.FileField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'fileobj_mimetype': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_type': ('django.db.models.fields.CharField', [], {'max_length': '7'}),
            'itemtype': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'marcxml': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'parent_heading': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Item']", 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'publisher': ('django.db.models.fields.CharField', [], {'max_length': '8192', 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Site']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '8192', 'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'syrup.membership': {
            'Meta': {'unique_together': "(('group', 'user'),)", 'object_name': 'Membership'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'default': "'STUDT'", 'max_length': '6'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'syrup.servicedesk': {
            'Meta': {'object_name': 'ServiceDesk'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'syrup.site': {
            'Meta': {'unique_together': "(('course', 'term', 'owner'),)", 'object_name': 'Site'},
            'access': ('django.db.models.fields.CharField', [], {'default': "'CLOSE'", 'max_length': '5'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Course']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'passkey': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'service_desk': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.ServiceDesk']"}),
            'term': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Term']"})
        },
        'syrup.term': {
            'Meta': {'object_name': 'Term'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'finish': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'syrup.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ils_userid': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'last_email_notice': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'wants_email_notices': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'syrup.z3950target': {
            'Meta': {'object_name': 'Z3950Target'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'database': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '210'}),
            'syntax': ('django.db.models.fields.CharField', [], {'default': "'USMARC'", 'max_length': '10'})
        }
    }
    
    complete_apps = ['syrup']
