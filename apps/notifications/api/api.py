from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from apps.users.models import User
import smtplib
import socket
import logging

logger = logging.getLogger(__name__)


class EmailAPIView(generics.GenericAPIView):
    """API view to send bulk email notifications to all subscribed users.

    POST: Send email notification to all users who have not opted out.
    
    Request body (POST): {} (no parameters required)
    Response (POST): 200 OK with count of emails sent
    """
    
    permission_classes = [IsAdminUser]  # Only admins can send bulk emails
    
    def post(self, request, *args, **kwargs):
        # Template contains the full message; body can be empty or short fallback
        subject = "Notificación de Nutrimate"

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', None)
        if not from_email:
            logger.warning('No DEFAULT_FROM_EMAIL or SERVER_EMAIL configured for sending emails')
            return Response(
                {'detail': 'Server email not configured.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Get all users who have not opted out
        subscribed_users = User.objects.filter(email_opt_out=False)
        
        if not subscribed_users.exists():
            return Response(
                {'detail': 'No subscribed users to send emails to.', 'count': 0},
                status=status.HTTP_200_OK
            )

        recipient_emails = list(subscribed_users.values_list('email', flat=True))
        
        try:
            # Render HTML template (static template, no dynamic message)
            html_content = render_to_string("emails/use_app_reminder.html")
            
            # Build email tuples for send_mass_mail with HTML alternative
            email_messages = []
            for email_address in recipient_emails:
                email_obj = EmailMultiAlternatives(
                    subject=subject,
                    body="",
                    from_email=from_email,
                    to=[email_address],
                )
                email_obj.attach_alternative(html_content, "text/html")
                email_messages.append(email_obj)
            
            # Send all emails
            for email_obj in email_messages:
                email_obj.send()
            
            logger.info('Successfully sent %d notification emails', len(recipient_emails))
            return Response(
                {
                    'detail': f'Email sent successfully to {len(recipient_emails)} users.',
                    'count': len(recipient_emails)
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
