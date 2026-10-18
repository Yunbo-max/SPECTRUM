import json,time,traceback
started=time.time()
result={'kind':'cuda-precision-smoke','scientific_score':False}
try:
 import torch
 result.update(torch_version=torch.__version__,device=torch.cuda.get_device_name(0),compute_capability=list(torch.cuda.get_device_capability(0)),bf16_supported_including_emulation=torch.cuda.is_bf16_supported(),bf16_native_supported=torch.cuda.is_bf16_supported(including_emulation=False))
 for name,dtype in [('fp32',torch.float32),('fp16',torch.float16)]:
  a=torch.ones((256,256),device='cuda',dtype=dtype)
  c=a@a
  torch.cuda.synchronize()
  result[name]={'all_finite':bool(torch.isfinite(c).all().item()),'max_abs_error':float((c.float()-256).abs().max().item())}
 result['peak_allocated_bytes']=torch.cuda.max_memory_allocated()
 result['status']='completed'
except Exception:
 result.update(status='failed',error=traceback.format_exc())
result['elapsed_seconds']=time.time()-started
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['status']=='completed' else 1)
