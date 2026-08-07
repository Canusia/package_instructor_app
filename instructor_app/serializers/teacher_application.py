from django.contrib.auth import get_user_model
from rest_framework import serializers


from ..models.teacher_applicant import (
    TeacherApplicant,
    TeacherApplication,
    ApplicantSchoolCourse,
    ApplicantRecommendation,
    ApplicationUpload,
    ApplicantCourseReviewer
)

from cis.serializers.term import AcademicYearSerializer
from cis.serializers.highschool_admin import CustomUserSerializer
from cis.serializers.highschool import HighSchoolSerializer
from cis.serializers.course import CourseSerializer

class TeacherApplicantSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    verify_email_url = serializers.CharField(read_only=True)
    status_label = serializers.SerializerMethodField()
    revoke_url = serializers.SerializerMethodField()

    class Meta:
        model = TeacherApplicant
        fields = '__all__'

        datatables_always_serialize = [
            'id',
            'verify_email_url',
            'status_label',
            'revoke_url',
        ]

    def get_status_label(self, obj):
        return obj.get_status_display()

    def get_revoke_url(self, obj):
        # CustomUserSerializer does not expose the user id, so the Applicants
        # tab gets a ready-made URL rather than building one client-side.
        from django.urls import reverse

        return reverse(
            'ce_instructor_app:revoke_applicant_access',
            kwargs={'user_id': obj.user_id}
        )


class TeacherApplicationSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    assigned_to = CustomUserSerializer()
    highschool = HighSchoolSerializer()
    createdon = serializers.DateField(format='%Y-%m-%d')

    courses = serializers.CharField(
        read_only=True
    )

    ce_url = serializers.CharField(
        read_only=True
    )

    attending_si_year = serializers.CharField(
        read_only=True
    )

    missing_items = serializers.ListField(read_only=True, allow_empty=True)
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = TeacherApplication
        fields = '__all__'

        datatables_always_serialize = [
            'id',
            'ce_url',
            'missing_items',
            'attending_si_year',
            'status_label',
        ]

    def get_status_label(self, obj):
        return obj.get_status_display()

class ApplicantCourseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for applicant-facing course list."""
    course_name = serializers.SerializerMethodField()
    highschool_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicantSchoolCourse
        fields = ['id', 'course_name', 'highschool_name']
        datatables_always_serialize = ['id']

    def get_course_name(self, obj):
        return str(obj.course) if obj.course else ''

    def get_highschool_name(self, obj):
        return str(obj.highschool) if obj.highschool else ''


class ApplicantSchoolCourseSerializer(serializers.ModelSerializer):
    teacherapplication = TeacherApplicationSerializer()
    course = CourseSerializer()
    highschool = HighSchoolSerializer()
    starting_academic_year = AcademicYearSerializer()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = ApplicantSchoolCourse
        fields = '__all__'

    def get_status_label(self, obj):
        return obj.get_status_display()

class ApplicantCourseReviewerSerializer(serializers.ModelSerializer):
    reviewer = CustomUserSerializer()
    application_course = ApplicantSchoolCourseSerializer()
    status_label = serializers.SerializerMethodField()

    assigned_on = serializers.DateField(format='%m/%d/%Y')
    class Meta:
        model = ApplicantCourseReviewer
        fields = '__all__'

    def get_status_label(self, obj):
        return obj.get_status_display()
