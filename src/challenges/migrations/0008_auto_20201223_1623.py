# Generated by Django 3.1.4 on 2020-12-23 16:23

import challenges.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("challenge", "0007_file_upload"),
    ]

    operations = [
        migrations.AlterField(
            model_name="file",
            name="upload",
            field=models.FileField(null=True, upload_to=challenge.logic.get_file_path),
        ),
    ]
