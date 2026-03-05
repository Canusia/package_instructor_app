from django.http import JsonResponse

from ...models.teacher_applicant import (
    TeacherApplicant,
    TeacherApplication,
)


def do_bulk_action(request):
    action = request.GET.get('action')

    if request.method == 'POST':
        action = request.POST.get('action')

    if action == 'resend_verification_link':
        return resend_verification_link(request)

    if action == 'get_verification_link':
        return get_verification_link(request)

    return JsonResponse({
        'status': 'success',
        'message': 'invalid action passed'
    })


def _get_applicants_from_ids(ids):
    """Resolve IDs to TeacherApplicant records.
    IDs may be TeacherApplication IDs or TeacherApplicant IDs."""
    applicants = []
    # Try as TeacherApplication IDs first
    applications = TeacherApplication.objects.filter(id__in=ids)
    for app in applications:
        try:
            applicants.append(app.user.teacherapplicant)
        except TeacherApplicant.DoesNotExist:
            continue
    # Also try as TeacherApplicant IDs directly
    direct = TeacherApplicant.objects.filter(id__in=ids)
    existing_ids = {a.id for a in applicants}
    for a in direct:
        if a.id not in existing_ids:
            applicants.append(a)
    return applicants


def resend_verification_link(request):
    ids = request.GET.getlist('ids[]')
    applicants = _get_applicants_from_ids(ids)

    recipient_list = []
    for applicant in applicants:
        if not applicant.account_verified:
            applicant.send_verification_request_email()
            recipient_list.append(applicant.user.email)

    data = {
        'status': 'success',
        'message': 'Successfully sent email(s) to <br>' + '<br>'.join(recipient_list),
        'action': 'display'
    }
    if len(recipient_list) == 0:
        data['message'] = 'No applicants pending account verification found.'

    return JsonResponse(data)


def get_verification_link(request):
    ids = request.GET.getlist('ids[]')
    applicants = _get_applicants_from_ids(ids)

    recipient_list = []
    index = 1
    for applicant in applicants:
        if not applicant.account_verified:
            recipient_list.append(
                f'{applicant.user}<br><span id=\'copy_to_{index}\'>{applicant.verify_email_url}</span>'
                f'&nbsp;&nbsp;<i title=\'copy to clipboard\' class=\'fas fa fa-paste copy-clipboard\' '
                f'data-clipboard-target=\'#copy_to_{index}\' style=\'cursor: pointer\'></i>'
            )
            index += 1

    data = {
        'status': 'success',
        'message': 'Verification Links are below<br><br>' + '<br>'.join(recipient_list),
        'action': 'display'
    }
    if len(recipient_list) == 0:
        data['message'] = 'No applicants pending account verification found.'

    return JsonResponse(data)
