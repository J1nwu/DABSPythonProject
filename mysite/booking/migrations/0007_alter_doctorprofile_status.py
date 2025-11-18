from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0006_doctorprofile_break_end_time_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="doctorprofile",
            name="status",
            field=models.CharField(
                choices=[
                    ("Pending", "Pending"),
                    ("Approved", "Approved"),
                    ("Rejected", "Rejected"),
                    ("Active", "Active"),
                    ("Inactive", "Inactive"),
                ],
                default="Pending",
                max_length=10,
            ),
        ),
    ]