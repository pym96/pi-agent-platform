import unittest
from plan import freeze_rates, formal_blocks

class PlanTests(unittest.TestCase):
    def test_frozen_plan_rejects_missing_slot_and_retuned_offsets(self):
        from plan import validate_frozen_plan
        calibration={'A_ns':[10**9]*6,'B_ns':[2*10**9]*6}
        rates=freeze_rates(calibration['A_ns'],calibration['B_ns'])
        plan={'stage':'formal','calibration':calibration,'rates':rates,'blocks':formal_blocks(rates)}
        validate_frozen_plan(plan)
        plan['blocks'][0]['points'][0]['slots'].pop()
        with self.assertRaises(ValueError):validate_frozen_plan(plan)
        plan['blocks']=formal_blocks(rates);plan['blocks'][0]['points'][1]['offset_ns'][1]+=1
        with self.assertRaises(ValueError):validate_frozen_plan(plan)

    def test_pilot_calibration_freezes_shared_offsets_and_abba(self):
        rates=freeze_rates([1_000_000_000]*6,[2_000_000_000]*6)
        self.assertEqual(rates['low']['rate'], '0.25')
        self.assertEqual(rates['low']['offset_ns'], [k*4_000_000_000 for k in range(20)])
        self.assertEqual(rates['low']['offer_end_ns'],80_000_000_000)
        blocks=formal_blocks(rates)
        self.assertEqual([b['id'] for b in blocks],['A1','B1','B2','A2'])
        self.assertEqual(sum(len(p['slots']) for b in blocks for p in b['points']),480)
        self.assertEqual(blocks[2]['points'][0]['name'],'openhigh')
        self.assertEqual(blocks[0]['points'][1]['offset_ns'],blocks[1]['points'][1]['offset_ns'])

if __name__=='__main__':unittest.main()
