#!/usr/bin/env python3
"""Offline artifact checks; independent review and disclosure remain separate."""
from pathlib import Path
import json, subprocess, re, hashlib, xml.etree.ElementTree as ET
p=Path(__file__).resolve().parent
def norm(s): return re.sub(r'\s+','',s).replace('--','–')
source=json.loads((p/'claims.json').read_text())
results=[]
for name,variant in source['variants'].items():
 d=p/name
 info=subprocess.check_output(['pdfinfo',str(d/'resume.pdf')],text=True)
 assert re.search(r'Pages:\s+1\b',info),name
 assert '595.28 x 841.89 pts (A4)' in info,name
 fonts=subprocess.check_output(['pdffonts',str(d/'resume.pdf')],text=True)
 rows=fonts.splitlines()[2:]
 assert rows and all(re.search(r'\byes\s+yes\s+(?:yes|no)\b',r) for r in rows),fonts
 subprocess.run(['pdftotext','-layout',str(d/'resume.pdf'),str(d/'resume.txt')],check=True)
 text=(d/'resume.txt').read_text(); md=(d/'resume.md').read_text(); tex=(d/'resume.tex').read_text()
 assert '候选草稿·禁止投递' in norm(text)
 assert 'Overfull' not in (d/'resume.log').read_text()
 for cid in variant['claims']:
  sentence=source['claims'][cid]['text']
  assert norm(sentence) in norm(text),(name,cid,'PDF text missing')
  assert sentence in md,(name,cid,'Markdown missing')
 # Every contribution is a single rendered line, not only one source line.
 lines=[norm(x) for x in text.splitlines()]
 bullets=re.findall(r'\\item (.+)',tex)
 for b in bullets:
  b=b.replace('\\_','_').replace('\\&','&').replace('\\%','%')
  assert any(norm(b) in line for line in lines),(name,b,'contribution wrapped')
 assert all('\\textbf' not in b for b in bullets)
 results.append({'variant':name,'pages':1,'size':'A4','fonts_embedded':True,'overfull':False,'all_claims_in_pdf_and_md':True,'single_line_contributions':len(bullets),'pdf_sha256':hashlib.sha256((d/'resume.pdf').read_bytes()).hexdigest(),'font_report':fonts})
(p/'validation.json').write_text(json.dumps({'variants':results},ensure_ascii=False,indent=2)+'\n')
# Check operational navigation; snapshot copies retain original context links by design.
links=[]
for file in [p/'README.md',p/'fact-map.md',p/'disclosure-review.md',p/'research/README.md',p.parent/'README.md']:
 for target in re.findall(r'\]\(([^)]+)\)',file.read_text()):
  if '://' in target or target.startswith('#'):continue
  dest=(file.parent/target.split('#')[0]).resolve()
  assert dest.exists(),(str(file),target)
  links.append({'file':str(file.relative_to(p.parent)),'target':target})
result={'checks':'Builder offline artifact checks only, not independent Verdict','variants':results,'navigation_links_checked':len(links)}
(p/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'variants':len(results),'contributions':sum(x['single_line_contributions'] for x in results),'navigation_links':len(links)},ensure_ascii=False))
