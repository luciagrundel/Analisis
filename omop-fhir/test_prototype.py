import copy
import unittest

from prototype import cohort, connect, load, sample


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(':memory:')
        self.addCleanup(self.db.close)

    def test_cohort_and_idempotent_update(self):
        bundle = sample()
        counts = load(self.db, bundle)
        self.assertEqual(counts, {'person': 10, 'visit_occurrence': 10,
                                 'condition_occurrence': 6, 'measurement': 10})
        self.assertEqual(load(self.db, bundle), counts)
        self.assertEqual(len(cohort(self.db, '2026-11-09', 125)), 2)
        self.assertEqual(cohort(self.db, '2026-11-08', 125), [])
        for entry in bundle['entry']:
            r = entry['resource']
            if r['resourceType'] == 'Observation' and r['id'] == 'g1':
                r['valueQuantity']['value'] = 200
        self.assertEqual(load(self.db, bundle), counts)
        self.assertEqual(len(cohort(self.db, '2026-11-09', 125)), 3)

    def test_invalid_reference_rolls_back(self):
        bundle = sample()
        bundle['entry'][-2]['resource']['subject']['reference'] = 'Patient/missing'
        with self.assertRaises(ValueError):
            load(self.db, bundle)
        self.assertEqual(self.db.execute('SELECT count(*) FROM person').fetchone()[0], 0)

    def test_unit_rejected_without_damaging_previous_load(self):
        bundle = sample()
        load(self.db, bundle)
        broken = copy.deepcopy(bundle)
        next(e['resource'] for e in broken['entry'] if e['resource']['resourceType'] == 'Observation')['valueQuantity']['code'] = 'mmol/L'
        with self.assertRaises(ValueError):
            load(self.db, broken)
        self.assertEqual(len(cohort(self.db, '2026-11-09', 125)), 2)

    def test_sources_have_independent_identity(self):
        load(self.db, sample(), 'a')
        load(self.db, sample(), 'b')
        self.assertEqual(self.db.execute('SELECT count(*) FROM person').fetchone()[0], 20)


if __name__ == '__main__':
    unittest.main()
