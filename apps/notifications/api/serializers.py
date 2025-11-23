from rest_framework import serializers
from apps.notifications.models import Email

class EmailSerializer(serializers.ModelSerializer):
    to_email = serializers.EmailField()
    subject = serializers.CharField(max_length=50, allow_blank=True)
    message = serializers.CharField(allow_blank=True)
    sent_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Email
        fields = [
            'to_email',
            'subject',
            'message',
            'sent_at'
        ]
        read_only_fields = ['id','sent_at']