import logging
from django.conf import settings

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.contrib.sites.models import Site

from django.template import Context, Template
from django.template.loader import get_template, render_to_string

from mailer import send_mail, send_html_mail

from ..models.teacher_applicant import (
    TeacherApplication, ApplicantSchoolCourse,
    ApplicantRecommendation,
    ApplicantCourseReviewer,
    get_fc_review_status
)
from ..models.teacher_application_note import TeacherApplicationNote

from ..settings.teacher_application_email import (
    teacher_application_email as tapp_settings,
)
from cis.settings.notes_email import notes_email

from ..settings.inst_app_language import (
    inst_app_language as inst_app_page_settings
)

from alerts.models import Alert

logger = logging.getLogger(__name__)


def _add_system_note(teacher_application, note_text, createdby=None):
    """Create a private system note on a TeacherApplication."""
    try:
        TeacherApplicationNote.objects.create(
            teacher_application=teacher_application,
            note=note_text,
            createdby=createdby,
            meta={'type': 'private'}
        )
    except Exception:
        logger.exception('Error creating system note for application %s', teacher_application.pk)


@receiver(post_save, sender=ApplicantCourseReviewer)
def assign_new_reviewer(sender, instance, created, **kwargs):
    """
    Send email to reviewer
    """
    app = instance.application_course.teacherapplication
    reviewer_name = f'{instance.reviewer.first_name} {instance.reviewer.last_name}'
    course_name = str(instance.application_course.course)

    if created:
        _add_system_note(
            app,
            f'Reviewer {reviewer_name} added for course {course_name}.',
        )
    else:
        instance.notify_status_change(instance.status)
        if instance.status != '---':
            _add_system_note(
                app,
                f'Reviewer {reviewer_name} submitted decision "{instance.status}" for course {course_name}.',
                createdby=instance.reviewer,
            )

@receiver(post_save, sender=ApplicantRecommendation)
def create_new_recommendation(sender, instance, created, **kwargs):
    """
    Send confirmation email to applicant when new recommendation has been created
    """
    if created:
        email_settings = inst_app_page_settings.from_db()

        # from_db() returns {} when the setting was never registered -- a
        # fresh environment, or a tenant stood up before register_settings
        # runs. This is a post_save receiver, so the KeyError escaped the
        # caller's save() after the row had been written (Canusia/ewu#74).
        # An unconfigured template means no notification -- logged, not a
        # blank email.
        message = email_settings.get('rec_received_email_message')
        if not message:
            logger.warning(
                'inst_app_language.rec_received_email_message is not configured; '
                'skipping the email for %s', instance.teacher_application_id)
            return

        email_template = Template(message)

        context = Context({
            'teacher_first_name': instance.teacher_application.user.first_name,
            'teacher_last_name': instance.teacher_application.user.last_name,
            'email': instance.teacher_application.user.email,
            'recommender_name': instance.submitter.get('name'),
        })
        text_body = email_template.render(context)
        to = [instance.teacher_application.user.email]

        if instance.submitter.get('email'):
            to.append(
                instance.submitter.get('email')
            )
        
        template = get_template('cis/email.html')
        html_body = template.render({
            'message': text_body
        })

        if getattr(settings, 'DEBUG', True):
            to = ['kadaji@gmail.com']

        subject = email_settings.get('rec_received_email_subject')

        send_html_mail(
            subject,
            text_body,
            html_body,
            settings.DEFAULT_FROM_EMAIL,
            to
        )

@receiver(pre_save, sender=ApplicantCourseReviewer)
def course_reviewer_status_updated(sender, instance, **kwargs):
    """Record each reviewer status change into status_changed_on.

    The faculty review page's "Recommendation History" renders
    ApplicantCourseReviewer.get_status_history, which reads status_changed_on.
    Without this the field is never written, so the history is always blank.
    Kept minimal (no notifications) — the review view owns those side effects.
    """
    from datetime import datetime

    previous_status = instance.tracker.previous('status')
    status = instance.status

    # No change, or still the "not yet reviewed" placeholder — nothing to log.
    if previous_status == status or status in (None, '', '---'):
        return

    status_changed_on = instance.status_changed_on or {}
    status_changed_on[datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')] = status
    instance.status_changed_on = status_changed_on


@receiver(pre_save, sender=TeacherApplication)
def teacher_app_status_updated(sender, instance, **kwargs):
    from datetime import datetime

    previous_status = instance.tracker.previous('status')
    status = instance.status

    if previous_status != status:
        status_changed_on = instance.status_changed_on
        if not status_changed_on:
            status_changed_on = {}

        status_changed_on[datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')] = status

        instance.status_changed_on = status_changed_on

        # call notifications method
        instance.notify_status_change(status)

        _add_system_note(
            instance,
            f'Status changed from "{previous_status}" to "{status}".',
            createdby=instance.assigned_to,
        )

        if previous_status == 'Submitted':
            # course admin changes this
            # get all alerts where type = new_si_application_submitted
            Alert.objects.filter(
                alert_type='new_si_application_submitted',
                read_on__isnull=True,
                message__contains=str(instance.id)
            ).update(
                read_on=datetime.now()
            )

        if previous_status == get_fc_review_status():
            # course admin changes this
            # get all alerts where type = new_si_application_submitted
            Alert.objects.filter(
                alert_type='si_application_reviewed',
                read_on__isnull=True,
                message__contains=str(instance.id)
            ).update(
                read_on=datetime.now()
            )

@receiver(post_save, sender=TeacherApplication)
def create_new_application(sender, instance, created, **kwargs):
    """
    Send confirmation email to applicant when new application has been created
    """
    if created:
        email_settings = tapp_settings.from_db()

        # from_db() returns {} when the setting was never registered -- a
        # fresh environment, or a tenant stood up before register_settings
        # runs. This is a post_save receiver, so the KeyError escaped the
        # caller's save() after the row had been written (Canusia/ewu#74).
        # An unconfigured template means no notification -- logged, not a
        # blank email.
        message = email_settings.get('new_applicant_email')
        if not message:
            logger.warning(
                'teacher_application_email.new_applicant_email is not configured; '
                'skipping the email for %s', instance.id)
            return

        email_template = Template(message)

        context = Context({
            'first_name': instance.user.first_name,
            'last_name': instance.user.last_name,
            'email': instance.user.email
        })
        text_body = email_template.render(context)
        to = [instance.user.email]

        template = get_template('cis/email.html')
        html_body = template.render({
            'message': text_body
        })

        if getattr(settings, 'DEBUG', True):
            to = ['kadaji@gmail.com']

        subject = email_settings.get('new_applicant_email_subject')

        send_html_mail(
            subject,
            text_body,
            html_body,
            settings.DEFAULT_FROM_EMAIL,
            to
        )

@receiver(post_save, sender=ApplicantSchoolCourse)
def selected_new_course(sender, instance, created, **kwargs):
    """
    Send notification email when a course is added to an application
    """
    if created:
        email_settings = tapp_settings.from_db()
        notify_on = email_settings.get('internal_notify_on', [])
        if 'course_added' not in notify_on:
            return
        # from_db() returns {} when the setting was never registered -- a
        # fresh environment, or a tenant stood up before register_settings
        # runs. This is a post_save receiver, so the KeyError escaped the
        # caller's save() after the row had been written (Canusia/ewu#74).
        # An unconfigured template means no notification -- logged, not a
        # blank email.
        message = email_settings.get('course_selected_email')
        if not message:
            logger.warning(
                'teacher_application_email.course_selected_email is not configured; '
                'skipping the email for %s', instance.id)
            return

        email_template = Template(message)

        context = Context({
            'teacher_first_name': instance.teacherapplication.user.first_name,
            'teacher_last_name': instance.teacherapplication.user.last_name,
            'teacher_email': instance.teacherapplication.user.email,
            'application_url': instance.teacherapplication.ce_url,
            'course': instance.course,
            'highschool': instance.course
        })
        text_body = email_template.render(context)
        to = [e.strip() for e in email_settings.get('course_selected_email_recipient', '').split(',') if e.strip()]

        template = get_template('cis/email.html')
        html_body = template.render({
            'message': text_body
        })

        if getattr(settings, 'DEBUG', True) or not to:
            to = ['kadaji@gmail.com']

        subject = email_settings.get('course_selected_email_subject')

        send_html_mail(
            subject,
            text_body,
            html_body,
            settings.DEFAULT_FROM_EMAIL,
            to
        )


@receiver(post_save, sender=TeacherApplicationNote)
def teacher_application_note_added(sender, instance, created, **kwargs):
    """
    Handle post-save actions for TeacherApplicationNote.

    - type='to_instructor': email the applicant with the note content and a reply link.
    - type='response': create an alert for the original note author.
    """
    if not created or not instance.meta:
        return

    note_type = instance.meta.get('type')

    if note_type == 'response':
        if not instance.parent:
            return
        try:
            parent_note = TeacherApplicationNote.objects.get(pk=instance.parent)
            alert = Alert()
            alert.alert_type = 'si_app_note_response'
            alert.recipient = parent_note.createdby
            link = str(instance.teacher_application.ce_url) + '#notes'
            alert.message = f'<a class="display_in_modal" href="{link}">New note added by {instance.createdby}'
            alert.save()
        except TeacherApplicationNote.DoesNotExist:
            pass

    if note_type == 'to_instructor':
        email_settings = notes_email.from_db()

        if email_settings.get('is_active', 'No') == 'No':
            return

        # from_db() returns {} when the setting was never registered -- a
        # fresh environment, or a tenant stood up before register_settings
        # runs. This is a post_save receiver, so the KeyError escaped the
        # caller's save() after the row had been written (Canusia/ewu#74).
        # An unconfigured template means no notification -- logged, not a
        # blank email.
        message = email_settings.get('teacherapplication_note_to_instructor_email')
        if not message:
            logger.warning(
                'teacherapplication_notes_email.teacherapplication_note_to_instructor_email is not configured; '
                'skipping the email for %s', instance.id)
            return

        email_template = Template(message)
        subject = email_settings.get('teacherapplication_note_to_instructor_subject')
        to = [instance.teacher_application.user.email]

        context = Context({
            'note': instance.note,
            'instructor_first_name': instance.teacher_application.user.first_name,
            'instructor_last_name': instance.teacher_application.user.last_name,
            'reply_url': instance.teacher_reply_url,
        })

        text_body = email_template.render(context)
        html_body = get_template('cis/email.html').render({'message': text_body})

        if getattr(settings, 'DEBUG', True):
            to = ['kadaji@gmail.com']

        if email_settings.get('is_active') == 'Debug':
            to = ['avi@canusia.com']

        send_html_mail(
            subject,
            text_body,
            html_body,
            settings.DEFAULT_FROM_EMAIL,
            to
        )
