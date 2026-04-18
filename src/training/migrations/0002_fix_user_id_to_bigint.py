"""Fix user_id from UUID to BigInt (table is empty, safe to drop+recreate)."""

from django.db import migrations, models


def drop_and_recreate_user_id(apps, schema_editor):
    schema_editor.execute(
        'ALTER TABLE "training_attendance" DROP COLUMN "user_id";'
    )
    schema_editor.execute(
        'ALTER TABLE "training_attendance" ADD COLUMN "user_id" bigint NOT NULL DEFAULT 0;'
    )
    schema_editor.execute(
        'ALTER TABLE "training_attendance" ALTER COLUMN "user_id" DROP DEFAULT;'
    )
    schema_editor.execute(
        'CREATE INDEX "ix_attendance_user_id" ON "training_attendance" ("user_id");'
    )


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(drop_and_recreate_user_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="trainingattendance",
            name="user_id",
            field=models.PositiveBigIntegerField(
                db_index=True,
                help_text="User-ID des Teilnehmers (FK zu identity.User.pk)",
            ),
        ),
    ]
