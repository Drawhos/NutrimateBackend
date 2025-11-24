from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.core.mail import BadHeaderError
from django.conf import settings
from apps.users.models import User
from apps.notifications.utils import send_bulk_emails, TEMPLATE_CONFIG
import smtplib
import socket
import logging

logger = logging.getLogger(__name__)


class EmailAPIView(generics.GenericAPIView):
    """API view to send bulk email notifications to all subscribed users.

    POST: Send email notification to all users who have not opted out.
    
    Optional query parameters:
    - template: Choose the email template to use (e.g., 'reminder')
    
    Request body (POST): {} (no parameters required)
    Response (POST): 200 OK with count of emails sent
    """
    
    permission_classes = [IsAdminUser]  # Only admins can send bulk emails
    
    def post(self, request, *args, **kwargs):
        subject = "Notificación de Nutrimate"

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', None)
        if not from_email:
            logger.warning('No DEFAULT_FROM_EMAIL or SERVER_EMAIL configured for sending emails')
            return Response(
                {'detail': 'Server email not configured.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Choose template key from query param (whitelisted)
        template_key = request.query_params.get('template')
        
        # Validate template
        if template_key not in TEMPLATE_CONFIG:
            return Response({'detail': 'Template no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
        
        template_config = TEMPLATE_CONFIG[template_key]
        filter_func = template_config['filter_func']

        # Get base queryset of subscribed users
        base_queryset = User.objects.filter(email_opt_out=False)
        
        # Apply template-specific filter if defined
        if filter_func:
            users_queryset = filter_func(base_queryset)
        else:
            users_queryset = base_queryset
        
        if not users_queryset.exists():
            return Response(
                {'detail': 'No users available to send emails to.', 'count': 0},
                status=status.HTTP_200_OK
            )
        
        try:
            # For dynamic templates, tuples (user, email) so render_to_string gets context per user
            recipient_list = [(user, user.email) for user in users_queryset]
            sent_count = send_bulk_emails(
                template_key,
                subject, 
                from_email, 
                recipient_list, 
                plain_text='',
            )

            logger.info('Successfully sent %d notification emails', sent_count)
            return Response(
                {
                    'detail': f'Email sent successfully to {sent_count} users.',
                    'count': sent_count
                },
                status=status.HTTP_200_OK
            )

        except BadHeaderError:
            logger.warning('BadHeaderError when sending bulk emails')
            return Response(
                {'detail': 'Invalid header found.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        except smtplib.SMTPRecipientsRefused as e:
            logger.exception('SMTP recipient refused: %s', e)
            return Response(
                {'detail': 'Recipient address refused by SMTP server.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except smtplib.SMTPAuthenticationError as e:
            logger.exception('SMTP authentication error while sending bulk emails: %s', e)
            return Response(
                {'detail': 'Failed to send email due to authentication error with mail server.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except (smtplib.SMTPException, socket.gaierror) as e:
            logger.exception('SMTP/network error while sending bulk emails: %s', e)
            return Response(
                {'detail': 'Failed to send email due to mail server or network error.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as e:
            logger.exception('Unexpected error sending bulk emails: %s', e)
            return Response(
                {'detail': 'Internal server error.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
