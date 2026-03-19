from rest_framework import serializers

from cis.models.course import CourseAdministrator
from cis.serializers.course import CourseSerializer
from cis.serializers.highschool_admin import CustomUserSerializer


class CourseAdministratorSerializer(serializers.ModelSerializer):
    course = CourseSerializer()
    user = CustomUserSerializer()

    faculty_id = serializers.CharField(
        read_only=True
    )

    class Meta:
        model = CourseAdministrator
        fields = '__all__'

        datatables_always_serialize = [
            'faculty_id'
        ]
