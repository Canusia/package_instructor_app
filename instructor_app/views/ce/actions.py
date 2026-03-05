import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy, reverse

from ...models.teacher_applicant import (
    TeacherApplication,
    ApplicantRecommendation,
    ApplicantCourseReviewer,
    ApplicantSchoolCourse,
    ApplicationUpload
)
from cis.models.note import TeacherApplicationNote

from ...forms.teacher_applicant import (
    ApplicantCourseReviewerForm,
    NoteReplyForm,
    EditSchoolCourseForm,
    AddCourseForm,
    EditTeacherAppCourseUploadForm,
)

logger = logging.getLogger(__name__)


def send_approval_email(request, record_id):
    record = get_object_or_404(TeacherApplication, pk=record_id)
    record.notify_application_approved()
    record.mark_as_approval_notification(request)

    return JsonResponse({
        'status': 'success',
        'message': 'Successfully sent approval notification',
        'action': 'reload'
    })


def view_approval_email(request, record_id):
    template = 'cis/ajax-base.html'
    record = get_object_or_404(TeacherApplication, pk=record_id)

    html_body, text_body = record.get_approval_notification_email()
    return render(
        request,
        template, {
            'ajax_content': html_body,
        }
    )


def download_as_pdf(request, record_id):
    record = get_object_or_404(TeacherApplication, pk=record_id)
    pdf = record.as_pdf(request)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="teacher-application.pdf"'
    return response


def download_files(request, record_id):
    import os
    import zipfile
    from io import BytesIO
    from cis.storage_backend import PrivateMediaStorage

    record = get_object_or_404(TeacherApplication, pk=record_id)
    pdf = record.as_pdf()

    ZIPFILE_NAME = f"{record.user.last_name}-{record.user.first_name}.zip"

    files = ApplicationUpload.objects.filter(
        teacher_application=record
    )

    recommendations = ApplicantRecommendation.objects.filter(
        teacher_application=record
    )

    b = BytesIO()
    with zipfile.ZipFile(b, 'w') as zf:
        zf.writestr('teacher_application.pdf', pdf)

        for current_file in files:
            fh = PrivateMediaStorage().open(current_file.upload.name, "rb")
            zf.writestr(current_file.filename, bytes(fh.read()))

        for current_file in recommendations:
            fh = PrivateMediaStorage().open(current_file.upload.name, "rb")
            zf.writestr(current_file.filename, bytes(fh.read()))

        zf.close()

        response = HttpResponse(b.getvalue(), content_type="application/x-zip-compressed")
        response['Content-Disposition'] = f'attachment; filename={ZIPFILE_NAME}'
        return response


def delete_course(request, record_id):
    record = get_object_or_404(
        ApplicantSchoolCourse,
        pk=record_id
    )

    ApplicantCourseReviewer.objects.filter(
        application_course=record
    ).delete()

    application_id = record.teacherapplication.id
    record.delete()

    return JsonResponse({
        'status': 'success',
        'message': 'Successfully deleted course',
        'redirect': reverse_lazy(
            'ce_instructor_app:teacher_application', kwargs={
                'record_id': application_id
            }
        )
    })


def remind_reviewer(request):
    reviewer_id = request.GET.get('reviewer_id')
    course_review = get_object_or_404(ApplicantCourseReviewer, pk=reviewer_id)
    course_review.notify_reviewer()

    return JsonResponse({
        'status': 'success',
        'message': 'Successfully processed your request'
    })


def update_reviewer_status(request):
    if request.method == 'POST':
        reviewer_id = request.POST.get('reviewer_id')
        status = request.POST.get('status')

        reviewer = get_object_or_404(ApplicantCourseReviewer, pk=reviewer_id)
        if not reviewer.misc_info:
            reviewer.misc_info = {}
        reviewer.status = status
        reviewer.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Reviewer status updated successfully.'
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def do_action(request, record_id):
    action = request.GET.get('action')

    if request.method == 'POST':
        action = request.POST.get('action')

    if action == 'edit_teacher_application_highschool':
        return edit_teacher_application_highschool(request, record_id)

    if action == 'edit_teacher_application_upload':
        return edit_teacher_application_upload(request, record_id)

    if action == 'add_teacher_application_course':
        return add_teacher_application_course(request, record_id)

    if action == 'delete_teacher_application_course':
        return delete_teacher_application_course(request, record_id)

    return JsonResponse({
        'status': 'success',
        'message': 'invalid action passed'
    })


def edit_teacher_application_upload(request, record_id):
    template = 'instructor_app/ce/edit_teacher_application_highschool.html'
    teacher_application = get_object_or_404(TeacherApplication, pk=record_id)

    upload_id = request.GET.get('upload_id')

    if request.method == 'POST':
        upload_id = request.POST.get('id')
        form = EditTeacherAppCourseUploadForm(
            teacher_application=teacher_application,
            upload_id=upload_id,
            data=request.POST
        )

        if form.is_valid():
            form.save(teacher_application)
            return JsonResponse({
                'status': 'success',
                'message': 'Successfully updated record',
                'action': 'reload_page'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }, status=400)

    form = EditTeacherAppCourseUploadForm(
        teacher_application=teacher_application, upload_id=upload_id
    )
    context = {
        'title': 'Update Upload',
        'form': form,
        'form_action': str(reverse_lazy('ce_instructor_app:teacher_app_action', kwargs={'record_id': record_id}))
    }
    return render(request, template, context)


def delete_teacher_application_course(request, record_id):
    application_course = get_object_or_404(ApplicantSchoolCourse, pk=record_id)

    ApplicantCourseReviewer.objects.filter(
        application_course=application_course
    ).delete()

    application_course.delete()

    return JsonResponse({
        'status': 'success',
        'message': 'Successfully removed course',
        'action': 'reload_page'
    })


def add_teacher_application_course(request, record_id):
    template = 'instructor_app/ce/edit_teacher_application_highschool.html'
    teacher_application = get_object_or_404(TeacherApplication, pk=record_id)

    if request.method == 'POST':
        form = AddCourseForm(
            teacher_application=teacher_application,
            data=request.POST
        )

        if form.is_valid():
            form.save(teacher_application)
            return JsonResponse({
                'status': 'success',
                'message': 'Successfully added record',
                'action': 'reload_page'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }, status=400)

    form = AddCourseForm(teacher_application=teacher_application)
    context = {
        'title': 'Add Course',
        'form': form,
        'form_action': str(reverse_lazy('ce_instructor_app:teacher_app_action', kwargs={'record_id': record_id}))
    }
    return render(request, template, context)


def edit_teacher_application_highschool(request, record_id):
    template = 'instructor_app/ce/edit_teacher_application_highschool.html'
    teacher_application = get_object_or_404(TeacherApplication, pk=record_id)

    if request.method == 'POST':
        form = EditSchoolCourseForm(
            teacher_application=teacher_application,
            data=request.POST
        )

        if form.is_valid():
            form.save(teacher_application)
            return JsonResponse({
                'status': 'success',
                'message': 'Successfully updated record',
                'action': 'reload_page'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }, status=400)

    form = EditSchoolCourseForm(teacher_application=teacher_application)
    context = {
        'title': 'Change High School',
        'form': form,
        'form_action': str(reverse_lazy('ce_instructor_app:teacher_app_action', kwargs={'record_id': record_id}))
    }
    return render(request, template, context)


def add_new_course_reviewer(request):
    '''
    Add new reviewer
    '''
    ajax = request.GET.get('ajax', None)
    base_template = 'cis/logged-base.html' if not ajax else 'cis/ajax-base.html'
    template = 'instructor_app/ce/manage_reviewer.html'

    if request.method == 'POST':
        application_course_id = request.POST.get('application_course_id')
        application_course = get_object_or_404(
            ApplicantSchoolCourse,
            pk=application_course_id)

        form = ApplicantCourseReviewerForm(
            application_course,
            request.POST)
        if form.is_valid():
            try:
                course_reviewer = form.save(commit=False)
                course_reviewer.application_course = application_course
                course_reviewer.save()

                return JsonResponse({
                    'status': 'success',
                    'message': 'Successfully saved record',
                    'new_record_id': course_reviewer.id,
                    'new_record_name': '',
                    'action': 'reload'
                })

            except ValueError as e:
                logger.exception('Error adding course reviewer')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Looks like a duplicate entry'
                })

            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Looks like a duplicate entry'
                })

    else:
        application_course_id = request.GET.get('parent')
        application_course = get_object_or_404(ApplicantSchoolCourse, pk=application_course_id)

        initial = {
            'id': '-1',
            'ajax': 1
        }

        form = ApplicantCourseReviewerForm(
            application_course=application_course,
            initial=initial
        )

    return render(
        request,
        template, {
            'form': form,
            'ajax': ajax,
            'record': application_course,
            'base_template': base_template
        })


def reply_to_note(request, note_id):
    note = get_object_or_404(
        TeacherApplicationNote,
        pk=note_id
    )

    replies = TeacherApplicationNote.objects.filter(
        parent=note.id,
        meta__type__in=['public', 'response', 'to_instructor']
    ).order_by(
        '-createdon'
    )

    template = 'instructor_app/ce/note_reply.html'
    form = NoteReplyForm(
        note=note
    )

    if request.method == 'POST':
        form = NoteReplyForm(
            note,
            request.POST
        )

        if form.is_valid():
            reply = form.save(request, note)

            messages.add_message(
                request,
                messages.SUCCESS,
                f'The note has been successfully added.',
                'list-group-item-success'
            )
            return redirect(
                'ce_instructor_app:teacher_app_note_reply',
                note_id=note.id
            )
        messages.add_message(
            request,
            messages.SUCCESS,
            f'Please fix the errors and try again',
            'list-group-item-danger'
        )

    return render(
        request,
        template,
        {
            'form': form,
            'note': note,
            'replies': replies
        })
reply_to_note.login_required = False


def remove_recommendation(request, record_id):
    try:
        rec = ApplicantRecommendation.objects.get(
            pk=record_id
        )
        teacher_application = rec.teacher_application
        rec.delete()

        messages.add_message(
            request,
            messages.SUCCESS,
            f'Successfully removed recommendation.',
            'list-group-item-success')
        return redirect(
            'ce_instructor_app:teacher_application',
            record_id=teacher_application.id
        )
    except Exception:
        messages.add_message(
            request,
            messages.SUCCESS,
            f'Unable to remove recommendation.',
            'list-group-item-error')
        return redirect(
            'ce_instructor_app:teacher_application',
            record_id=teacher_application.id
        )


def remove_upload(request, record_id):
    try:
        upload = ApplicationUpload.objects.get(
            pk=record_id
        )
        teacher_application = upload.teacher_application
        upload.delete()

        messages.add_message(
            request,
            messages.SUCCESS,
            f'Successfully removed file.',
            'list-group-item-success')
        return redirect(
            'ce_instructor_app:teacher_application',
            record_id=teacher_application.id
        )
    except Exception:
        messages.add_message(
            request,
            messages.SUCCESS,
            f'Unable to remove file.',
            'list-group-item-error')
        return redirect(
            'ce_instructor_app:teacher_application',
            record_id=teacher_application.id
        )


def delete_record(request, record_id):
    record = get_object_or_404(
        TeacherApplication,
        pk=record_id
    )

    TeacherApplicationNote.objects.filter(
        teacher_application=record
    ).delete()

    ApplicantRecommendation.objects.filter(
        teacher_application=record
    ).delete()

    ApplicationUpload.objects.filter(
        teacher_application=record
    ).delete()

    ApplicantCourseReviewer.objects.filter(
        application_course__teacherapplication=record
    ).delete()

    ApplicantSchoolCourse.objects.filter(
        teacherapplication=record
    ).delete()

    user = record.user
    record.delete()

    # try to remove base user account if this was the only role
    try:
        user.delete()
    except Exception:
        pass

    return JsonResponse({
        'status': 'success',
        'message': 'Successfully deleted application',
        'redirect': reverse_lazy('ce_instructor_app:teacher_applications')
    })
