import logging

from django.conf import settings
from django.template import Context, Template
from django.template.loader import get_template

from mailer import send_html_mail

logger = logging.getLogger(__name__)


def render_email(template_str, context_dict):
    """
    Render an email template string with context and wrap in HTML email layout.

    Returns:
        tuple: (html_body, text_body)
    """
    template = Template(template_str)
    context = Context(context_dict)
    text_body = template.render(context)

    html_template = get_template('cis/email.html')
    html_body = html_template.render({'message': text_body})

    return html_body, text_body


def send_notification(subject, template_str, context_dict, recipients):
    """
    Render and send an HTML email notification.

    In DEBUG mode, redirects all emails to the test address.
    """
    if not template_str:
        logger.warning('Empty email template, skipping send')
        return

    html_body, text_body = render_email(template_str, context_dict)

    if getattr(settings, 'DEBUG', True):
        recipients = ['kadaji@gmail.com']

    send_html_mail(
        subject,
        text_body,
        html_body,
        settings.DEFAULT_FROM_EMAIL,
        recipients
    )
