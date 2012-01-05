# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'UserProfile'
        db.create_table('syrup_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('ils_userid', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('wants_email_notices', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('last_email_notice', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
            ('external_memberships_checked', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('syrup', ['UserProfile'])

        # Adding model 'ServiceDesk'
        db.create_table('syrup_servicedesk', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('external_id', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
        ))
        db.send_create_signal('syrup', ['ServiceDesk'])

        # Adding model 'Term'
        db.create_table('syrup_term', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('start', self.gf('django.db.models.fields.DateField')()),
            ('finish', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('syrup', ['Term'])

        # Adding model 'Department'
        db.create_table('syrup_department', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('service_desk', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.ServiceDesk'])),
        ))
        db.send_create_signal('syrup', ['Department'])

        # Adding model 'Course'
        db.create_table('syrup_course', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('department', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Department'])),
            ('coursenotes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('syrup', ['Course'])

        # Adding model 'Z3950Target'
        db.create_table('syrup_z3950target', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('host', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('database', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('port', self.gf('django.db.models.fields.IntegerField')(default=210)),
            ('syntax', self.gf('django.db.models.fields.CharField')(default='USMARC', max_length=10)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('syrup', ['Z3950Target'])

        # Adding model 'Config'
        db.create_table('syrup_config', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=256)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=8192)),
        ))
        db.send_create_signal('syrup', ['Config'])

        # Adding model 'Site'
        db.create_table('syrup_site', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Course'])),
            ('start_term', self.gf('django.db.models.fields.related.ForeignKey')(related_name='start_term', to=orm['syrup.Term'])),
            ('end_term', self.gf('django.db.models.fields.related.ForeignKey')(related_name='end_term', to=orm['syrup.Term'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('service_desk', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.ServiceDesk'])),
            ('access', self.gf('django.db.models.fields.CharField')(default='ANON', max_length=5)),
            ('sitenotes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('syrup', ['Site'])

        # Adding unique constraint on 'Site', fields ['course', 'start_term', 'owner']
        db.create_unique('syrup_site', ['course_id', 'start_term_id', 'owner_id'])

        # Adding model 'Group'
        db.create_table('syrup_group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Site'])),
            ('external_id', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=2048, null=True, blank=True)),
        ))
        db.send_create_signal('syrup', ['Group'])

        # Adding model 'Membership'
        db.create_table('syrup_membership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Group'])),
            ('role', self.gf('django.db.models.fields.CharField')(default='STUDT', max_length=6)),
        ))
        db.send_create_signal('syrup', ['Membership'])

        # Adding unique constraint on 'Membership', fields ['group', 'user']
        db.create_unique('syrup_membership', ['group_id', 'user_id'])

        # Adding model 'Item'
        db.create_table('syrup_item', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Site'])),
            ('item_type', self.gf('django.db.models.fields.CharField')(max_length=7)),
            ('bib_id', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('suppress_item', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('marcxml', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=8192, db_index=True)),
            ('author', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=8192, null=True, blank=True)),
            ('publisher', self.gf('django.db.models.fields.CharField')(max_length=8192, null=True, blank=True)),
            ('published', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('source_title', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=8192, null=True, blank=True)),
            ('volume', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('issue', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('pages', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('isbn', self.gf('django.db.models.fields.CharField')(max_length=17, null=True, blank=True)),
            ('barcode', self.gf('django.db.models.fields.CharField')(max_length=14, null=True, blank=True)),
            ('orig_prefix', self.gf('django.db.models.fields.IntegerField')(default='-1')),
            ('orig_callno', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('orig_suffix', self.gf('django.db.models.fields.IntegerField')(default='-1')),
            ('evergreen_update', self.gf('django.db.models.fields.CharField')(default='Cat', max_length=4, blank=True)),
            ('copyright_status', self.gf('django.db.models.fields.CharField')(default='UK', max_length=2)),
            ('circ_modifier', self.gf('django.db.models.fields.CharField')(default='CIRC', max_length=50, blank=True)),
            ('circ_desk', self.gf('django.db.models.fields.CharField')(default='6329', max_length=5, blank=True)),
            ('itemtype', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=1, null=True, blank=True)),
            ('parent_heading', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Item'], null=True, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=2048, null=True, blank=True)),
            ('fileobj', self.gf('django.db.models.fields.files.FileField')(default=None, max_length=255, null=True, blank=True)),
            ('fileobj_origname', self.gf('django.db.models.fields.CharField')(max_length=2048, null=True, blank=True)),
            ('fileobj_mimetype', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('itemnotes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('syrup', ['Item'])

        # Adding model 'Declaration'
        db.create_table('syrup_declaration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['syrup.Item'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('syrup', ['Declaration'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Membership', fields ['group', 'user']
        db.delete_unique('syrup_membership', ['group_id', 'user_id'])

        # Removing unique constraint on 'Site', fields ['course', 'start_term', 'owner']
        db.delete_unique('syrup_site', ['course_id', 'start_term_id', 'owner_id'])

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

        # Deleting model 'Group'
        db.delete_table('syrup_group')

        # Deleting model 'Membership'
        db.delete_table('syrup_membership')

        # Deleting model 'Item'
        db.delete_table('syrup_item')

        # Deleting model 'Declaration'
        db.delete_table('syrup_declaration')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'syrup.config': {
            'Meta': {'object_name': 'Config'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '256'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '8192'})
        },
        'syrup.course': {
            'Meta': {'ordering': "['code']", 'object_name': 'Course'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'coursenotes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'department': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Department']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        },
        'syrup.declaration': {
            'Meta': {'object_name': 'Declaration'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Item']"}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'syrup.department': {
            'Meta': {'ordering': "['name']", 'object_name': 'Department'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'service_desk': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.ServiceDesk']"})
        },
        'syrup.group': {
            'Meta': {'ordering': "['site__course__code', 'site__course__name', 'external_id']", 'object_name': 'Group'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'external_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Site']"})
        },
        'syrup.item': {
            'Meta': {'ordering': "['title', 'author', 'published']", 'object_name': 'Item'},
            'author': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '8192', 'null': 'True', 'blank': 'True'}),
            'barcode': ('django.db.models.fields.CharField', [], {'max_length': '14', 'null': 'True', 'blank': 'True'}),
            'bib_id': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'circ_desk': ('django.db.models.fields.CharField', [], {'default': "'6329'", 'max_length': '5', 'blank': 'True'}),
            'circ_modifier': ('django.db.models.fields.CharField', [], {'default': "'CIRC'", 'max_length': '50', 'blank': 'True'}),
            'copyright_status': ('django.db.models.fields.CharField', [], {'default': "'UK'", 'max_length': '2'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'evergreen_update': ('django.db.models.fields.CharField', [], {'default': "'Cat'", 'max_length': '4', 'blank': 'True'}),
            'fileobj': ('django.db.models.fields.files.FileField', [], {'default': 'None', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'fileobj_mimetype': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'fileobj_origname': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isbn': ('django.db.models.fields.CharField', [], {'max_length': '17', 'null': 'True', 'blank': 'True'}),
            'issue': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'item_type': ('django.db.models.fields.CharField', [], {'max_length': '7'}),
            'itemnotes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'itemtype': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'marcxml': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'orig_callno': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'orig_prefix': ('django.db.models.fields.IntegerField', [], {'default': "'-1'"}),
            'orig_suffix': ('django.db.models.fields.IntegerField', [], {'default': "'-1'"}),
            'pages': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'parent_heading': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Item']", 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'publisher': ('django.db.models.fields.CharField', [], {'max_length': '8192', 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Site']"}),
            'source_title': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '8192', 'null': 'True', 'blank': 'True'}),
            'suppress_item': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '8192', 'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'volume': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'syrup.membership': {
            'Meta': {'ordering': "['user__username', 'group__site__course__code', 'group__site__course__name', 'group__external_id']", 'unique_together': "(('group', 'user'),)", 'object_name': 'Membership'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'default': "'STUDT'", 'max_length': '6'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'syrup.servicedesk': {
            'Meta': {'ordering': "['name']", 'object_name': 'ServiceDesk'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'syrup.site': {
            'Meta': {'ordering': "['course__code', 'owner__last_name', '-start_term__start']", 'unique_together': "(('course', 'start_term', 'owner'),)", 'object_name': 'Site'},
            'access': ('django.db.models.fields.CharField', [], {'default': "'ANON'", 'max_length': '5'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.Course']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end_term': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'end_term'", 'to': "orm['syrup.Term']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'service_desk': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['syrup.ServiceDesk']"}),
            'sitenotes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'start_term': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'start_term'", 'to': "orm['syrup.Term']"})
        },
        'syrup.term': {
            'Meta': {'ordering': "['start', 'code']", 'object_name': 'Term'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'finish': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'start': ('django.db.models.fields.DateField', [], {})
        },
        'syrup.userprofile': {
            'Meta': {'ordering': "['user__username']", 'object_name': 'UserProfile'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'external_memberships_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ils_userid': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'last_email_notice': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'wants_email_notices': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'syrup.z3950target': {
            'Meta': {'object_name': 'Z3950Target'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'database': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'host': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '210'}),
            'syntax': ('django.db.models.fields.CharField', [], {'default': "'USMARC'", 'max_length': '10'})
        }
    }

    complete_apps = ['syrup']
