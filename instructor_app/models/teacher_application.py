import uuid, logging

from django.db import models
from django.urls import reverse_lazy
from django.contrib.auth.models import Group
from django.db.models import JSONField

from model_utils import FieldTracker

from alerts.models import Alert
from instructor_app.email import render_email, send_notification
from cis.models.term import AcademicYear
from cis.models.course import CourseAppRequirement, Course

logger = logging.getLogger(__name__)

FC_REVIEW_STATUS_DEFAULT = 'Ready for Review'

def get_fc_review_status():
    from instructor_app.settings.inst_app_language import inst_app_language
    return inst_app_language.from_db().get('fc_review_status_label', FC_REVIEW_STATUS_DEFAULT) or FC_REVIEW_STATUS_DEFAULT


class TeacherApplication(models.Model):
    """
    Base user model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # applicant = models.ForeignKey('instructor_app.TeacherApplicant', on_delete=models.PROTECT)
    user = models.ForeignKey('cis.CustomUser', on_delete=models.PROTECT, related_name='inst_app_teacherapplication_set')

    createdon = models.DateField(auto_now_add=False)

    status_changed_on = JSONField(blank=True, null=True)
    tracker = FieldTracker(fields=['status'])

    STATUS_OPTIONS = (
        ('In Progress', 'In Progress'),
        ('Submitted', 'Submitted'),
        ('Under Review', 'Under Review'),
        ('Ready for Review', 'Ready for Review'),
        ('Decision Made', 'Decision Made'),
        ('Withdrawn', 'Withdrawn'),
        ('Closed', 'Closed'),
    )
    status = models.CharField(max_length=30, choices=STATUS_OPTIONS, default="In Progress")

    misc_info = JSONField(blank=True, null=True)

    highschool = models.ForeignKey(
        'cis.HighSchool', on_delete=models.PROTECT, blank=True, null=True, related_name='inst_app_teacherapplication_set')
    highschool_info = JSONField(blank=True, null=True)

    assigned_to = models.ForeignKey(
        'cis.CustomUser', on_delete=models.PROTECT, blank=True, null=True,
        related_name='inst_app_assigned_to')


    def get_approval_notification_email(self):
        from django.utils.html import strip_tags
        from instructor_app.settings.teacher_application_email import (
            teacher_application_email
        )

        email_settings = teacher_application_email.from_db()
        template_str = email_settings.get('app_approved_email')

        html_body, text_body = render_email(template_str, {
            'applicant_first_name': self.user.first_name,
            'applicant_last_name': self.user.last_name,
            'applicant_highschool': self.highschool.name,
            'approved_courses_only_as_a_list': ', '.join(self.accepted_courses_names)
        })
        return (html_body, strip_tags(text_body))


    @property
    def accepted_courses(self):
        from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
        return ApplicantSchoolCourse.objects.filter(
            teacherapplication=self,
            status__in=['Accepted', 'Conditionally Accepted']
        )

    @property
    def accepted_courses_names(self):
        return [sc.course.name for sc in self.accepted_courses]

    def notify_application_approved(self):
        from instructor_app.settings.teacher_application_email import (
            teacher_application_email
        )

        email_settings = teacher_application_email.from_db()
        template_str = email_settings.get('app_approved_email')
        subject = email_settings.get('app_approved_email_subject')

        send_notification(subject, template_str, {
            'applicant_first_name': self.user.first_name,
            'applicant_last_name': self.user.last_name,
            'applicant_highschool': self.highschool.name,
            'approved_courses_only_as_a_list': ', '.join(self.accepted_courses_names)
        }, [self.user.email])

    def as_pdf(self, request=None):
        from instructor_app.services.pdf import application_as_pdf
        return application_as_pdf(self)

    def needs_notification(self, last_sent_on, num_days):
        # return True
        from datetime import datetime

        current_date = datetime.now()
        last_sent_on = datetime.strptime(last_sent_on, '%m/%d/%Y')

        return True if abs((current_date - last_sent_on).days) >= num_days else False

    def remove_role(self):
        group = Group.objects.get(name='applicant')
        self.user.groups.remove(group)

    def import_as_teacher(self):
        from instructor_app.services.import_teacher import import_as_teacher
        return import_as_teacher(self)

    @property
    def attending_si_year(self):
        if not self.misc_info.participating_acad_year:
            return 'NA'
        return AcademicYear.objects.get(pk=self.misc_info.participating_acad_year).name

    @property
    def document_list_asHTML(self):
        import itertools
        from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
        from instructor_app.models.application_upload import ApplicationUpload

        files_uploaded = ApplicationUpload.objects.filter(
            teacher_application=self
        ).values_list('associated_with', flat=True)

        assoc_ids = list(
            itertools.chain(*files_uploaded)
        )

        all_reqs = ApplicantSchoolCourse.objects.filter(
            teacherapplication=self
        ).values_list('course__id', flat=True)
        file_assoc = CourseAppRequirement.objects.filter(
            course__id__in=all_reqs
        )

        result = '<div class="list-group list-group-flush">'
        for file in file_assoc:
            result += '<div class="list-group-item list-group-item-action flex-column align-items-start '
            if file.required == '1' and str(file.id) not in assoc_ids:
                result += " list-group-item-danger"
            result += '">'

            result += "<div class='d-flex w-100 justify-content-between "
            result += "'>"
            result += f"<h5 class='mb-1'>{file.name}</h5>"
            result += "<small>"
            if str(file.id) in assoc_ids:
                result += '<i class="fas fa-check" title="Successfully Uploaded"></i>&nbsp;'
            else:
                if file.required == '1':
                    result += '<i class="fas fa-exclamation-triangle" title="Not yet uploaded"></i>'
            result += '</small>'
            result += '</div>'

            result += "<small class='text-muted'>"
            if file.required == '1':
                result += 'Required'
            else:
                result += 'Optional'
            result += "</small>"

            result += '</div>'
        else:
            result += '<p class="alert alert-danger">Either you have not selected any course or no course requirements have been added</p>'
        result += '</div>'
        return result

    @property
    def courses(self):
        from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
        courses = ApplicantSchoolCourse.objects.filter(
            teacherapplication=self
        ).order_by(
            'course__name'
        ).values_list('course__title', 'course__name')

        course_names = [
            f'{cTitle} {cCat}' for cTitle, cCat in courses
        ]
        return ', '.join(course_names)

    @property
    def course_ids(self):
        from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
        course_ids = ApplicantSchoolCourse.objects.filter(
            teacherapplication=self
        ).values_list('course__id')

        return course_ids

    @property
    def status_for_teacher(self):
        if self.status == get_fc_review_status():
            return 'Under Review'

        if self.status in [
            'Denied',
            'Conditionally accepted',
            'Accepted'
        ]:
            return 'Decision Made'

        return self.status

    @property
    def get_status_history(self):
        if not self.status_changed_on:
            self.status_changed_on = {}
            return '-'

        result = ''
        for key, val in self.status_changed_on.items():
            key = key.replace('_', ' ').title()
            result += f'<div class="detail_label">{key}</div><div class="mt-2">{val}</div>'
        return result

    def add_reviewers(self):
        from instructor_app.models.applicant_course_reviewer import ApplicantCourseReviewer
        # for each course applied, get active faculty and add as reviewers
        applied_courses = self.selected_courses
        for applied_course in applied_courses:
            course = applied_course.course

            fc_reviewers = course.get_faculty_coordinators()

            for fc_reviewer in fc_reviewers:
                try:
                    reviewer = ApplicantCourseReviewer(
                        application_course=applied_course,
                        reviewer=fc_reviewer.user
                    )
                    reviewer.save()
                except Exception as e:
                    logger.error(e)
                    ...

    def notify_status_change(self, new_status):
        if new_status.lower() == 'in progress':
            return

        if new_status.lower() == get_fc_review_status().lower():
            self.add_reviewers()


        if new_status.lower() == 'decision made':
            from instructor_app.settings.teacher_application_email import teacher_application_email as tapp_s

            email_settings = tapp_s.from_db()
            internal_recipients = [e.strip() for e in email_settings.get('course_selected_email_recipient', '').split(',') if e.strip()]

            recipient = [self.assigned_to.email] if self.assigned_to else internal_recipients.copy()
            recipient += [e for e in internal_recipients if e not in recipient]

            context_dict = {
                'teacher_first_name': self.user.first_name,
                'teacher_last_name': self.user.last_name,
                'highschool': self.highschool.name,
                'teacher_email': self.user.email,
                'courses': self.courses,
                'application_status': self.status,
            }

            send_notification(
                email_settings.get('app_decision_made_email_subject'),
                email_settings.get('app_decision_made_email'),
                context_dict,
                recipient
            )


        if new_status.lower() == 'submitted':
            from instructor_app.settings.teacher_application_email import teacher_application_email as tapp_s

            email_settings = tapp_s.from_db()
            notify_on = email_settings.get('internal_notify_on', [])
            if 'app_submitted' not in notify_on:
                return

            internal_recipients = [e.strip() for e in email_settings.get('course_selected_email_recipient', '').split(',') if e.strip()]
            recipient = [self.assigned_to.email] if self.assigned_to else internal_recipients.copy()

            # send alerts to course administrator(s)
            course_ids = self.course_ids
            course_admins = Course.get_administrators(course_ids)

            for course_admin in course_admins:
                alert = Alert()
                alert.alert_type = 'new_si_application_submitted'
                alert.recipient = course_admin.user
                link = self.ce_url
                alert.message = f'<a href="{link}">SI application by {self.user.first_name} for {self.courses} has been marked \'{new_status}\'</a>'
                alert.save()

                recipient += [course_admin.user.email]

            recipient += [e for e in internal_recipients if e not in recipient]

            context_dict = {
                'teacher_first_name': self.user.first_name,
                'teacher_last_name': self.user.last_name,
                'highschool': self.highschool.name,
                'teacher_email': self.user.email,
                'courses': self.courses,
                'application_status': self.status,
            }

            send_notification(
                email_settings.get('app_submitted_email_subject'),
                email_settings['app_submitted_email'],
                context_dict,
                recipient
            )

    @property
    def faculty_url(self):
        from cis.utils import getDomain
        url = getDomain() + '/faculty/instructor_apps/application/' + str(self.id)
        return url

    @property
    def missing_items(self):
        missing = []
        if not self.has_selected_course():
            missing.append('Course Selection')

        if not self.has_submitted_ed_bg():
            missing.append('Ed. Background')

        if not self.has_received_recommendation():
            missing.append('Recommendation')

        if not self.has_uploaded_material():
            missing.append('Document(s)')

        return missing

    @property
    def ce_url(self):
        from cis.utils import getDomain
        url = reverse_lazy(
                'ce_instructor_app:teacher_application',
                kwargs={
                    'record_id': self.id
                }
            )
        url = getDomain() + str(url)
        return url

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} / {self.status}"

    class Meta:
        ordering = ['createdon']

    @classmethod
    def get_applications_assigned(cls, user, status=None):
        from instructor_app.models.applicant_course_reviewer import ApplicantCourseReviewer
        pending_app_ids = ApplicantCourseReviewer.objects.filter(
            reviewer=user
        ).distinct('application_course').values_list('application_course__teacherapplication')

        if pending_app_ids:
            return TeacherApplication.objects.filter(
                id__in=pending_app_ids
            )
        return TeacherApplication.objects.none()

    @classmethod
    def create_new(cls, user):
        from datetime import datetime
        record = TeacherApplication(user=user)
        record.createdon = datetime.now().date()

        record.misc_info = {}
        record.save()

        return record

    def can_edit(self):
        return bool(self.status == 'In Progress' or self.status == 'Incomplete')

    def has_selected_course(self):
        from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
        return ApplicantSchoolCourse.objects.filter(
            teacherapplication=self
        ).exists()

    @property
    def selected_courses(self):
        from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
        return ApplicantSchoolCourse.objects.filter(
            teacherapplication=self
        )

    def has_received_recommendation(self):
        from instructor_app.settings.inst_app_language import inst_app_language
        from instructor_app.models.applicant_recommendation import ApplicantRecommendation

        config = inst_app_language.from_db()

        return True if ApplicantRecommendation.objects.filter(
            teacher_application=self
        ).count() >= int(config.get('recommendations_needed', '1')) else False

    def has_recommender_submitted(self, rec_email):
        from instructor_app.models.applicant_recommendation import ApplicantRecommendation
        return True if ApplicantRecommendation.objects.filter(
            teacher_application=self,
            submitter__email__iexact=rec_email
        ).exists() else False

    @property
    def recommendations(self):
        from instructor_app.models.applicant_recommendation import ApplicantRecommendation
        try:
            return ApplicantRecommendation.objects.filter(
                teacher_application=self
            )
        except ApplicantRecommendation.DoesNotExist:
            return ApplicantRecommendation.objects.none()

    def has_submitted_ed_bg(self):
        return True if self.user.education_background else False

    def education_bg(self):
        return self.user.education_background

    @property
    def education_entries(self):
        """Return list of education entry dicts from education_background JSON."""
        ed_bg = self.user.education_background
        if not ed_bg:
            return []
        institutions = ed_bg.get('institution', [])
        degrees = ed_bg.get('degree', [])
        majors = ed_bg.get('major', [])
        entries = []
        for i in range(max(len(institutions), len(degrees), len(majors))):
            inst = institutions[i] if i < len(institutions) else ''
            deg = degrees[i] if i < len(degrees) else ''
            maj = majors[i] if i < len(majors) else ''
            if inst or deg or maj:
                entries.append({'institution': inst, 'degree': deg, 'major': maj})
        return entries

    def has_uploaded_material(self):
        try:
            import itertools
            from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
            from instructor_app.models.application_upload import ApplicationUpload

            files_uploaded = ApplicationUpload.objects.filter(
                teacher_application=self
            ).values_list('associated_with', flat=True)

            assoc_ids = list(
                itertools.chain(*files_uploaded)
            )

            selected_courses = ApplicantSchoolCourse.objects.filter(
                teacherapplication=self
            ).values_list('course__id', flat=True)

            return not CourseAppRequirement.objects.filter(
                course__id__in=selected_courses,
                required='1'
            ).exclude(
                id__in=assoc_ids
            ).exists()
        except:
            return True

    def uploads(self):
        from instructor_app.models.application_upload import ApplicationUpload
        return ApplicationUpload.objects.filter(
            teacher_application=self
        )


    def can_submit(self):
        """
        Checks if application is ready to be submitted
        """

        from instructor_app.settings.inst_app_language import inst_app_language
        app_settings = inst_app_language.from_db()
        if app_settings.get('is_accepting_new', 'No') == 'No':
            return False

        if self.has_selected_course() and self.has_received_recommendation() and self.has_submitted_ed_bg() and self.has_uploaded_material():
            return True
        return False

    @property
    def interested_courses(self):
        from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
        interested_courses = ApplicantSchoolCourse.objects.filter(
            teacherapplication=self
        )

        courses = []
        for interested_course in interested_courses:
            course = {
                'name': interested_course.course.name,
                'status': interested_course.status,
                'id': str(interested_course.id)
            }
            courses.append(course)
        return courses

    def get_recommendation_url(self, email):
        from django.contrib.sites.models import Site
        site = Site.objects.all().first()

        return str(site.domain) + str(
            reverse_lazy(
                'applicant_app:instructor_recommendation',
                kwargs={
                    'record_id': self.id
                }
            )
        ) + "?email="+email

    def update_recommendation_request_info(self, name, email, name2=None, email2=None, name3=None, email3=None):
        from datetime import datetime

        if not self.misc_info:
            self.misc_info = {}

        self.misc_info['recommender_name'] = name
        self.misc_info['recommender_email'] = email

        self.misc_info['recommender_name_2'] = name2
        self.misc_info['recommender_email_2'] = email2

        self.misc_info['recommender_name_3'] = name3
        self.misc_info['recommender_email_3'] = email3

        self.misc_info['recommendation_requested_on'] = datetime.now().strftime('%m/%d/%Y')
        self.save()

    def send_recommendation_request(self, sendto_name, sendto_email):
        from instructor_app.settings.inst_app_language import inst_app_language
        from instructor_app.models.applicant_school_course import ApplicantSchoolCourse

        email_settings = inst_app_language.from_db()

        url = self.get_recommendation_url(sendto_email)
        recommendations = self.recommendations

        rec_emails = [r.submitter.get('email') for r in recommendations]
        if sendto_email in rec_emails:
            return True

        courses = []
        try:
            courses = ApplicantSchoolCourse.objects.filter(
                teacherapplication=self
            ).values_list('course__title', flat=True)
        except ApplicantSchoolCourse.DoesNotExist:
            pass

        send_notification(
            email_settings.get('rec_req_email_subject'),
            email_settings['rec_req_email_message'],
            {
                'recommender_name': sendto_name,
                'teacher_first_name': self.user.first_name,
                'teacher_last_name': self.user.last_name,
                'highschool': self.highschool.name if self.highschool else '',
                'course_titles': ', '.join(courses),
                'recommendation_link': url,
            },
            [sendto_email]
        )
        return True
