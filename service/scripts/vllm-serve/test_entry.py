"""The actual entry rejects forged/expired GO before touching Docker or CUDA."""
import json,hashlib,pathlib,subprocess,sys,tempfile,time,unittest
HERE=pathlib.Path(__file__).resolve().parent
class EntryTests(unittest.TestCase):
 def test_invalid_go_never_reaches_external_tools(self):
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);go=d/'go.json';go.write_text(json.dumps({'issue':24,'deadline_epoch':1}))
   digest=hashlib.sha256(go.read_bytes()).hexdigest()
   r=subprocess.run([sys.executable,str(HERE/'launch.py'),'--go',str(go),'--go-sha256',digest],capture_output=True,text=True,timeout=5)
   self.assertEqual(r.returncode,2);self.assertIn('GO rejected',r.stderr)
   self.assertNotIn('docker',r.stderr.lower());self.assertNotIn('nvidia-smi',r.stderr.lower())
if __name__=='__main__':unittest.main()
