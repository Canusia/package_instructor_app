import uuid, os

from django.db import models
from django.db.models import JSONField
from django.dispatch import receiver

from cis.storage_backend import PrivateMediaStorage
from cis.utils import recommendation_upload_path


class ApplicantRecommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    teacher_application = models.ForeignKey('instructor_app.TeacherApplication', on_delete=models.PROTECT)
    applicantschoolcourse = models.ForeignKey(
        'instructor_app.ApplicantSchoolCourse', on_delete=models.PROTECT, blank=True, null=True)

    submitted_on = models.DateField(auto_now=True)
    recommendation = JSONField(blank=True, null=True)
    submitter = JSONField(blank=True, null=True)

    upload = models.FileField(
        storage=PrivateMediaStorage(),
        upload_to=recommendation_upload_path
    )

    @property
    def filename(self):
        return os.path.basename(self.upload.name)


@receiver(models.signals.post_delete, sender=ApplicantRecommendation)
def auto_delete_recommendation_on_delete(sender, instance, **kwargs):
    try:
        if instance.upload:
            instance.upload.delete(save=False)
        return True
    except AttributeError:
        pass
    return False
