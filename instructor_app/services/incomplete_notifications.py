"""
Service: incomplete_notifications
==================================

Core logic for identifying and notifying applicants with incomplete instructor
applications. Decoupled from the management command so the same logic can be
used by the cron command, the CE preview view, and the report export.

Public API
----------
get_pending_notifications() -> list[dict] | str
    Returns either a skip-reason string (if the feature is not active) or a
    list of pending-notification dicts, one per qualifying application:

        {
            'app':                   <TeacherApplication>,
            'missing_items':         ['...', ...],
            'recommenders_to_remind': [{'name': '...', 'email': '...'}, ...],
            'to_email':              'applicant@example.com',
        }

    No side effects — safe to call for preview/report purposes.

send_notifications(pending) -> dict
    Takes the list returned by get_pending_notifications(), sends emails,
    re-sends recommendation requests, updates misc_info, and saves notes.
    Returns a summary dict:

        {
            'sent': 3,
            'detail': { '<app_id>': {'name': '...', 'missing': [...], 'notified': [...]}, ... }
        }
"""

import logging
from datetime import datetime

from django.conf import settings
from django.utils.safestring import mark_safe
from django.template import Context, Template
from django.template.loader import get_template

from mailer import send_html_mail

from cis.models.customuser import CustomUser
from cis.models.note import TeacherApplicationNote

from ..models.teacher_applicant import TeacherApplication
from ..settings.incomplete_si_application import incomplete_si_application

logger = logging.getLogger(__name__)

# Slot definitions for up to 3 recommenders stored in misc_info
_RECOMMENDER_SLOTS = [
    ('recommender_name', 'recommender_email'),
    ('recommender_name_2', 'recommender_email_2'),
    ('recommender_name_3', 'recommender_email_3'),
]


def get_pending_notifications():
    """
    Evaluate which in-progress applications should receive a notification.

    Returns a skip-reason string if the feature is inactive, otherwise a list
    of dicts describing each application that qualifies.  No emails are sent
    and no records are modified.
    """
    from ..settings.inst_app_language import inst_app_language

    app_settings = inst_app_language.from_db()
    if app_settings.get('is_accepting_new', 'No') != 'Yes':
        return 'Not accepting applications — skipped'

    si_settings = incomplete_si_application.from_db()
    if si_settings.get('is_active', 'No') != 'Yes':
        return 'Notification not active — skipped'

    recommendations_needed = int(app_settings.get('recommendations_needed', '1'))
    frequency = int(si_settings.get('frequency', '2'))

    in_progress_apps = TeacherApplication.objects.filter(
        status__iexact='in progress'
    ).select_related('user')

    pending = []

    for app in in_progress_apps:
        misc_info = app.misc_info or {}

        last_notified = misc_info.get('last_notified_on', '10/10/2020')
        if not app.needs_notification(last_notified, frequency):
            continue

        missing_items = []
        recommenders_to_remind = []

        if not app.has_selected_course():
            missing_items.append('Select interested course(s)')
        else:
            if recommendations_needed > 0 and not app.has_received_recommendation():
                item = 'Waiting for recommendation letter'

                for name_key, email_key in _RECOMMENDER_SLOTS:
                    rec_name = misc_info.get(name_key)
                    rec_email = misc_info.get(email_key)
                    if rec_email and not app.has_recommender_submitted(rec_email):
                        recommenders_to_remind.append({'name': rec_name, 'email': rec_email})

                if recommenders_to_remind:
                    names = ', '.join(r['name'] for r in recommenders_to_remind if r['name'])
                    item += f' (Reminder will be sent to: {names})'

                missing_items.append(item)

            if not app.has_submitted_ed_bg():
                missing_items.append('Missing Education Background')
            if not app.has_uploaded_material():
                missing_items.append('Upload supporting materials')

        if not missing_items:
            continue

        debug_mode = getattr(settings, 'DEBUG', True) or si_settings.get('is_active') == 'Debug'
        to_email = si_settings.get('debug_email', 'kadaji@gmail.com') if debug_mode else app.user.email

        pending.append({
            'app': app,
            'missing_items': missing_items,
            'recommenders_to_remind': recommenders_to_remind,
            'to_email': to_email,
        })

    return pending


def send_notifications(pending):
    """
    Send notifications for the list returned by get_pending_notifications().

    Sends emails, re-sends recommendation requests, updates misc_info
    last_notified_on, and saves a private TeacherApplicationNote per
    application.

    Returns a summary dict:
        { 'sent': <int>, 'detail': { '<app_id>': {...}, ... } }
    """
    from ..settings.inst_app_language import inst_app_language

    si_settings = incomplete_si_application.from_db()
    cron_user = CustomUser.objects.get(username='cron')

    subject = si_settings.get('email_subject', '')
    message_tmpl = Template(si_settings.get('email_message', ''))
    wrapper = get_template('cis/email.html')

    sent = 0
    detail = {}

    for entry in pending:
        app = entry['app']
        missing_items = entry['missing_items']
        recommenders_to_remind = entry['recommenders_to_remind']
        to_email = entry['to_email']

        # Re-send recommendation requests
        misc_info = app.misc_info or {}
        for rec in recommenders_to_remind:
            try:
                app.send_recommendation_request(rec['name'], rec['email'])
            except Exception as e:
                logger.error('Failed to send recommendation reminder for app %s: %s', app.id, e)
        if recommenders_to_remind:
            misc_info['recommendation_requested_on'] = datetime.now().strftime('%m/%d/%Y')

        # Render email body
        context = Context({
            'missing_items': mark_safe('<br>'.join(missing_items)),
            'teacher_first_name': app.user.first_name,
            'teacher_last_name': app.user.last_name,
        })
        text_body = message_tmpl.render(context)
        html_body = wrapper.render({'message': text_body})

        # Send notification
        send_html_mail(subject, text_body, html_body, settings.DEFAULT_FROM_EMAIL, [to_email])

        # Update misc_info and save
        misc_info['last_notified_on'] = datetime.now().strftime('%m/%d/%Y')
        app.misc_info = misc_info
        app.save()

        # Log a private note
        TeacherApplicationNote(
            teacher_application_id=app.id,
            note=text_body,
            createdby=cron_user,
            meta={'type': 'Private'},
        ).save()

        detail[str(app.id)] = {
            'name': str(app.user),
            'missing': missing_items,
            'notified': [to_email],
        }
        sent += 1

    return {'sent': sent, 'detail': detail}
