from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('title', models.CharField(max_length=240)),
                ('category', models.CharField(choices=[('brandschutz', 'Brandschutz'), ('explosionsschutz', 'Explosionsschutz'), ('arbeitssicherheit', 'Arbeitssicherheit'), ('nachweis', 'Nachweis'), ('general', 'Allgemein')], default='general', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'documents_document',
            },
        ),
        migrations.CreateModel(
            name='DocumentVersion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('version', models.IntegerField()),
                ('filename', models.CharField(max_length=255)),
                ('content_type', models.CharField(max_length=120)),
                ('size_bytes', models.BigIntegerField()),
                ('sha256', models.CharField(max_length=64)),
                ('s3_key', models.CharField(max_length=512)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='versions', to='documents.document')),
            ],
            options={
                'db_table': 'documents_document_version',
            },
        ),
        migrations.AddConstraint(
            model_name='document',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'title'), name='uq_doc_title_per_tenant'),
        ),
        migrations.AddConstraint(
            model_name='documentversion',
            constraint=models.UniqueConstraint(fields=('document', 'version'), name='uq_doc_version'),
        ),
    ]
