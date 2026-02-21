from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("wildfire_assessment", "0013_userprofile_dashboard_widgets"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="EcologicalReserve",
            new_name="AreaOfInterest",
        ),
        migrations.AlterModelTable(
            name="areaofinterest",
            table=None,
        ),
    ]
