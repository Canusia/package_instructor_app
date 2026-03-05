from django.contrib.auth import get_user_model
from rest_framework import serializers


from instructor_app.models.teacher_applicant import (
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

    class Meta:
        model = TeacherApplicant
        fields = '__all__'

        datatables_always_serialize = [
            'id',
            'verify_email_url',
        ]


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

    class Meta:
        model = TeacherApplication
        fields = '__all__'

        datatables_always_serialize = [
            'id',
            'ce_url',
            'missing_items',
            'attending_si_year',
        ]

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

    class Meta:
        model = ApplicantSchoolCourse
        fields = '__all__'
        
class ApplicantCourseReviewerSerializer(serializers.ModelSerializer):
    reviewer = CustomUserSerializer()
    application_course = ApplicantSchoolCourseSerializer()

    assigned_on = serializers.DateField(format='%m/%d/%Y')
    class Meta:
        model = ApplicantCourseReviewer
        fields = '__all__'
