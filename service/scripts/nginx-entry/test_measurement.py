import unittest
from measurement import summarize_rows

class MeasurementTests(unittest.TestCase):
    def test_errors_remain_in_denominator_and_percentiles_use_successes(self):
        result=summarize_rows([{'code':200,'latency_ns':1},{'code':503,'latency_ns':100},{'code':200,'latency_ns':3}],4)
        self.assertEqual(result['planned'],4)
        self.assertEqual(result['success'],2)
        self.assertEqual(result['error'],2)
        self.assertEqual(result['missing'],1)
        self.assertEqual(result['p95_ns'],3)


class DenominatorEdges(unittest.TestCase):
    def test_zero_success_has_undefined_quantiles(self):
        r=summarize_rows([{'code':0,'latency_ns':0,'error':'timeout'}],2)
        self.assertIsNone(r['p95_ns']);self.assertEqual(r['error'],2)
    def test_extra_receipts_cannot_hide_duplicate_attempts(self):
        with self.assertRaises(ValueError):summarize_rows([{'code':200,'latency_ns':1}]*2,1)

class TimestampTests(unittest.TestCase):
    def test_nanosecond_receipts_keep_sub_microsecond_distinction(self):
        from measurement import timestamp_ns
        self.assertEqual(timestamp_ns('2026-10-25T12:00:00.123456789Z')-timestamp_ns('2026-10-25T12:00:00.123456788Z'),1)

class GoReceiptTests(unittest.TestCase):
    def test_packages_without_tests_do_not_hide_real_required_test(self):
        from measurement import summarize_go
        self.assertEqual(summarize_go([{'Action':'skip','Package':'cmd/service'},{'Action':'pass','Test':'TestDurableAdmissionAndRecovery'}])['tests'],1)
    def test_skipped_test_and_empty_collection_fail(self):
        from measurement import summarize_go
        for events in [[],[{'Action':'skip','Test':'TestDurableAdmissionAndRecovery'}]]:
            with self.assertRaises(ValueError):summarize_go(events)

if __name__=='__main__':unittest.main()
