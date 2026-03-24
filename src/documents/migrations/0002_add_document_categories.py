"""Add new document categories for Gefahrstoffdatenbank."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="category",
            field=models.CharField(
                choices=[
                    ("brandschutz", "Brandschutz"),
                    ("explosionsschutz", "Explosionsschutz"),
                    ("arbeitssicherheit", "Arbeitssicherheit"),
                    ("nachweis", "Nachweis"),
                    ("general", "Allgemein"),
                    ("sdb", "Sicherheitsdatenblatt"),
                    ("gefaehrdungsbeurteilung", "Gefährdungsbeurteilung"),
                    ("betriebsanweisung", "Betriebsanweisung"),
                    ("unterweisung", "Unterweisungsnachweis"),
                    ("pruefbericht", "Prüfbericht"),
                ],
                default="general",
                max_length=50,
            ),
        ),
    ]
