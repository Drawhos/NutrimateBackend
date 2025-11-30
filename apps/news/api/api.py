import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse

import requests
import os
import logging

logger = logging.getLogger(__name__)


class NewsListAPIView(APIView):
    """Proxy view for the external news API.

    This view forwards the external API JSON response directly. No serializer is
    necessary when the raw JSON is returned unchanged.
    """

    def get(self, request, *args, **kwargs):
        url = (
            f"https://api.apitube.io/v1/news/everything?per_page=10"
            f"&api_key={os.getenv('NEWS_API_KEY')}"
            f"&language.code=es&category.id=medtop:20000465"
        )

        try:
            resp = requests.get(url, timeout=5.0)
            resp.raise_for_status()
            # Return parsed JSON via DRF Response so renderers/content-negotiation work
            return HttpResponse(resp.text, content_type="application/json")

        except requests.exceptions.Timeout:
            logger.warning('News API timed out')
            return Response({'detail': 'External news service timed out.'}, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except requests.exceptions.HTTPError:
            logger.exception('External news service returned error %s', resp.status_code)
            return Response({'detail': f'External service returned HTTP {resp.status_code}'}, status=status.HTTP_502_BAD_GATEWAY)

        except requests.exceptions.RequestException:
            logger.exception('Failed to fetch news from external service')
            return Response({'detail': 'Failed to reach news service.'}, status=status.HTTP_502_BAD_GATEWAY)
