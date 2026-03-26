from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.urls import reverse

from rest_framework import viewsets

from cis.models.course import CourseAppRequirement
from ...forms.course_requirements import (
    AddCourseAppRequirementForm,
    UpdateCourseRequirementForm,
    DeleteCourseRequirementForm,
)
from cis.utils import CIS_user_only

from ...serializers.course_requirement import CourseAppRequirementSerializer


class CourseAppRequirementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseAppRequirementSerializer
    permission_classes = [CIS_user_only]

    def get_queryset(self):
        course_id = self.request.GET.get('course_id')
        if course_id:
            return CourseAppRequirement.objects.filter(
                course__id=course_id
            )
        return CourseAppRequirement.objects.all()


def do_bulk_action(request):
    action = request.GET.get('action')

    if request.method == 'POST':
        action = request.POST.get('action')

    if action == 'add_new_req':
        return add_new_req(request)

    if action == 'update_req_status':
        return update_req_status(request)

    if action == 'delete_req':
        return delete_req(request)

    data = {
        'status': 'success',
        'message': 'invalid action passed'
    }
    return JsonResponse(data)


def add_new_req(request):
    template = 'cis/course/update_si_availability.html'

    if request.method == 'POST':

        form = AddCourseAppRequirementForm(data=request.POST)
        if form.is_valid():
            status = form.save(request)

            data = {
                'status': 'success',
                'message': 'Successfully processed request',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status': 'error',
                'message': 'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    form = AddCourseAppRequirementForm()
    context = {
        'title': 'Add Course Application Requirement',
        'intro': '<p class="alert alert-info">This will add a new course application requirement to the selected courses.</p>',
        'form': form,
        'form_action': str(reverse('ce_instructor_app:course_req_bulk_actions'))
    }

    return render(request, template, context)


def update_req_status(request):
    template = 'cis/course/update_si_availability.html'

    if request.method == 'POST':

        form = UpdateCourseRequirementForm(data=request.POST)

        if form.is_valid():
            status = form.save(request)

            data = {
                'status': 'success',
                'message': 'Successfully updated records',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status': 'error',
                'message': 'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    ids = request.GET.getlist('ids[]')
    form = UpdateCourseRequirementForm(ids)
    context = {
        'title': 'Change New School & SI Availability',
        'form': form
    }

    return render(request, template, context)


def delete_req(request):
    template = 'cis/course/update_si_availability.html'

    if request.method == 'POST':

        form = DeleteCourseRequirementForm(data=request.POST)

        if form.is_valid():
            status = form.save(request)

            data = {
                'status': 'success',
                'message': 'Successfully updated records',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status': 'error',
                'message': 'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    ids = request.GET.getlist('ids[]')
    form = DeleteCourseRequirementForm(ids)
    context = {
        'title': 'Delete Course Application Requirement',
        'form': form
    }

    return render(request, template, context)
