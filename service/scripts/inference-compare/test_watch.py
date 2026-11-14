import unittest
from authority import GPU
from watch import compute_processes

class WatchTests(unittest.TestCase):
    def test_gpu_inventory_cannot_hide_foreign_or_unknown(self):
        self.assertEqual(compute_processes('42, '+GPU+'\n',{42}),[])
        self.assertEqual(compute_processes('43, '+GPU+'\n',{42}),[43])
        for raw in ['unknown','1, wrong-uuid','N/A, '+GPU]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):compute_processes(raw,{42})

if __name__=='__main__':unittest.main()
