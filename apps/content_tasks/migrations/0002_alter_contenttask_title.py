from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content_tasks", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contenttask",
            name="title",
            field=models.CharField(blank=True, max_length=240),
        ),
    ]
