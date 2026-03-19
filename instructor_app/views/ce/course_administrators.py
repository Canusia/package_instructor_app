from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse

from rest_framework import viewsets

from cis.models.course import Course, CourseAdministrator
from cis.forms.course import CourseAdministratorForm
from cis.utils import CIS_user_only, FACULTY_user_only

from ...serializers.course_administrator import CourseAdministratorSerializer


class CourseAdministratorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseAdministratorSerializer
    permission_classes = [CIS_user_only | FACULTY_user_only]

    def get_queryset(self):
        course_id = self.request.GET.get('course_id')
        status = self.request.GET.get('status', 'active')
        faculty_coordinator_user_id = self.request.GET.get('faculty_coordinator_user_id')

        if course_id:
            return CourseAdministrator.objects.filter(
                course__id=course_id,
                status__iexact='active'
            )

        if faculty_coordinator_user_id:
            return CourseAdministrator.objects.filter(
                user__id=faculty_coordinator_user_id
            )

        return CourseAdministrator.objects.all()


def manage_course_administrator_role(request):

    ajax = request.GET.get('ajax', None)
    base_template = 'cis/logged-base.html' if not ajax else 'cis/ajax-base.html'
    template = 'cis/course/manage_administrator.html'

    course = None
    course_admin = None

    if request.method == 'POST':
        id = request.POST.get('id')

        course_admin = None

        if id != '-1':
            course_admin = get_object_or_404(
                CourseAdministrator, pk=id
            )

        form = CourseAdministratorForm(
                id=id,
                course=None,
                data=request.POST,
                instance=course_admin
            )

        if form.is_valid():
            course_admin = form.save(request, commit=True)

            data = {
                'status': 'success',
                'message': 'Successfully saved record',
                'new_record_id': course_admin.id,
                'new_record_name': course_admin.user.first_name,
                'action': 'reload'
            }
            return JsonResponse(data)
        else:
            data = {
                'status': 'error',
                'message': 'Please correct the errors and try again',
                'errors': form.errors
            }
            return JsonResponse(data)
    else:
        course_admin_id = request.GET.get('id')
        course_id = request.GET.get('parent')
        if course_id:
            course = get_object_or_404(Course, pk=course_id)

        if course_admin_id != '-1':
            course_admin = get_object_or_404(
                CourseAdministrator, pk=course_admin_id
            )
        form = CourseAdministratorForm(
            id=course_admin_id,
            course=course,
            instance=course_admin
        )
    return render(
        request,
        template, {
            'form': form,
            'ajax': ajax,
            'record': course_admin,
            'base_template': base_template
        })


def delete_course_administrator_role(request, record_id):
    record = get_object_or_404(CourseAdministrator, pk=record_id)

    try:
        record.delete()

        data = {
            'status': 'success',
            'message': 'Successfully deleted record',
            'action': 'reload'
        }
    except Exception as e:
        data = {
            'status': 'error',
            'message': 'Unable to complete request.' + str(e),
        }
    return JsonResponse(data)
