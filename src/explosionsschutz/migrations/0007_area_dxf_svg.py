from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explosionsschutz', '0006_allow_null_substance_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='area',
            name='dxf_svg',
            field=models.FileField(
                blank=True, null=True,
                upload_to='areas/svg/',
                help_text='SVG-Preview generiert aus DXF via ezdxf',
            ),
        ),
    ]
