from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, get_connection
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)


# Context function for progress_reminder: returns dict with meta and progreso
def get_progress_context(user):
    """Build context for progress_reminder template."""
    return {
        'meta': user.ideal.ideal_weight if user.ideal else 'N/A',
        'progreso': user.progress.current_weight if user.progress else 'N/A',
    }


# Filter function for progress_reminder: only users with progress
def filter_users_with_progress(base_queryset):
    """Filter users who have a progress record."""
    return base_queryset.filter(progress__isnull=False).select_related('progress', 'ideal')


# Template configuration: define templates, filters, and context functions
TEMPLATE_CONFIG = {
    'reminder': {
        'path': 'emails/use_app_reminder.html',
        'is_dynamic': False,
        'filter_func': None,  # Uses base queryset (all subscribed users)
        'context_func': None,
    },
    'progress_reminder': {
        'path': 'emails/progress_reminder.html',
        'is_dynamic': True,
        'filter_func': filter_users_with_progress,
        'context_func': get_progress_context,
    },
}

TEMPLATE_CHOICES = {key: config['path'] for key, config in TEMPLATE_CONFIG.items()}


def send_bulk_emails(template_key, subject, from_email, recipient_list, plain_text=''):
    """Render template and send HTML emails in batch.

    Args:
        template_name (str): Path to template to render
        subject (str): Email subject
        from_email (str): Sender email
        recipient_list: Either a list of email strings (static render) 
                       or a list of tuples (user_obj, email) for dynamic context
        plain_text (str): Plain text body fallback
        is_dynamic (bool): Whether to render template per user with dynamic context.

    Returns:
        The number of messages sent.
        Raises exceptions from the mail layer to be handled by caller.
    """
    messages = []
    template_name = TEMPLATE_CONFIG[template_key]['path']
    is_dynamic = TEMPLATE_CONFIG[template_key]['is_dynamic']

    # Check if we have dynamic context (tuples) or static (strings)
    if is_dynamic:
        # Dynamic rendering per user
        context_func = TEMPLATE_CONFIG[template_key]['context_func']
        for user, email_address in recipient_list:
            context = context_func(user)
            html_content = render_to_string(template_name, context)
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_text,
                from_email=from_email,
                to=[email_address],
            )
            msg.attach_alternative(html_content, 'text/html')
            messages.append(msg)
    else:
        # Static rendering
        html_content = render_to_string(template_name)
        for _, email_address in recipient_list:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_text,
                from_email=from_email,
                to=[email_address],
            )
            msg.attach_alternative(html_content, 'text/html')
            messages.append(msg)

    # Send using a single connection for efficiency
    connection = get_connection()
    sent = connection.send_messages(messages)
    logger.info('send_bulk_emails sent %s messages', sent)
    return sent
