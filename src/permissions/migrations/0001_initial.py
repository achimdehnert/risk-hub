from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=200, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'permissions_permission',
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('name', models.CharField(max_length=120)),
                ('is_system', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'permissions_role',
            },
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('permission', models.ForeignKey(on_delete=models.deletion.CASCADE, to='permissions.permission')),
                ('role', models.ForeignKey(on_delete=models.deletion.CASCADE, to='permissions.role')),
            ],
            options={
                'db_table': 'permissions_role_permission',
            },
        ),
        migrations.AddField(
            model_name='role',
            name='permissions',
            field=models.ManyToManyField(related_name='roles', through='permissions.RolePermission', to='permissions.permission'),
        ),
        migrations.CreateModel(
            name='Scope',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('scope_type', models.CharField(choices=[('TENANT', 'Tenant'), ('SITE', 'Site'), ('ASSET', 'Asset')], max_length=12)),
                ('site_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('asset_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'permissions_scope',
            },
        ),
        migrations.CreateModel(
            name='Assignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('user_id', models.UUIDField(db_index=True)),
                ('created_by_user_id', models.UUIDField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('valid_from', models.DateTimeField(blank=True, null=True)),
                ('valid_to', models.DateTimeField(blank=True, null=True)),
                ('role', models.ForeignKey(on_delete=models.deletion.CASCADE, to='permissions.role')),
                ('scope', models.ForeignKey(on_delete=models.deletion.CASCADE, to='permissions.scope')),
            ],
            options={
                'db_table': 'permissions_assignment',
            },
        ),
        migrations.AddConstraint(
            model_name='rolepermission',
            constraint=models.UniqueConstraint(fields=('role', 'permission'), name='uq_role_permission'),
        ),
        migrations.AddConstraint(
            model_name='role',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'name'), name='uq_permissions_role_name_per_tenant'),
        ),
        migrations.AddConstraint(
            model_name='scope',
            constraint=models.CheckConstraint(check=models.Q(('scope_type__in', ['TENANT', 'SITE', 'ASSET'])), name='ck_scope_type_valid'),
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'user_id', 'role', 'scope'), name='uq_assignment'),
        ),
    ]
