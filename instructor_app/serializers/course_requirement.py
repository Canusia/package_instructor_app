from rest_framework import serializers

from cis.models.course import CourseAppRequirement
from cis.serializers.course import CourseSerializer


class CourseAppRequirementSerializer(serializers.ModelSerializer):
    course = CourseSerializer()

    class Meta:
        model = CourseAppRequirement
        fields = '__all__'
        datatables_always_serialize = [
            'course',
            'id'
        ]
