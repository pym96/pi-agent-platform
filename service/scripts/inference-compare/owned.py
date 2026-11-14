"""Reuse exact-ID reconciliation at a new issue28 label seam; never invoke old GO."""
import importlib.util,ipaddress,json,subprocess
from pathlib import Path
from authority import nonce,digest

spec=importlib.util.spec_from_file_location('_pi28_exact_docker',Path(__file__).resolve().parents[1]/'vllm-serve/owned.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

class OwnedDocker(base.OwnedDocker):
    def __init__(self,role,sha,model_nonce,runner=None):
        if role not in ('builder','regulator'):raise ValueError('issue28 role')
        digest(sha,40);nonce(model_nonce)
        self.project='pi-compare28-'+('b' if role=='builder' else 'r')
        self.labels={'workorder':'28','execution-sha':sha,'com.docker.compose.project':self.project,'pi28.nonce':model_nonce}
        self.receipts=[]
        self.runner=runner or (lambda args:subprocess.run(['docker',*args],capture_output=True,text=True,timeout=8))

    def network(self,ident):
        digest(ident);r=self.command(['network','inspect',ident])
        if r.returncode:raise RuntimeError('network inventory unknown')
        rows=json.loads(r.stdout)
        if len(rows)!=1 or rows[0]['Id']!=ident:raise ValueError('network exact identity')
        row=rows[0]
        if row['Internal'] is not True or any(row.get('Labels',{}).get(k)!=v for k,v in self.labels.items()):raise ValueError('network ownership/internal')
        return row

    def create_network(self):
        args=['network','create','--internal']
        for k,v in self.labels.items():args+=['--label',k+'='+v]
        r=self.command([*args,self.project+'-'+self.labels['pi28.nonce']])
        if r.returncode:raise RuntimeError('network creation failed')
        ident=r.stdout.strip();self.network(ident);return ident

    def remove_network(self,ident):
        row=self.network(ident)
        if row['Containers']:raise RuntimeError('network is not empty')
        r=self.command(['network','rm',ident]);inventory=self.command(['network','ls','-q','--no-trunc'])
        if r.returncode or inventory.returncode or ident in inventory.stdout.splitlines():raise RuntimeError('network cleanup unknown')
        return {'network_id':ident,'removed':True}

    def endpoint(self,cid,network_id):
        net=self.network(network_id);row=self.inspect(cid)
        if row is None or not row['State']['Running']:raise ValueError('live model required')
        if row['HostConfig'].get('PortBindings') or any(row['NetworkSettings'].get('Ports',{}).values()):raise ValueError('host ports prohibited')
        nets=list(row['NetworkSettings']['Networks'].values())
        if len(nets)!=1 or nets[0]['NetworkID']!=network_id:raise ValueError('single exact network')
        ip=nets[0]['IPAddress'];addr=ipaddress.ip_address(ip)
        if addr.version!=4 or not addr.is_private or addr.is_loopback or addr.is_unspecified:raise ValueError('private IPv4')
        if net['Containers'].get(cid,{}).get('IPv4Address','').split('/')[0]!=ip:raise ValueError('network membership')
        return 'http://'+ip+':8082'
