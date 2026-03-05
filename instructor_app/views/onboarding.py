"""
Instructor applicant onboarding views for new teacher registration flow.

Flow: start_app -> awaiting_verification -> verify_email -> complete_signup -> dashboard
"""
import logging
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.db import IntegrityError
from django.contrib import messages, auth

from instructor_app.models.teacher_applicant import TeacherApplicant, TeacherApplication
from instructor_app.forms.teacher_applicant import (
    TeacherApplicantVerifyEmailForm,
    TeacherApplicantVerifyAccountForm,
    TeacherApplicantProfileForm,
)
from instructor_app.settings.inst_app_language import inst_app_language

logger = logging.getLogger(__name__)


def _get_app_settings():
    """Return inst_app_language settings dict."""
    return inst_app_language.from_db()


def _is_accepting_applications(app_settings=None):
    """Check if instructor applications are currently being accepted."""
    if app_settings is None:
        app_settings = _get_app_settings()
    return app_settings.get('is_accepting_new', 'No') == 'Yes'


def start_app(request):
    """
    Entry point for new instructor applicant accounts.

    Collects name and email, creates an unverified TeacherApplicant record,
    sends verification email, and redirects to awaiting_verification page.

    Public view (login_required = False).
    """
    app_settings = _get_app_settings()
    accepting = _is_accepting_applications(app_settings)
    closed_message = '' if accepting else app_settings.get('closed_message', '-')
    signup_intro = app_settings.get('signup_intro', '')

    if not accepting:
        return render(
            request,
            'instructor_app/start-app.html',
            {
                'accepting_applications': False,
                'closed_message': closed_message,
                'signup_intro': signup_intro,
            })

    if request.method == 'POST':
        form = TeacherApplicantVerifyEmailForm(request.POST)

        if form.is_valid():
            try:
                applicant = form.save()

                if applicant is None:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        'Unable to create account. Please try again or contact support.',
                        'list-group-item-danger')
                else:
                    applicant.send_verification_request_email()
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        'Your account has been created. Please check your email to verify your address.',
                        'list-group-item-success')
                    return redirect('applicant_app:awaiting_verification')
            except IntegrityError as e:
                form._errors['email'] = [str(e)]
        else:
            messages.add_message(
                request,
                messages.ERROR,
                'Please correct the errors below and try again.',
                'list-group-item-danger')
    else:
        form = TeacherApplicantVerifyEmailForm()

    return render(
        request,
        'instructor_app/start-app.html',
        {
            'form': form,
            'accepting_applications': True,
            'signup_intro': signup_intro,
        })


start_app.login_required = False


def awaiting_verification(request):
    """
    Display message after applicant submits email in start_app.

    Shows instructions to check email for the verification link.

    Public view (login_required = False).
    """
    app_settings = _get_app_settings()
    intro = app_settings.get('awaiting_verify_intro', '')

    return render(
        request,
        'instructor_app/awaiting_verification.html',
        {
            'intro': intro,
        })


awaiting_verification.login_required = False


def verify_email(request, verification_id):
    """
    Handle email verification link clicks.

    Validates the verification token, marks the account as verified,
    and redirects to complete_signup.

    Public view (login_required = False).
    """
    applicant = TeacherApplicant.objects.filter(verification_id=verification_id)

    if not applicant:
        messages.add_message(
            request,
            messages.ERROR,
            'This verification link is invalid or has expired. Please start a new application.',
            'list-group-item-danger')
        return redirect('index')

    applicant = applicant[0]

    if applicant.account_verified:
        messages.add_message(
            request,
            messages.SUCCESS,
            'Your email has already been verified. Please login to continue.',
            'list-group-item-success')
        return redirect('index')

    app_settings = _get_app_settings()
    intro = app_settings.get('confirm_verify_intro', '')

    if request.method == 'POST':
        applicant.account_verified = True
        applicant.verification_id = None
        applicant.save()

        messages.add_message(
            request,
            messages.SUCCESS,
            'Your email has been verified. Please complete your profile below.',
            'list-group-item-success')

        return redirect('applicant_app:complete_signup', applicant_id=applicant.id)

    return render(
        request,
        'instructor_app/confirm_verification.html',
        {
            'intro': intro,
            'form': TeacherApplicantVerifyAccountForm(initial={
                'verification_id': verification_id
            })
        })


verify_email.login_required = False


def complete_signup(request, applicant_id):
    """
    Final step of instructor applicant registration - collect profile information.

    Collects contact info, address, and password. On successful submission:
    - Saves profile data to user model
    - Logs the user in
    - Redirects to dashboard

    Public view (login_required = False).
    """
    applicant = get_object_or_404(TeacherApplicant, pk=applicant_id)

    # Set session key so address_suggestions view allows access
    request.session['record_key'] = str(applicant.pk)

    app_settings = _get_app_settings()
    accepting = _is_accepting_applications(app_settings)

    if not accepting:
        closed_message = app_settings.get('closed_message', '-')
        return render(
            request,
            'instructor_app/start-app.html',
            {
                'accepting_applications': False,
                'closed_message': closed_message,
            })

    if request.method == 'POST':
        form = TeacherApplicantProfileForm(
            applicant=applicant, data=request.POST
        )

        if form.is_valid():
            try:
                form.save(applicant)

                # Create a record in TeacherApplication to track progress through onboarding steps
                teacher_application = TeacherApplication.objects.create(
                    user=applicant.user,
                    createdon=date.today(),
                    misc_info={},
                )

                auth.login(
                    request,
                    applicant.user,
                    backend='cis.email_backend.EmailAuthBackend'
                )

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Your account has been created successfully. Please continue below.',
                    'list-group-item-success')
                return redirect(
                    'applicant_app:manage_courses',
                    teacher_application.id)

            except IntegrityError as e:
                form._errors['email'] = [str(e)]
        else:
            messages.add_message(
                request,
                messages.ERROR,
                'Please correct the errors below and try again.',
                'list-group-item-danger')
    else:
        form = TeacherApplicantProfileForm(applicant=applicant)

    return render(
        request,
        'instructor_app/complete_signup.html',
        {
            'form': form,
        })


complete_signup.login_required = False
