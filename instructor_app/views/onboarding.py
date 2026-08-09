"""
Instructor applicant onboarding views for new teacher registration flow.

Flow: start_app -> awaiting_verification -> verify_email -> complete_signup -> dashboard
"""
import logging
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.db import IntegrityError
from django.conf import settings
from django.contrib import messages, auth
from django.urls import reverse

from ..models.teacher_applicant import TeacherApplicant, TeacherApplication
from ..services.applications import start_or_resume_application
from ..forms.teacher_applicant import (
    TeacherApplicantVerifyEmailForm,
    TeacherApplicantVerifyAccountForm,
    TeacherApplicantProfileForm,
)
from ..settings.inst_app_language import inst_app_language

logger = logging.getLogger(__name__)


def _get_app_settings():
    """Return inst_app_language settings dict."""
    return inst_app_language.from_db()


def _login_url_for(applicant):
    """Login page with a next= back to this applicant's complete-app step.

    There is no named login route in MyCE — LOGIN_URL is a plain path.
    """
    destination = reverse(
        'applicant_app:complete_signup',
        kwargs={'applicant_id': applicant.id},
    )
    return f'{settings.LOGIN_URL}?next={destination}'


def _is_pre_existing(applicant):
    """True when this applicant record was attached to an account that already existed."""
    return bool((applicant.meta or {}).get('pre_existing_account'))


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

    # An authenticated user has nothing to verify. Without this branch they
    # would be mailed a link that redirects them to sign in while already
    # signed in.
    if request.user.is_authenticated:
        return _start_app_for_authenticated_user(request, signup_intro)

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


def _start_app_for_authenticated_user(request, signup_intro):
    """
    Signed-in entry point: no email round-trip, no credentials touched.

    POST starts (or resumes) the application; GET offers the button. An
    ineligible signed-in user gets the same refusal an ineligible email does.
    """
    from ..services.applicant_eligibility import (
        existing_user_may_apply,
        is_existing_applicant,
    )

    user = request.user

    if is_existing_applicant(user):
        application = start_or_resume_application(user)
        return redirect('applicant_app:manage_courses', application.id)

    if not (
        TeacherApplicantVerifyEmailForm._existing_users_may_apply()
        and existing_user_may_apply(user)
    ):
        messages.add_message(
            request,
            messages.ERROR,
            'This account is not eligible to submit an instructor application.',
            'list-group-item-danger')
        return redirect('index')

    if request.method == 'POST':
        TeacherApplicant.objects.get_or_create(
            user=user,
            defaults={
                'account_verified': True,
                'meta': {'pre_existing_account': True},
            },
        )
        application = start_or_resume_application(user)
        return redirect('applicant_app:manage_courses', application.id)

    return render(
        request,
        'instructor_app/start-app.html',
        {
            'accepting_applications': True,
            'signup_intro': signup_intro,
            'authenticated_start': True,
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

        if _is_pre_existing(applicant):
            # The account already exists and already has a password. Confirming
            # the mailed link proves inbox control, which is enough to provision
            # a new account but not enough to hand out a session on an account
            # that already holds roles — so they sign in the normal way.
            messages.add_message(
                request,
                messages.SUCCESS,
                'Your email has been verified. Please sign in to continue your application.',
                'list-group-item-success')
            return redirect(_login_url_for(applicant))

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

    # This URL is public and takes an applicant_id. For an applicant sitting on
    # a pre-existing account the step edits a real staff/teacher/student record,
    # so it is only served to that user, signed in as themselves.
    if _is_pre_existing(applicant):
        if not request.user.is_authenticated:
            return redirect(_login_url_for(applicant))
        if request.user.pk != applicant.user_id:
            messages.add_message(
                request,
                messages.ERROR,
                'You are signed in as a different user. Please sign in with the '
                'account that started this application.',
                'list-group-item-danger')
            return redirect('index')

    # Set session key so address_suggestions view allows access
    request.session['record_key'] = str(applicant.pk)

    app_settings = _get_app_settings()
    accepting = _is_accepting_applications(app_settings)
    complete_signup_intro = app_settings.get('complete_signup_intro', '')

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

                # Create the TeacherApplication that tracks progress through the
                # onboarding steps — or resume a live one they already have.
                teacher_application = start_or_resume_application(applicant.user)

                if not request.user.is_authenticated:
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
            'complete_signup_intro': complete_signup_intro,
        })


complete_signup.login_required = False
