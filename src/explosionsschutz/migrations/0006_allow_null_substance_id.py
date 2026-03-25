from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explosionsschutz', '0005_alter_equipmentatexcheck_result_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='explosionconcept',
            name='substance_id',
            field=models.UUIDField(
                blank=True, db_index=True, null=True,
                help_text='FK zu substances.Substance (UUID)',
            ),
        ),
    ]
