from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('slug', models.SlugField(max_length=63, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'tenancy_organization',
            },
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('name', models.CharField(max_length=200)),
                ('address', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('organization', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='sites', to='tenancy.organization')),
            ],
            options={
                'db_table': 'tenancy_site',
            },
        ),
        migrations.AddConstraint(
            model_name='site',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'name'), name='uq_site_name_per_tenant'),
        ),
    ]
