from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Assessment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('title', models.CharField(max_length=240)),
                ('description', models.TextField(blank=True, default='')),
                ('category', models.CharField(choices=[('brandschutz', 'Brandschutz'), ('explosionsschutz', 'Explosionsschutz'), ('arbeitssicherheit', 'Arbeitssicherheit'), ('arbeitsschutz', 'Arbeitsschutz'), ('general', 'Allgemein')], default='general', max_length=50)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('in_review', 'In Review'), ('approved', 'Approved'), ('archived', 'Archived')], default='draft', max_length=20)),
                ('site_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('created_by_id', models.UUIDField(blank=True, null=True)),
                ('approved_by_id', models.UUIDField(blank=True, null=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'risk_assessment',
            },
        ),
        migrations.CreateModel(
            name='Hazard',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('title', models.CharField(max_length=240)),
                ('description', models.TextField(blank=True, default='')),
                ('severity', models.IntegerField(choices=[(1, 'Gering'), (2, 'Mittel'), (3, 'Hoch'), (4, 'Sehr hoch'), (5, 'Kritisch')], default=1)),
                ('probability', models.IntegerField(choices=[(1, 'Unwahrscheinlich'), (2, 'Selten'), (3, 'Gelegentlich'), (4, 'Wahrscheinlich'), (5, 'Häufig')], default=1)),
                ('mitigation', models.TextField(blank=True, default='')),
                ('residual_risk', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assessment', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='hazards', to='risk.assessment')),
            ],
            options={
                'db_table': 'risk_hazard',
            },
        ),
        migrations.AddIndex(
            model_name='hazard',
            index=models.Index(fields=['tenant_id', 'assessment'], name='risk_hazard_tenant__a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='assessment',
            index=models.Index(fields=['tenant_id', 'status'], name='risk_assess_tenant__d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='assessment',
            index=models.Index(fields=['tenant_id', 'category'], name='risk_assess_tenant__g7h8i9_idx'),
        ),
        migrations.AddConstraint(
            model_name='assessment',
            constraint=models.CheckConstraint(check=models.Q(('status__in', ['draft', 'in_review', 'approved', 'archived'])), name='ck_assessment_status_valid'),
        ),
        migrations.AddConstraint(
            model_name='assessment',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'title'), name='uq_assessment_title_per_tenant'),
        ),
    ]
