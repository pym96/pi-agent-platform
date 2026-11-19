import unittest
from recompute import verify_planned_rows

class RecomputeTests(unittest.TestCase):
    def test_deleted_failure_or_changed_payload_cannot_shrink_frozen_denominator(self):
        slots=[{'id':str(k),'payload':{'k':k}} for k in range(20)]
        rows=[{'id':s['id'],'payload':s['payload'],'classification':'failed'} for s in slots]
        verify_planned_rows(rows,slots)
        for bad in [rows[:-1],rows+[rows[0]],[dict(r,payload={}) if i==2 else r for i,r in enumerate(rows)]]:
            with self.assertRaises(ValueError):verify_planned_rows(bad,slots)

if __name__=='__main__':unittest.main()
