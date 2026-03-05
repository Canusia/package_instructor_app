import uuid, logging

from django.db import models
from django.db.models import JSONField

from model_utils import FieldTracker

from alerts.models import Alert
from instructor_app.email import send_notification
from cis.models.course import Course

logger = logging.getLogger(__name__)


class ApplicantCourseReviewer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    application_course = models.ForeignKey('instructor_app.ApplicantSchoolCourse', on_delete=models.PROTECT)
    reviewer = models.ForeignKey('cis.CustomUser', on_delete=models.PROTECT, related_name='inst_app_applicantcoursereviewer_set')

    assigned_on = models.DateField(auto_now_add=True)

    STATUS_OPTIONS = (
        ('---', '---'),
        ('Approved', 'Approved'),
        ('Declined', 'Declined'),
        ('Need more information', 'Need more information')
    )
    status = models.CharField(max_length=50, choices=STATUS_OPTIONS, default='---')
    misc_info = JSONField(blank=True, null=True)

    status_changed_on = JSONField(blank=True, null=True)
    tracker = FieldTracker(fields=['status'])

    class Meta:
        unique_together = ['reviewer', 'application_course']

    def notify_reviewer(self):
        from instructor_app.settings.teacher_application_email import teacher_application_email as tapp_settings

        email_settings = tapp_settings.from_db()
        app = self.application_course.teacherapplication

        try:
            assigned_to_first_name = assigned_to_last_name = 'Not Assigned'
            if app.assigned_to:
                assigned_to_first_name = app.assigned_to.first_name
                assigned_to_last_name = app.assigned_to.last_name

            context_dict = {
                'teacher_first_name': app.user.first_name,
                'teacher_last_name': app.user.last_name,
                'teacher_email': app.user.email,
                'course': self.application_course.course,
                'fc_first_name': self.reviewer.first_name,
                'fc_last_name': self.reviewer.last_name,
                'application_url': app.faculty_url,
                'highschool': self.application_course.highschool.name,
                'assigned_cis_staff_first_name': assigned_to_first_name,
                'assigned_cis_staff_last_name': assigned_to_last_name,
            }
        except Exception as e:
            logger.error('Exception while processing reviewer email template' + str(e))
            return

        send_notification(
            email_settings.get('fc_ready_email_subject'),
            email_settings['fc_ready_email'],
            context_dict,
            [self.reviewer.email]
        )

    @property
    def get_status_history(self):
        if not self.status_changed_on:
            self.status_changed_on = {}
            return '-'

        result = ''
        for key, val in self.status_changed_on.items():
            key = key.replace('_', ' ').title()
            result += f'<div class="detail_label">{key}</div><div class="mb-2">{val}</div>'
        return result


    def notify_status_change(self, new_status):
        app = self.application_course.teacherapplication

        from instructor_app.settings.teacher_application_email import teacher_application_email as tapp_s

        email_settings = tapp_s.from_db()

        recipient = []
        if not app.assigned_to:
            course_ids = app.course_ids
            course_admins = Course.get_administrators(course_ids)

            for course_admin in course_admins:
                alert = Alert()
                alert.alert_type = 'si_application_reviewed'
                alert.recipient = course_admin.user
                link = app.ce_url
                alert.message = f'<a href="{link}">{self.reviewer.first_name} has reviewed application submitted by {app.user.first_name} for {app.courses}</a>'
                alert.save()

                recipient += [course_admin.user.email]
        else:
            recipient = [app.assigned_to.email]

        send_notification(
            email_settings.get('course_reviewed_email_subject'),
            email_settings['course_reviewed_email'],
            {
                'teacher_first_name': app.user.first_name,
                'teacher_last_name': app.user.last_name,
                'highschool': app.highschool.name,
                'application_url': app.ce_url,
                'course': self.application_course.course,
                'course_review_status': self.status,
                'reviewer_name': self.reviewer.first_name + ' ' + self.reviewer.last_name,
                'reviewer_email': self.reviewer.email,
                'reviewer_comment': self.misc_info.get('reviewer_note')
            },
            recipient
        )
