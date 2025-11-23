from rest_framework import generics, status
from rest_framework.response import Response
from django.core.mail import send_mail, BadHeaderError

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from django.conf import settings
import smtplib
import socket
import logging

from apps.notifications.api.serializers import EmailSerializer

logger = logging.getLogger(__name__)


class EmailAPIView(generics.GenericAPIView):
    """API view to send email notifications.

    POST: Send an email notification.

    Request body (POST): {
        "to_email": "...",
        "subject": "...",
        "message": "..."
    }
    Response (POST): 200 OK
    """
    
    def post(self, request, *args, **kwargs):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        to_email = data['to_email']
        subject = data['subject']
        message = data['message']

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', None)
        if not from_email:
            logger.warning('No DEFAULT_FROM_EMAIL or SERVER_EMAIL configured for sending emails')
            return Response(
                {'detail': 'Server email not configured.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        html_content = render_to_string("emails/notification.html", {
            "message": message,
            "subject": subject,
        })

        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[to_email],
        )
        
        email.attach_alternative(html_content, "text/html")

        try:
            email.send()
            return Response({"detail": "Email sent successfully"}, status=status.HTTP_200_OK)

        except BadHeaderError:
            logger.warning('BadHeaderError when sending email to %s', to_email)
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
            logger.exception('SMTP authentication error while sending email to %s: %s', to_email, e)
            return Response(
                {'detail': 'Failed to send email due to authentication error with mail server.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except (smtplib.SMTPException, socket.gaierror) as e:
            logger.exception('SMTP/network error while sending email to %s: %s', to_email, e)
            return Response(
                {'detail': 'Failed to send email due to mail server or network error.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as e:
            logger.exception('Unexpected error sending email to %s: %s', to_email, e)
            return Response(
                {'detail': 'Internal server error.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
