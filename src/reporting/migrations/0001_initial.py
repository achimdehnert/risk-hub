from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='RetentionPolicy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('name', models.CharField(max_length=160)),
                ('category', models.CharField(max_length=120)),
                ('retention_days', models.IntegerField()),
                ('delete_mode', models.CharField(choices=[('soft', 'Soft'), ('hard', 'Hard'), ('never', 'Never')], default='soft', max_length=12)),
                ('legal_hold_allowed', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'reporting_retention_policy',
            },
        ),
        migrations.CreateModel(
            name='ExportJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('requested_by_user_id', models.UUIDField()),
                ('export_type', models.CharField(max_length=200)),
                ('params_json', models.JSONField(default=dict)),
                ('params_hash', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')], default='queued', max_length=16)),
                ('priority', models.IntegerField(default=0)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('error', models.TextField(blank=True, null=True)),
                ('output_document_id', models.UUIDField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('retention_policy', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to='reporting.retentionpolicy')),
            ],
            options={
                'db_table': 'reporting_export_job',
            },
        ),
        migrations.AddIndex(
            model_name='exportjob',
            index=models.Index(fields=['tenant_id', 'status', '-created_at'], name='reporting_e_tenant__a1b2c3_idx'),
        ),
    ]
