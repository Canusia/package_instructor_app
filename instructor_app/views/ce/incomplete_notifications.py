from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from cis.menu import cis_menu, draw_menu

from ...services.incomplete_notifications import get_pending_notifications, send_notifications


def preview(request):
    """
    CE staff view — preview or trigger incomplete-application notifications.

    GET:  Shows who would be notified and what is missing. No side effects.
    POST: Sends the notifications immediately and redirects back with a summary.
    """
    menu = draw_menu(cis_menu, 'instructors', 'incomplete_notifications')

    if request.method == 'POST':
        pending = get_pending_notifications()
        if isinstance(pending, str):
            messages.warning(request, pending)
        else:
            result = send_notifications(pending)
            messages.success(request, f'{result["sent"]} notification(s) sent.')
        return redirect(reverse('ce_instructor_app:incomplete_notifications'))

    pending = get_pending_notifications()

    skip_reason = None
    if isinstance(pending, str):
        skip_reason = pending
        pending = []

    return render(request, 'instructor_app/ce/incomplete_notifications.html', {
        'page_title': 'Incomplete Application Notifications',
        'menu': menu,
        'pending': pending,
        'skip_reason': skip_reason,
    })
