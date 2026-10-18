import subprocess,json,pathlib,time
p=pathlib.Path(__file__).parent
t=time.monotonic()
r=subprocess.run(['/root/rivermind-data/spectrum-harness/venv/bin/python', '-m', 'pip', 'install', '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple', 'vllm==0.10.0', 'transformers==4.53.3', 'ray==2.48.0'])
(p/'install-exit.json').write_text(json.dumps({'returncode':r.returncode,'seconds':time.monotonic()-t}))
