import unittest
from unittest.mock import patch

from lab import extract, transaction


class FhirTests(unittest.TestCase):
    def test_transaction_has_stable_put_ids(self):
        bundle = transaction()
        self.assertEqual(bundle['type'], 'transaction')
        self.assertEqual(len(bundle['entry']), 36)
        for entry in bundle['entry']:
            resource = entry['resource']
            self.assertEqual(entry['request'], {'method': 'PUT', 'url': resource['resourceType'] + '/' + resource['id']})

    @patch('lab.request')
    def test_extract_follows_pagination(self, request):
        def page(url):
            if 'Patient?' in url:
                return {'resourceType': 'Bundle', 'type': 'searchset',
                        'entry': [{'resource': {'resourceType': 'Patient', 'id': 'a'}}],
                        'link': [{'relation': 'next', 'url': 'http://hapi/fhir/page2'}]}
            if url.endswith('page2'):
                return {'resourceType': 'Bundle', 'type': 'searchset',
                        'entry': [{'resource': {'resourceType': 'Patient', 'id': 'b'}}]}
            return {'resourceType': 'Bundle', 'type': 'searchset'}
        request.side_effect = page
        result = extract('http://hapi/fhir')
        self.assertEqual([e['resource']['id'] for e in result['entry']], ['a', 'b'])
        self.assertEqual(request.call_count, 5)

    @patch('lab.request')
    def test_extract_rejects_cross_server_link(self, request):
        request.return_value = {'resourceType': 'Bundle', 'type': 'searchset',
                                'link': [{'relation': 'next', 'url': 'http://other/fhir'}]}
        with self.assertRaises(ValueError):
            extract('http://hapi/fhir')
