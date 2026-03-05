import uuid

from django.db import models
from django.db.models import JSONField
from django.template.loader import get_template


class ApplicantSchoolCourse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    teacherapplication = models.ForeignKey('instructor_app.TeacherApplication', on_delete=models.PROTECT)
    course = models.ForeignKey('cis.Course', on_delete=models.PROTECT, related_name='inst_app_applicantschoolcourse_set')
    highschool = models.ForeignKey(
        'cis.HighSchool', on_delete=models.PROTECT, blank=True, null=True, related_name='inst_app_applicantschoolcourse_set')

    starting_academic_year = models.ForeignKey(
        'cis.AcademicYear', on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='inst_app_applicantschoolcourse_set'
    )
    misc_info = JSONField()

    STATUS_OPTIONS = (
        ('---', '---'),
        # ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Conditionally Accepted', 'Conditionally Accepted'),
        ('Denied', 'Denied'),
    )
    status = models.CharField(max_length=50, choices=STATUS_OPTIONS, default='---')
    note = models.CharField(max_length=1000, blank=True, null=True)

    class Meta:
        unique_together = ['teacherapplication', 'course', 'highschool']

    @property
    def reviewers_asHTML(self):
        from .applicant_course_reviewer import ApplicantCourseReviewer
        context = {
            'reviewers': ApplicantCourseReviewer.objects.filter(
                application_course=self
            ).order_by('-assigned_on')
        }
        template = get_template('instructor_app/ce/course_reviewers.html')
        html = template.render(context)

        return html

    @property
    def first_time_teaching(self):
        if self.misc_info.get('first_time') == '1':
            return 'Yes'
        elif self.misc_info.get('first_time') == '2':
            return 'No'
        return ''

    @property
    def replacing_instructor(self):
        if self.misc_info.get('replace_instructor') == '1':
            return 'Yes'
        elif self.misc_info.get('replace_instructor') == '2':
            return 'No'
        return ''

    @property
    def replacing_info(self):
        try:
            if self.misc_info.get('replace_instructor') == '1':
                return self.misc_info.get('instructor_name') + '<br>' + self.misc_info.get('start_date') + ' - ' + self.misc_info.get('end_date')
        except:
            return ''
