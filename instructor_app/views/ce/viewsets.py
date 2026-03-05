from django.db.models import Q

from rest_framework import viewsets

from instructor_app.models.teacher_applicant import (
    TeacherApplicant,
    TeacherApplication,
    ApplicantCourseReviewer,
    ApplicantSchoolCourse,
)
from cis.models.course import Course
from cis.models.term import AcademicYear

from instructor_app.serializers.teacher_application import (
    TeacherApplicantSerializer,
    TeacherApplicationSerializer,
    ApplicantCourseReviewerSerializer,
    ApplicantCourseListSerializer,
)

from cis.utils import CIS_user_only, FACULTY_user_only, HSADMIN_user_only


class TeacherApplicantViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeacherApplicantSerializer
    permission_classes = [CIS_user_only | FACULTY_user_only | HSADMIN_user_only]

    def get_queryset(self):
        records = TeacherApplicant.objects.all()
        pending_only = self.request.GET.get('pending_only', '').strip()
        if pending_only:
            records = records.filter(account_verified=False)
        return records


class ApplicantCourseListViewSet(viewsets.ReadOnlyModelViewSet):
    """Applicant-facing ViewSet for their selected courses."""
    serializer_class = ApplicantCourseListSerializer

    def get_queryset(self):
        teacher_application_id = self.request.GET.get('teacher_application_id', '').strip()
        if teacher_application_id:
            return ApplicantSchoolCourse.objects.filter(
                teacherapplication__id=teacher_application_id,
                teacherapplication__user=self.request.user
            )
        return ApplicantSchoolCourse.objects.none()


class TeacherApplicationReviewerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ApplicantCourseReviewerSerializer
    permission_classes = [CIS_user_only | FACULTY_user_only | HSADMIN_user_only]

    def get_queryset(self):
        teacher_application_status = self.request.GET.get('status', '').strip()
        review_status = self.request.GET.get('course_review_status', '').strip()
        course_id = self.request.GET.get('course', '').strip()

        records = ApplicantCourseReviewer.objects.all()

        if teacher_application_status:
            records = records.filter(
                application_course__teacherapplication__status__iexact=teacher_application_status
            )

        if review_status:
            records = records.filter(
                status__iexact=review_status
            )

        if course_id:
            if course_id == '-2':
                course_ids = self.request.user.get_courses_overseeing()
                cohort_apps = ApplicantSchoolCourse.objects.filter(
                    course__id__in=course_ids
                ).values_list('teacherapplication__id', flat=True)
            else:
                cohort_apps = ApplicantSchoolCourse.objects.filter(
                    course__id=course_id
                ).values_list('teacherapplication__id', flat=True)

            records = records.filter(
                application_course__teacherapplication__id__in=cohort_apps
            )
        return records


class TeacherApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeacherApplicationSerializer
    permission_classes = [CIS_user_only | FACULTY_user_only | HSADMIN_user_only]

    def get_queryset(self):
        status = self.request.GET.get('status', '').strip()
        course_status = self.request.GET.get('course_status', '').strip()
        cohort_id = self.request.GET.get('cohort', '').strip()
        course_id = self.request.GET.get('course', '').strip()
        active_only = self.request.GET.get('active_only', '').strip()
        reviewer = self.request.GET.get('reviewer')
        academic_year_id = self.request.GET.get('academic_year', '').strip()

        records = TeacherApplication.objects.none()
        if active_only:
            active_status = []
            for app_status, label in TeacherApplication.STATUS_OPTIONS:
                if app_status not in ['Withdrawn', 'Closed']:
                    active_status.append(app_status)
            records = TeacherApplication.objects.filter(
                status__in=active_status
            )
        else:
            records = TeacherApplication.objects.all()

        if academic_year_id:
            records = records.filter(
                Q(misc_info__participating_acad_year=academic_year_id) |
                Q(misc_info__participating_acad_year__isnull=True)
            )

        if reviewer:
            assigned_to = ApplicantCourseReviewer.objects.filter(
                reviewer__id=reviewer
            ).distinct(
                'application_course__teacherapplication__id'
            ).values_list(
                'application_course__teacherapplication__id', flat=True
            )
            records = records.filter(
                id__in=assigned_to
            )

        if course_status:
            app_ids = ApplicantSchoolCourse.objects.filter(
                status=course_status
            ).distinct('teacherapplication').values_list('teacherapplication__id', flat=True)

            records = records.filter(
                pk__in=app_ids
            )

        if status:
            records = records.filter(
                status=status
            )

        if cohort_id:
            cohort_apps = ApplicantSchoolCourse.objects.filter(
                course__cohort__id=cohort_id
            ).values_list('teacherapplication__id', flat=True)

            records = records.filter(
                id__in=cohort_apps
            )

        if course_id:
            if course_id == '-2':
                course_ids = self.request.user.get_courses_overseeing()
                cohort_apps = ApplicantSchoolCourse.objects.filter(
                    course__id__in=course_ids
                ).values_list('teacherapplication__id', flat=True)
            else:
                cohort_apps = ApplicantSchoolCourse.objects.filter(
                    course__id=course_id
                ).values_list('teacherapplication__id', flat=True)

            records = records.filter(
                id__in=cohort_apps
            )
        return records
