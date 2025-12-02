from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.news.api.api import NewsListAPIView


class NewsListAPIViewTests(TestCase):

	def setUp(self):
		self.factory = APIRequestFactory()
  
    # ---------- TEST CASES ----------

	def test_public_access_allowed(self):
		"""The view does not require authentication and should be reachable by anonymous users."""
		request = self.factory.get('/api/news/')

		with patch('apps.news.api.api.requests.get') as mock_get:
			mock_resp = MagicMock()
			mock_resp.json.return_value = {'result': []}
			mock_resp.status_code = 200
			mock_get.return_value = mock_resp

			view = NewsListAPIView.as_view()
			response = view(request)

			self.assertEqual(response.status_code, 200)
			self.assertEqual(response.data, {'result': []})

	def test_single_and_multiple_title_params_forwarded_and_deduped(self):
		# repeated title params + single comma-separated CSV should be deduped
		request = self.factory.get('/api/news/?title=one&title=two&titles=two,three')

		with patch('apps.news.api.api.requests.get') as mock_get:
			mock_resp = MagicMock()
			mock_resp.json.return_value = {'ok': True}
			mock_resp.status_code = 200
			mock_get.return_value = mock_resp

			view = NewsListAPIView.as_view()
			response = view(request)

			# verify we forwarded a deduped, comma-joined `title` param
			called_args, called_kwargs = mock_get.call_args
			self.assertIn('params', called_kwargs)
			params = called_kwargs['params']
			# view uses repeated `title` params when present and ignores `titles=` CSV,
			# so we expect just the two repeated values deduped
			self.assertEqual(params['title'], 'one,two')
			self.assertEqual(response.status_code, 200)

	def test_commas_in_single_title_split_and_dedup(self):
		# a single ?title=a,b should split into two titles
		request = self.factory.get('/api/news/?title=a,b&title=b')

		with patch('apps.news.api.api.requests.get') as mock_get:
			mock_resp = MagicMock()
			mock_resp.json.return_value = {'ok': True}
			mock_resp.status_code = 200
			mock_get.return_value = mock_resp

			view = NewsListAPIView.as_view()
			response = view(request)

			called_args, called_kwargs = mock_get.call_args
			params = called_kwargs['params']
			# dedup while preserving order: a,b -> a,b (b duplicated removed)
			self.assertEqual(params['title'], 'a,b')
			self.assertEqual(response.status_code, 200)

	def test_too_many_titles_returns_400(self):
		# create 6 titles to trigger the validation
		qs = '&'.join(f'title=t{i}' for i in range(6))
		request = self.factory.get(f'/api/news/?{qs}')

		view = NewsListAPIView.as_view()
		response = view(request)

		self.assertEqual(response.status_code, 400)

	def test_external_timeout_returns_504(self):
		request = self.factory.get('/api/news/?title=one')

		with patch('apps.news.api.api.requests.get', side_effect=Exception('timeout')):
			# Use the real exception type used in view (requests.exceptions.Timeout)
			with patch('apps.news.api.api.requests.get', side_effect=__import__('requests').exceptions.Timeout):
				view = NewsListAPIView.as_view()
				response = view(request)
				self.assertEqual(response.status_code, 504)

	def test_external_http_error_returns_502(self):
		request = self.factory.get('/api/news/?title=one')

		with patch('apps.news.api.api.requests.get') as mock_get:
			mock_resp = MagicMock()
			mock_resp.raise_for_status.side_effect = __import__('requests').exceptions.HTTPError('bad')
			mock_resp.status_code = 502
			mock_get.return_value = mock_resp

			view = NewsListAPIView.as_view()
			response = view(request)

			self.assertEqual(response.status_code, 502)

	def test_external_request_exception_returns_502(self):
		request = self.factory.get('/api/news/')

		with patch('apps.news.api.api.requests.get', side_effect=__import__('requests').exceptions.RequestException):
			view = NewsListAPIView.as_view()
			response = view(request)
			self.assertEqual(response.status_code, 502)

