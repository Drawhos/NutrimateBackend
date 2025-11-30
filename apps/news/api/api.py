import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import requests
import logging

logger = logging.getLogger(__name__)


class NewsListAPIView(APIView):
    """Proxy view for the external news API.

    Query parameters supported (client -> this endpoint):
    - title (repeatable) e.g. ?title=foo&title=bar
    - titles (CSV) e.g. ?titles=foo,bar

    Rules:
    - It is accepted a maximum of 5 titles (combined from repeated title params and
        the CSV titles param). If the client provides more than 5 the request
        returns HTTP 400.
    - Titles are deduplicated while preserving order before being forwarded.

 }   Responses:
    - 200 OK with JSON from external API on success
    - 400 Bad Request if too many titles are provided
    - 502 Bad Gateway if the external service returns an error or is unreachable
    """

    def get(self, request, *args, **kwargs):
        url = (
            f"https://api.apitube.io/v1/news/everything?per_page=10"
            f"&api_key={os.getenv('NEWS_API_KEY')}"
            f"&language.code=es&category.id=medtop:20000465"
        )

        # Collect optional title filters from query parameters.
        # Accept either repeated ?title=one&title=two or a CSV param ?titles=one,two
        raw_titles = request.query_params.getlist('title') or []
        if not raw_titles:
            csv = request.query_params.get('titles')
            if csv:
                raw_titles = [t.strip() for t in csv.split(',') if t.strip()]

        # If a single title contains commas (e.g. ?title=a,b), split it apart
        flattened = []
        for item in raw_titles:
            if ',' in item:
                flattened.extend([t.strip() for t in item.split(',') if t.strip()])
            elif item:
                flattened.append(item)

        # Deduplicate while preserving order
        seen = set()
        titles = []
        for t in flattened:
            if t and t not in seen:
                seen.add(t)
                titles.append(t)

        if len(titles) > 5:
            return Response({'detail': 'You may provide at most 5 titles.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            params = {
                'per_page': 10,
                'api_key': os.getenv('NEWS_API_KEY'),
                'language.code': 'es',
                'category.id': 'medtop:20000465',
            }

            if titles:
                # API expects titles as a comma-separated value
                params['title'] = ','.join(titles)

            resp = requests.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            return Response(resp.json(), status=resp.status_code)

        except requests.exceptions.Timeout:
            logger.warning('News API timed out')
            return Response({'detail': 'External news service timed out.'}, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except requests.exceptions.HTTPError:
            logger.exception('External news service returned error %s', resp.status_code)
            return Response({'detail': f'External service returned HTTP {resp.status_code}'}, status=status.HTTP_502_BAD_GATEWAY)

        except requests.exceptions.RequestException:
            logger.exception('Failed to fetch news from external service')
            return Response({'detail': 'Failed to reach news service.'}, status=status.HTTP_502_BAD_GATEWAY)
