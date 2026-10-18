import unittest
import host_guard as g
class GuardTests(unittest.TestCase):
 def setUp(self):
  from unittest.mock import patch
  self.persist=patch.object(g,'save_owned').start()
  self.addCleanup(patch.stopall)
 def sample(self,**kw):
  s=dict(pressure=1,swap_bytes=0,disk_free=30*g.GIB,owned_rss=0);s.update(kw);return s
 def test_normal(self):self.assertEqual(g.reasons(self.sample()),[])
 def test_pressure_warning(self):
  self.assertEqual(g.reasons(self.sample(pressure=2)),[])
  self.assertTrue(g.can_resume(self.sample(pressure=2)))
  self.assertIn('owned_rss',g.reasons(self.sample(pressure=2,owned_rss=2*g.GIB)))
  self.assertTrue(g.can_resume(self.sample(pressure=2,swap_bytes=5*g.GIB)))
 def test_critical(self):self.assertIn('memory_pressure',g.reasons(self.sample(pressure=4)))
 def test_memory(self):self.assertIn('owned_rss',g.reasons(self.sample(owned_rss=2*g.GIB)))
 def test_disk(self):self.assertIn('disk_free',g.reasons(self.sample(disk_free=9*g.GIB)))
 def test_swap(self):self.assertIn('swap_used',g.reasons(self.sample(swap_bytes=6*g.GIB)))
 def test_unknown_fails_closed(self):self.assertIn('observation_unavailable',g.reasons(None))
 def test_hysteresis(self):
  self.assertFalse(g.can_resume(self.sample(disk_free=12*g.GIB)))
  self.assertTrue(g.can_resume(self.sample(swap_bytes=5*g.GIB)))
  self.assertTrue(g.can_resume(self.sample()))
 def test_residual_swap_does_not_block_normal_low_load_resume(self):
  self.assertTrue(g.can_resume(self.sample(swap_bytes=5*g.GIB)))
  self.assertTrue(g.can_resume(self.sample(pressure=2,swap_bytes=5*g.GIB)))
  self.assertFalse(g.can_resume(self.sample(swap_bytes=6*g.GIB)))
 def test_observed_allowed_pressure_and_residual_swap_can_resume(self):
  self.assertTrue(g.can_resume(self.sample(pressure=2,swap_bytes=4370989056)))
  self.assertFalse(g.can_resume(self.sample(pressure=2,swap_bytes=5*g.GIB,owned_rss=g.GIB)))
  self.assertFalse(g.can_resume(self.sample(pressure=2,swap_bytes=6*g.GIB)))
 def test_tree_does_not_include_unrelated(self):
  rows={10:(1,100,'a'),11:(10,200,'b'),12:(11,300,'c'),50:(1,9000,'d')}
  self.assertEqual(g.descendants(rows,10),{10,11,12})
 def test_swap_units(self):self.assertEqual(g.parse_swap('total = 2.00G used = 1347.94M free = 700.06M'),int(1347.94*1024**2))
 def test_tracked_orphan_counts_and_pid_reuse_does_not(self):
  rows={10:(1,100,(1,1)),11:(1,200,(2,2)),12:(1,300,(4,4))}
  self.assertEqual(g.owned_ids(rows,10,{11:(2,2),12:(3,3)}),{10,11})
 def test_reaped_root_pid_reuse_is_not_signalled(self):
  from unittest.mock import Mock,patch
  child=Mock(pid=10);child.poll.return_value=0
  rows={10:(1,100,(9,9)),11:(10,200,(9,10))}
  with patch.object(g,'process_rows',return_value=rows),patch.object(g.os,'kill') as kill,patch.object(g.time,'sleep'):
   g.terminate(child,{10:(1,1)})
  kill.assert_not_called();child.terminate.assert_not_called()
 def test_tracked_exec_identity_survives(self):
  from unittest.mock import Mock,patch
  child=Mock(pid=10);child.poll.return_value=0
  rows={11:(1,200,(2,2))}
  with patch.object(g,'process_rows',side_effect=[rows,{}]),patch.object(g.os,'kill') as kill,patch.object(g.time,'sleep'):
   g.terminate(child,{11:(2,2)})
  kill.assert_called_once_with(11,g.signal.SIGTERM)
 def test_existing_consumer_lock(self):
  from unittest.mock import patch
  from pathlib import Path
  import tempfile,fcntl
  with tempfile.TemporaryDirectory() as root:
   folder=Path(root)/'project/research-state/harness/consumers';folder.mkdir(parents=True)
   with (folder/'consumer.lock').open('w') as f,patch.object(g,'ROOT',Path(root)):
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    self.assertTrue(g.consumer_present())
 def test_unreadable_owned_pid_is_not_absent(self):
  rows={10:(1,100,(1,1)),11:(1,1000,None)}
  self.assertIn(11,g.owned_ids(rows,10,{11:(2,2)}))
 def test_final_discovered_descendant_is_retained(self):
  from unittest.mock import Mock,patch
  child=Mock(pid=10);child.poll.side_effect=[None,None]
  rows={10:(1,100,(1,1)),11:(10,200,(2,2))};tracked={10:(1,1)}
  with patch.object(g,'process_rows',side_effect=[rows,{},{}]),patch.object(g.time,'sleep'):
   g.terminate(child,tracked)
  self.assertEqual(tracked[11],(2,2))
  self.persist.assert_called_with(tracked)
 def test_ledger_write_failure_still_stops_child(self):
  from unittest.mock import Mock,patch
  child=Mock(pid=10);child.poll.side_effect=[None,None]
  self.persist.side_effect=OSError('disk full')
  with patch.object(g,'process_rows',side_effect=[{10:(1,100,(1,1))},{},{}]),patch.object(g.time,'sleep'):
   with self.assertRaises(RuntimeError):g.terminate(child,{10:(1,1)})
  child.terminate.assert_called_once()

 def test_resource_sample_keeps_rss_when_child_identity_is_unavailable(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  rows={10:(1,100,(1,1)),11:(10,200,None)}
  with patch.object(g.subprocess,'check_output',side_effect=['2','used = 4.00G']), patch.object(g,'process_rows',return_value=rows), patch.object(g.shutil,'disk_usage',return_value=SimpleNamespace(free=30*g.GIB)):
   observation=g.observe(10,{})
  self.assertIsNotNone(observation)
  self.assertEqual(observation['owned_rss'],300)
  self.assertEqual(g.reasons(observation),[])

 def test_unknown_identity_rss_still_enforces_memory_limit(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  rows={10:(1,100,(1,1)),11:(10,2*g.GIB,None)}
  with patch.object(g.subprocess,'check_output',side_effect=['2','used = 4.00G']), patch.object(g,'process_rows',return_value=rows), patch.object(g.shutil,'disk_usage',return_value=SimpleNamespace(free=30*g.GIB)):
   observation=g.observe(10,{})
  self.assertIsNotNone(observation)
  self.assertIn('owned_rss',g.reasons(observation))

if __name__=='__main__':unittest.main()
