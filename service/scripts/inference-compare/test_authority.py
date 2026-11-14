import copy,datetime,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from authority import validate

def write(path,value):
    path.write_text(json.dumps(value,sort_keys=True));return hashlib.sha256(path.read_bytes()).hexdigest()

def fixture(root):
    utc=lambda n:datetime.datetime.fromtimestamp(n,datetime.timezone.utc).isoformat().replace('+00:00','Z')
    phase={'schema':'pi28-master-phase-contract/v1','issue':28,'id':'test28',
           **{k:utc(t) for k,t in [('start',900),('builder_latest_model_start',1400),('regulator_latest_model_start',1500),('all_server_owned_stop',1700),('final_candidate_push_latest',1800),('final_Verdict_target',1900),('Master_main_push_latest',2000),('end',2100)]},
           'server_root':'/media/usv012/pjx/pi-agent-platform/experiments/28-engine-compare-20261114',
           'physical_GPU_UUID':'GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead',
           'budgets':{'B_device_Created_to_removed_s':2400,'B_native_generations':560,'B_completion_POST':640,'R_device_Created_to_removed_s':600,'R_native_generations':32,'R_completion_POST':64,'server_conservative_wall_CPU_total_s':5400}}
    ph=write(root/'phase.json',phase)
    spent={'device_s':0,'native':0,'POST':0,'server_wall_s':0}
    lh=write(root/'ledger.json',spent)
    plan={'blocks':[{'id':'pilotA','arm':'A','max_attempts':16},{'id':'pilotB','arm':'B','max_attempts':16}]}
    planhash=write(root/'plan.json',plan)
    go={'schema':'pi28-stage-go/v1','issue':28,'role':'builder','stage':'pilot','phase_contract_sha256':ph,
        'source_sha':'a'*40,'gpu_uuid':phase['physical_GPU_UUID'],'nonce':'test-once',
        'deadline_epoch':1300,'allocated_device_s':300,'allocated_native':18,'allocated_POST':18,'allocated_server_wall_s':350,
        'spent':spent,'ledger_file':'ledger.json','ledger_sha256':lh,'plan_file':'plan.json','plan_sha256':planhash,
        'models':[{'id':'pilotA','arm':'A','nonce':'model-a','deadline_epoch':1150,'max_attempts':16},
                  {'id':'pilotB','arm':'B','nonce':'model-b','deadline_epoch':1300,'max_attempts':16}],
        'entry_hashes':{'authority.py':'b'*64}}
    return go,ph

class AuthorityTests(unittest.TestCase):
    def test_independent_phase_wrong_identity_and_budget_reject_before_tools(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);go,ph=fixture(root);gh=write(root/'go.json',go)
            self.assertEqual(validate(root/'go.json',gh,root/'phase.json',ph,now=1000)['issue'],28)
            for changes in [{'issue':24},{'role':'master'},{'deadline_epoch':True},{'deadline_epoch':float('nan')},
                            {'allocated_device_s':2401},{'source_sha':'x'*40},{'phase_contract_sha256':'f'*64},
                            {'nonce':'../bad'},{'spent':dict(go['spent'],native=-1)}]:
                bad=copy.deepcopy(go);bad.update(changes);digest=write(root/'go.json',bad)
                with self.subTest(changes=changes),self.assertRaises(ValueError):validate(root/'go.json',digest,root/'phase.json',ph,now=1000)
            write(root/'go.json',go)
            with self.assertRaises(ValueError):validate(root/'go.json',gh,root/'phase.json',ph,now=1401)
            (root/'phase.json').write_text('{}')
            with self.assertRaises(ValueError):validate(root/'go.json',gh,root/'phase.json',ph,now=1000)

if __name__=='__main__':unittest.main()
