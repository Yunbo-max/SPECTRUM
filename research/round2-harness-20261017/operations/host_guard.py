"""Bounded macOS supervisor for this project's local consumer, not remote jobs."""
import ctypes, fcntl, json, os, re, selectors, shutil, signal, sqlite3, subprocess, sys, time
from pathlib import Path
GIB=1024**3
ROOT=Path(__file__).resolve().parents[1]
STOP=False

def parse_swap(value):
 m=re.search(r'used\s*=\s*([\d.]+)([KMGTP])',value)
 if not m:raise ValueError('unrecognized swap observation')
 return int(float(m[1])*1024**('KMGTP'.index(m[2])+1))

# Darwin dispatch levels: 1 normal, 2 warning, 4 critical.
# Warning alone permits lightweight control; all other resource checks remain.
def reasons(s):
 if s is None:return ['observation_unavailable']
 return [name for name,bad in [('memory_pressure',s['pressure'] not in (1,2)),('swap_used',s['swap_bytes']>=6*GIB),('disk_free',s['disk_free']<10*GIB),('owned_rss',s['owned_rss']>=2*GIB)] if bad]

def can_resume(s):
 # Old swap can persist after pressure normalizes; allow low-load recovery
 # under the same 6 GiB stop threshold after the existing 60-second stability window.
 return not reasons(s) and s['disk_free']>=15*GIB and (s['swap_bytes']<=4*GIB or (s['pressure']==1 and s['owned_rss']<GIB))

def descendants(rows,pid):
 owned={pid}
 while True:
  more={p for p,(parent,_,_) in rows.items() if parent in owned}
  if more<=owned:return owned
  owned|=more

class ProcBSDInfo(ctypes.Structure):
 # Darwin SDK sys/proc_info.h PROC_PIDTBSDINFO, microsecond creation identity.
 _fields_=[('prefix',ctypes.c_uint32*12),('comm',ctypes.c_char*16),('name',ctypes.c_char*32),('counts',ctypes.c_uint32*5),('nice',ctypes.c_int32),('seconds',ctypes.c_uint64),('microseconds',ctypes.c_uint64)]

_LIBPROC=None
def process_identity(pid):
 global _LIBPROC
 if _LIBPROC is None:
  _LIBPROC=ctypes.CDLL('/usr/lib/libproc.dylib')
  _LIBPROC.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
  _LIBPROC.proc_pidinfo.restype=ctypes.c_int
 info=ProcBSDInfo()
 if _LIBPROC.proc_pidinfo(pid,3,0,ctypes.byref(info),ctypes.sizeof(info))!=ctypes.sizeof(info):return None
 return (int(info.seconds),int(info.microseconds))

def process_rows():
 out=subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,rss='],text=True,timeout=3)
 rows={}
 for line in out.splitlines():
  a=line.split()
  if len(a)==3:
   pid=int(a[0]);identity=process_identity(pid)
   rows[pid]=(int(a[1]),int(a[2])*1024,identity)
 return rows

def owned_ids(rows,pid,tracked):
 return descendants(rows,pid)|{p for p,identity in (tracked or {}).items() if p in rows and (rows[p][2] is None or identity is None or rows[p][2]==identity)}

def consumer_present():
 for path in (ROOT/'project/research-state/harness/consumers').glob('*.lock'):
  with path.open('a') as f:
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:return True
 return False

def observe(pid=None,tracked=None):
 try:
  pressure=int(subprocess.check_output(['/usr/sbin/sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True,timeout=3).strip())
  swap=parse_swap(subprocess.check_output(['/usr/sbin/sysctl','-n','vm.swapusage'],text=True,timeout=3))
  rows=process_rows() if pid else {}
  owned=owned_ids(rows,pid,tracked) if pid else set()
  if any(p in rows and rows[p][2] is None for p in owned):return None
  return dict(pressure=pressure,swap_bytes=swap,disk_free=shutil.disk_usage(ROOT).free,owned_rss=sum(rows[p][1] for p in owned if p in rows))
 except (OSError,ValueError,subprocess.SubprocessError):return None

def rotate(path,limit=2*1024*1024):
 if path.exists() and path.stat().st_size>=limit:
  older=path.with_suffix(path.suffix+'.2');previous=path.with_suffix(path.suffix+'.1')
  if previous.exists():os.replace(previous,older)
  os.replace(path,previous)

def event(kind,**data):
 p=ROOT/'logs/host-guard.log';rotate(p)
 with p.open('a') as f:f.write(json.dumps(dict(time=time.time(),event=kind,**data))+'\n')
 state=ROOT/'logs/host-guard-status.json';temp=state.with_suffix('.tmp')
 temp.write_text(json.dumps(dict(time=time.time(),event=kind,**data),indent=2));os.replace(temp,state)

def terminate(child, tracked=None):
 # Capture identities before termination; never signal restored/reused PIDs.
 owned=dict(tracked or {})
 # A still-live Popen child cannot have had its PID recycled. Once reaped,
 # only retained identities are authority; never rediscover from that PID.
 if child.poll() is None:
  try:
   rows=process_rows()
   for p in descendants(rows,child.pid):
    if p in rows and (rows[p][2] is not None or p not in owned):owned[p]=rows[p][2]
  except (OSError,subprocess.SubprocessError):pass
 persistence_failed=False
 if tracked is not None:
  tracked.update(owned)
  try:save_owned(tracked)
  except OSError:persistence_failed=True
 if child.poll() is None:child.terminate()
 try:child.wait(timeout=10)
 except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
 try:current=process_rows()
 except (OSError,subprocess.SubprocessError):return
 for pid,identity in owned.items():
  if identity is not None and pid in current and current[pid][2]==identity:
   try:os.kill(pid,signal.SIGTERM)
   except ProcessLookupError:pass
 time.sleep(1)
 try:current=process_rows()
 except (OSError,subprocess.SubprocessError):return
 for pid,identity in owned.items():
  if identity is not None and pid in current and current[pid][2]==identity:
   try:os.kill(pid,signal.SIGKILL)
   except ProcessLookupError:pass

 if persistence_failed:raise RuntimeError('ownership ledger write failed; local cleanup attempted; do not assume recovery')

def settle_local_interruptions(tracked):
 # Only settle this guard's observed local command process after verified exit.
 # This does not settle SSH/GPU jobs or imply external side effects completed.
 from research_autopilot.controller import Controller
 c=Controller(ROOT/'runtime/controller.sqlite')
 rows=process_rows()
 if any(pid in rows and (identity is None or rows[pid][2] is None or rows[pid][2]==identity) for pid,identity in tracked.items()):
  event('cleanup_unresolved');return False
 for task in c.status('spectrum-round2-work-harness')['tasks']:
  a=task.get('attempt')
  if task['state']!='reconcile_required' or not a or not a['owner'].startswith('spectrum-guarded.'):continue
  session=a.get('session_id') or ''
  if not session.startswith('command:'):continue
  try:pid=int(session.rsplit(':',1)[1])
  except ValueError:continue
  if pid not in tracked:continue
  f=ROOT/'project/.runtime/command-agent'/a['run_id']/'interruption.json'
  if not f.exists():continue
  record=json.loads(f.read_text())
  if not record.get('cleanup',{}).get('leader_stopped'):continue
  c.reconcile(a['run_id'],a['owner'],a['fence'],outcome='failed',
   reason='Host resource guard interrupted this local invocation; observed owned processes exited. Preserve partial outputs and reconcile any external jobs before retry.',actual_seconds=record['actual_seconds'])
  event('local_interruption_reconciled',run_id=a['run_id'])
 return True

def save_owned(tracked):
 path=ROOT/'logs/host-guard-owned.json';temp=path.with_suffix('.tmp')
 temp.write_text(json.dumps({str(pid):identity for pid,identity in tracked.items()}));os.replace(temp,path)

def retained_owned_alive():
 path=ROOT/'logs/host-guard-owned.json'
 if not path.exists():return False
 try:
  tracked=json.loads(path.read_text());rows=process_rows()
  return any(int(pid) in rows and (identity is None or rows[int(pid)][2] is None or tuple(identity)==rows[int(pid)][2]) for pid,identity in tracked.items())
 except (OSError,ValueError,subprocess.SubprocessError):return True

def phase():
 with sqlite3.connect(ROOT/'runtime/controller.sqlite',timeout=3) as db:
  return json.loads(db.execute('select state from research_programs where project_id=?',('spectrum-round2-work-harness',)).fetchone()[0])['phase']

def main():
 global STOP
 def stop(*_):
  global STOP
  STOP=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 lock=(ROOT/'logs/host-guard.lock').open('a')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  lock.close();return
 child=None;tracked={};healthy_since=None;backoff=30;last_wait=0
 try:
  while not STOP:
   if phase()!='active':event('program_not_active',phase=phase());return
   if retained_owned_alive():
    event('prior_owned_processes_unreconciled');time.sleep(30);continue
   s=observe()
   if not can_resume(s):
    healthy_since=None
    if time.monotonic()-last_wait>=30:event('resource_wait',reasons=reasons(s),snapshot=s);last_wait=time.monotonic()
    time.sleep(5);continue
   if healthy_since is None:healthy_since=time.monotonic()
   if time.monotonic()-healthy_since<60:time.sleep(5);continue
   if consumer_present():
    event('existing_consumer_wait');healthy_since=None;time.sleep(5);continue
   argv=[str(ROOT/'venv/bin/python'),'-m','research_autopilot.program_cli','--db',str(ROOT/'runtime/controller.sqlite'),'run','spectrum-round2-work-harness','--owner','spectrum-guarded','--poll-seconds','5']
   child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,bufsize=0)
   event('consumer_started',pid=child.pid,snapshot=s)
   start=time.monotonic();next_check=0;limited=False;tracked={}
   with selectors.DefaultSelector() as sel:
    for stream,name in [(child.stdout,'consumer-autonomous.log'),(child.stderr,'consumer-autonomous.err.log')]:
     os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,name)
    while child.poll() is None and not STOP:
     if time.monotonic()>=next_check:
      s=observe(child.pid,tracked);next_check=time.monotonic()+5
      try:
       rows=process_rows();tracked.update({p:rows[p][2] for p in descendants(rows,child.pid) if p in rows})
      except (OSError,subprocess.SubprocessError):pass
      save_owned(tracked)
      if reasons(s):
       event('resource_stop',reasons=reasons(s),snapshot=s,pid=child.pid);limited=True;terminate(child,tracked);break
     for key,_ in sel.select(timeout=1):
      data=os.read(key.fileobj.fileno(),65536)
      if not data:sel.unregister(key.fileobj);continue
      path=ROOT/'logs'/key.data;rotate(path)
      with path.open('ab') as f:f.write(data)
   terminate(child,tracked)  # also clean observed orphan MCP/tool children after exit
   rc=child.poll();child.stdout.close();child.stderr.close();child=None
   if not settle_local_interruptions(tracked):return
   save_owned({})
   event('consumer_stopped',exit_code=rc,resource_limited=limited)
   healthy_since=None
   if STOP:return
   if phase()!='active':return
   if time.monotonic()-start>300:backoff=30
   event('restart_backoff',seconds=backoff)
   for _ in range(backoff):
    if STOP:return
    time.sleep(1)
   backoff=min(600,backoff*2)
 finally:
  if child is not None:terminate(child,tracked)
  event('guard_stopped')
  lock.close()

if __name__=='__main__':main()
