import uuid, os

from django.db import models
from django.db.models import JSONField
from django.dispatch import receiver

from cis.models.course import CourseAppRequirement
from cis.storage_backend import PrivateMediaStorage
from cis.utils import teacher_app_upload_path


class ApplicationUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    teacher_application = models.ForeignKey('instructor_app.TeacherApplication', on_delete=models.PROTECT)

    associated_with = JSONField(
        blank=True,
        null=True
    )

    upload = models.FileField(
        storage=PrivateMediaStorage(),
        upload_to=teacher_app_upload_path,
        blank=True)

    @property
    def filename(self):
        return os.path.basename(self.upload.name)

    @property
    def associated_with_as_html(self):
        if not self.associated_with:
            return ''

        file_assoc = CourseAppRequirement.objects.filter(
            id__in=self.associated_with
        )

        if not file_assoc:
            return ''

        return '<br>'.join([
            file.name for file in file_assoc
        ])


@receiver(models.signals.post_delete, sender=ApplicationUpload)
def auto_delete_upload_on_delete(sender, instance, **kwargs):
    try:
        if instance.upload:
            instance.upload.delete(save=False)
        return True
    except AttributeError:
        pass
    return False
