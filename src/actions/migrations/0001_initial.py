from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ActionItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.UUIDField(db_index=True)),
                ('title', models.CharField(max_length=240)),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('open', 'Offen'), ('in_progress', 'In Bearbeitung'), ('completed', 'Erledigt'), ('cancelled', 'Abgebrochen')], default='open', max_length=20)),
                ('priority', models.IntegerField(choices=[(1, 'Niedrig'), (2, 'Mittel'), (3, 'Hoch'), (4, 'Kritisch')], default=2)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('assigned_to_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('assessment_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('hazard_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'actions_action_item',
            },
        ),
        migrations.AddIndex(
            model_name='actionitem',
            index=models.Index(fields=['tenant_id', 'status'], name='actions_act_tenant__a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='actionitem',
            index=models.Index(fields=['tenant_id', 'due_date'], name='actions_act_tenant__d4e5f6_idx'),
        ),
        migrations.AddConstraint(
            model_name='actionitem',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'title'), name='uq_action_title_per_tenant'),
        ),
    ]
