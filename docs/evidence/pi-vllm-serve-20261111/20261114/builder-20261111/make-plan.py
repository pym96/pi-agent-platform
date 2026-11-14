import json,pathlib,hashlib
root=pathlib.Path(__file__).parent
base='List every integer from 1 through 400, comma-separated, with no explanation. '
def direct(i,budget,action='direct'):return {'id':i,'action':action,'budget':budget,'prompt':base+i}
def platform(i,action='platform'):return {'id':i,'action':action,'budget':128,'session':'g2-b-'+i,'prompt':base+i}
normal=[direct('direct16',16),direct('direct64',64),direct('cancel128',128,'disconnect'),direct('aftercancel16',16),platform('platform-a'),platform('platform-b'),platform('sse-replay','sse_disconnect'),{**platform('api-restart','restart'),'queued_prompt':base+'queued-must-not-execute'},platform('new-session')]
plans={
 'normal':{'criteria':'C-G2-03@1.1','kind':'real-model-functional','role':'builder','generation_timeout':30,'steps':normal},
 'deadline':{'criteria':'C-G2-03@1.1','kind':'real-model-functional','role':'builder','generation_timeout':0.001,'steps':[direct('deadline128',128,'deadline')]},
 'recovery':{'criteria':'C-G2-03@1.1','kind':'real-model-functional','role':'builder','generation_timeout':30,'steps':[direct('afterdeadline16',16)]},
 'fallback':{'criteria':'C-G2-03@1.1','kind':'real-model-functional','role':'builder','generation_timeout':30,'steps':[direct('fallback16',16)]}}
for name,plan in plans.items():
 p=root/('plan-'+name+'.json');p.write_text(json.dumps(plan,indent=2));print(name,hashlib.sha256(p.read_bytes()).hexdigest())
