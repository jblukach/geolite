import json
import os
import sys
import types
import unittest
from unittest import mock

from search import search


class _FakeReader:

    def __init__(self, dataset: str, calls: list[tuple[str, str]]):
        self.dataset = dataset
        self.calls = calls

    def get(self, ip_text: str):
        self.calls.append((self.dataset, ip_text))
        if self.dataset == 'asn':
            return {
                'autonomous_system_number': 65000,
                'autonomous_system_organization': 'Example Org',
                'network': '198.51.100.0/24',
            }
        return {
            'country': {'iso_code': 'US', 'names': {'en': 'United States'}},
            'subdivisions': [{'names': {'en': 'Ohio'}}],
            'city': {'names': {'en': 'Columbus'}},
            'network': '198.51.100.0/24',
        }


class _ReaderContext:

    def __init__(self, dataset: str, calls: list[tuple[str, str]]):
        self.dataset = dataset
        self.calls = calls

    def __enter__(self):
        return _FakeReader(self.dataset, self.calls)

    def __exit__(self, exc_type, exc, tb):
        return False


class SearchHandlerTests(unittest.TestCase):

    def setUp(self):
        self.calls: list[tuple[str, str]] = []
        fake_maxminddb = types.ModuleType('maxminddb')

        def _open_database(path):
            dataset = 'asn' if 'ASN' in path else 'city'
            return _ReaderContext(dataset, self.calls)

        fake_maxminddb.open_database = _open_database
        self.module_patch = mock.patch.dict(sys.modules, {'maxminddb': fake_maxminddb}, clear=False)
        self.module_patch.start()

    def tearDown(self):
        self.module_patch.stop()

    def _invoke(self, event, context=None, **env):
        with mock.patch.dict(os.environ, env, clear=False), \
            mock.patch('search.search._read_metadata_file', side_effect=lambda name: '2026-01-01T00:00:00Z'), \
            mock.patch('search.search.os.path.isfile', return_value=True):
            return search.handler(event, context)

    def test_query_ip_csv_input_supported(self):
        response = self._invoke({'rawQueryString': 'ip=198.51.100.1,198.51.100.2'})
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['requested_count'], 2)
        self.assertEqual([entry['ip'] for entry in body['results']], ['198.51.100.1', '198.51.100.2'])
        self.assertEqual(
            body['results'][0]['asn'],
            {'id': 65000, 'org': 'Example Org', 'net': '198.51.100.0/24'},
        )
        self.assertEqual(
            body['results'][0]['geo'],
            {
                'country': 'United States - US',
                'state': 'Ohio',
                'city': 'Columbus',
                'cidr': '198.51.100.0/24',
            },
        )

    def test_json_keys_and_path_and_get_fallback_supported(self):
        body_response = self._invoke({'body': json.dumps({'ipAddress': '198.51.100.3', 'query': '198.51.100.4'})})
        self.assertEqual(body_response['statusCode'], 200)
        body_payload = json.loads(body_response['body'])
        self.assertEqual([entry['ip'] for entry in body_payload['results']], ['198.51.100.3', '198.51.100.4'])

        path_response = self._invoke({'rawPath': '/geo/2001%3Adb8%3A%3A1'})
        self.assertEqual(path_response['statusCode'], 200)
        path_payload = json.loads(path_response['body'])
        self.assertEqual(path_payload['results'][0]['ip'], '2001:db8::1')

        fallback_response = self._invoke(
            {
                'rawPath': '/geo',
                'requestContext': {'http': {'method': 'GET', 'sourceIp': '203.0.113.10'}},
            }
        )
        self.assertEqual(fallback_response['statusCode'], 200)
        fallback_payload = json.loads(fallback_response['body'])
        self.assertEqual(fallback_payload['results'][0]['ip'], '203.0.113.10')

    def test_results_include_per_entry_errors_and_preserve_order(self):
        response = self._invoke({'ips': ['198.51.100.1', 'bad-ip', '198.51.100.2']})
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual([entry['ip'] for entry in body['results']], ['198.51.100.1', 'bad-ip', '198.51.100.2'])
        self.assertIn('error', body['results'][1])

    def test_valid_ips_are_deduplicated_for_lookup_volume(self):
        response = self._invoke({'ips': ['198.51.100.1', '198.51.100.1', '198.51.100.2']})
        self.assertEqual(response['statusCode'], 200)
        # 2 unique valid IPs x 2 readers (asn + city)
        self.assertEqual(len(self.calls), 4)

    def test_returns_400_for_empty_and_oversized(self):
        empty_response = self._invoke({})
        self.assertEqual(empty_response['statusCode'], 400)

        oversized_response = self._invoke({'ips': ['198.51.100.1', '198.51.100.2']}, MAX_IPS_PER_REQUEST='1')
        self.assertEqual(oversized_response['statusCode'], 400)

    def test_returns_413_for_request_body_too_large(self):
        response = self._invoke(
            {'body': json.dumps({'ips': ['198.51.100.1']}) + ('x' * 200)},
            MAX_REQUEST_BODY_BYTES='16',
        )
        self.assertEqual(response['statusCode'], 413)

    def test_returns_503_when_budget_is_too_low(self):
        class _Context:
            def get_remaining_time_in_millis(self):
                return 100

        response = self._invoke({'ips': ['198.51.100.1']}, context=_Context(), MIN_REMAINING_TIME_MS='500')
        self.assertEqual(response['statusCode'], 503)

    def test_outputs_utc_timestamps(self):
        response = self._invoke({'ips': ['198.51.100.1']})
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['geolite2-asn.mmdb'].endswith('Z'))
        self.assertTrue(body['geolite2-city.mmdb'].endswith('Z'))
        self.assertTrue(body['timestamp_utc'].endswith('Z'))


if __name__ == '__main__':
    unittest.main()