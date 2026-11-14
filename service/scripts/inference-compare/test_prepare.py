import tempfile,unittest
from pathlib import Path
from prepare import inventory

class InventoryTests(unittest.TestCase):
    def test_accepted_runtime_size_and_legacy_bytes_manifests_normalize_without_dropping_rows(self):
        from prepare import manifest_files
        self.assertEqual(manifest_files({'files':[{'path':'env/a','size':7,'sha256':'a'*64}]}),[{'path':'env/a','bytes':7,'sha256':'a'*64}])
        self.assertEqual(manifest_files([{'path':'a','bytes':8,'sha256':'b'*64}])[0]['bytes'],8)
        for rows in [[{'path':'a','size':True,'sha256':'a'*64}],[{'path':'../a','size':1,'sha256':'a'*64}],[{'path':'a','bytes':1,'size':2,'sha256':'a'*64}]]:
            with self.assertRaises(ValueError):manifest_files(rows)

    def test_inventory_counts_root_itself_and_never_calls_missing_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'raw').write_bytes(b'original')
            result=inventory([root])
            self.assertTrue(result['complete'])
            self.assertIn(str(root.resolve()),[r['path'] for r in result['files']])
            self.assertEqual(result['apparent_bytes'],root.stat().st_size+(root/'raw').stat().st_size)
            result=inventory([root,root/'missing'])
            self.assertFalse(result['complete']);self.assertTrue(result['errors'])

if __name__=='__main__':unittest.main()
