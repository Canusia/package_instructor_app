from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from cis.menu import cis_menu, draw_menu

from ...services.pending_review_notifications import (
    get_pending_review_notifications,
    send_pending_review_notifications,
)


def preview(request):
    """
    CE staff view — preview or trigger pending-review notifications.

    GET:  Shows which reviewers would be reminded. No side effects.
    POST: Sends the notifications immediately and redirects with a summary.
    """
    menu = draw_menu(cis_menu, 'instructors', 'pending_review_notifications')

    if request.method == 'POST':
        pending = get_pending_review_notifications()
        result = send_pending_review_notifications(pending)
        messages.success(request, f'{result["sent"]} notification(s) sent.')
        return redirect(reverse('ce_instructor_app:pending_review_notifications'))

    pending = get_pending_review_notifications()

    return render(request, 'instructor_app/ce/pending_review_notifications.html', {
        'page_title': 'Pending Review Notifications',
        'menu': menu,
        'pending': pending,
    })
