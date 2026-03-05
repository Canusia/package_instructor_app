from django.db import migrations, models


def rename_status_forward(apps, schema_editor):
    TeacherApplication = apps.get_model('instructor_app', 'TeacherApplication')
    TeacherApplication.objects.filter(
        status='Approved for FC review'
    ).update(status='Ready for Review')


def rename_status_reverse(apps, schema_editor):
    TeacherApplication = apps.get_model('instructor_app', 'TeacherApplication')
    TeacherApplication.objects.filter(
        status='Ready for Review'
    ).update(status='Approved for FC review')


class Migration(migrations.Migration):

    dependencies = [
        ('instructor_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teacherapplication',
            name='status',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('In Progress', 'In Progress'),
                    ('Submitted', 'Submitted'),
                    ('Under Review', 'Under Review'),
                    ('Ready for Review', 'Ready for Review'),
                    ('Decision Made', 'Decision Made'),
                    ('Withdrawn', 'Withdrawn'),
                    ('Closed', 'Closed'),
                ],
                default='In Progress',
            ),
        ),
        migrations.RunPython(rename_status_forward, rename_status_reverse),
    ]
