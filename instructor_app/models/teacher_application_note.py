import uuid

from django.db import models
from django.db.models import JSONField
from django.urls import reverse_lazy


class TeacherApplicationNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    teacher_application = models.ForeignKey(
        'instructor_app.TeacherApplication',
        on_delete=models.CASCADE,
        related_name='notes'
    )

    note = models.TextField(blank=False)
    createdby = models.ForeignKey(
        'cis.CustomUser',
        on_delete=models.PROTECT,
        related_name='inst_app_notes',
        null=True,
        blank=True
    )
    createdon = models.DateTimeField(auto_now_add=True)
    parent = models.UUIDField(blank=True, null=True)
    meta = JSONField(blank=True, null=True)

    class Meta:
        app_label = 'instructor_app'
        ordering = ['-createdon']

    def __str__(self):
        return f"Note by {self.createdby} on {self.createdon}"

    @property
    def teacher_reply_url(self):
        from cis.utils import getDomain
        note_id = self.parent if self.parent else self.id
        url = reverse_lazy(
            'ce_instructor_app:teacher_app_note_reply',
            kwargs={'note_id': note_id}
        )
        return getDomain() + str(url)
