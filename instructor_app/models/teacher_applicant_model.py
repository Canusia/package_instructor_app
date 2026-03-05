import uuid, logging

from django.db import models
from django.urls import reverse_lazy
from django.contrib.auth.models import Group

from instructor_app.email import send_notification
from cis.models.customuser import CustomUser

logger = logging.getLogger(__name__)


class TeacherApplicant(models.Model):
    """
    Base user model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('cis.CustomUser', on_delete=models.PROTECT, related_name='inst_app_teacherapplicant')

    STATUS_OPTIONS = (
        ('Incomplete', 'Incomplete'),
        ('Inactive', 'Inactive'),
    )
    status = models.CharField(max_length=30, choices=STATUS_OPTIONS, default="Incomplete")

    verification_id = models.UUIDField(blank=True, null=True, editable=False)
    account_verified = models.BooleanField(default=False)
    account_verified_on = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    class Meta:
        ordering = ['user__first_name']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        group = Group.objects.get(name='applicant')
        self.user.groups.add(group)

    def reset_verification_id(self, reset_account_verified=True):
        if reset_account_verified:
            self.account_verified = False
        self.verification_id = uuid.uuid4()
        self.save()
        return self.verification_id

    @property
    def verify_email_url(self):
        from cis.utils import getDomain
        if not self.verification_id:
            self.reset_verification_id()
        return getDomain() + str(
            reverse_lazy(
                'applicant_app:verify_email',
                kwargs={'verification_id': self.verification_id}
            )
        )

    def send_verification_request_email(self):
        from instructor_app.settings.inst_app_language import inst_app_language

        email_settings = inst_app_language.from_db()
        template_str = email_settings.get('verification_email', '')
        subject = email_settings.get('verify_email_subject', 'Verify your email')

        send_notification(subject, template_str, {
            'teacher_first_name': self.user.first_name,
            'teacher_last_name': self.user.last_name,
            'teacher_email': self.user.email,
            'verification_link': self.verify_email_url,
        }, [self.user.email])

    @classmethod
    def create_new(cls, tapp_form):
        """
        Returns a TeacherApplicant object
        """
        from instructor_app.models.teacher_application import TeacherApplication

        user = CustomUser()
        user.first_name = tapp_form.cleaned_data['first_name']
        user.last_name = tapp_form.cleaned_data['last_name']
        user.middle_name = tapp_form.cleaned_data['middle_name']

        user.email = tapp_form.cleaned_data['email']
        user.username = tapp_form.cleaned_data['email']
        user.secondary_email = tapp_form.cleaned_data['secondary_email']
        user.alt_email = tapp_form.cleaned_data['alt_email']

        user.ssn = tapp_form.cleaned_data.get('ssn')
        user.date_of_birth = tapp_form.cleaned_data.get('date_of_birth')

        user.primary_phone = tapp_form.cleaned_data['primary_phone']
        user.secondary_phone = tapp_form.cleaned_data['secondary_phone']
        user.alt_phone = tapp_form.cleaned_data['alt_phone']

        user.address1 = tapp_form.cleaned_data['home_address']
        user.city = tapp_form.cleaned_data['city']
        user.state = tapp_form.cleaned_data['state']
        user.postal_code = tapp_form.cleaned_data['zip_code']

        user.set_password(tapp_form.cleaned_data['password'])
        user.save()

        record = TeacherApplicant(user=user)
        record.save()

        teacher_application = TeacherApplication.create_new(user=user)
        return teacher_application
