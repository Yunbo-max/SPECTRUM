"""CPU-only integration probes of unchanged author code; no model benchmark."""
from pathlib import Path
import importlib.util,json,torch
S=Path('/root/rivermind-data/spectrum-harness/project/research-state/adaptive-decoder-source-review-20261019')
torch.set_num_threads(1)
spec=importlib.util.spec_from_file_location('author_top_h',S/'top-h/logit_processor.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=[]
for name,n,a in [('uniform-default-alpha',100,.4),('uniform-allowed-alpha-one',100,1.),('single-candidate',1,.4)]:
    try:
        y=m.TopH_LogitsProcessor(top_n=n,temperature=1.,alpha=a)(torch.zeros((1,1),dtype=torch.long),torch.zeros((1,128)))
        row={'case':name,'top_n':n,'alpha':a,'outcome':'returned','retained_tokens':int(torch.isfinite(y).sum())}
    except Exception as e:
        row={'case':name,'top_n':n,'alpha':a,'outcome':type(e).__name__,'message':str(e)}
    rows.append(row)
result={'software_only':True,'device':'cpu on hn01; one Torch CPU thread, no model loaded','source_commit':'8b94d62b238ed62793627f4a2556d90188560854','cases':rows,'interpretation':'Boundary-condition integration checks of unchanged author processor, not model performance; default-alpha success does not validate a future vLLM port.'}
print(json.dumps(result,indent=2))
