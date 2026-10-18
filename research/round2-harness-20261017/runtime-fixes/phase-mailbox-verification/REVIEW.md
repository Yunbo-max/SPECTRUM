# Controller-owned phase mailbox repair review

Independent static reviewer: /root/mailbox_review, 2026-10-18.

Initial review found that FIFO request files could block the heartbeat loop and
that replacing the mailbox directory could redirect controller file operations.
Both were fixed with nonblocking/no-follow regular-file reads and a retained
directory descriptor. Added GPU-host behavior tests cover both cases.

Final review found no remaining important issue. Worker DB access is removed;
trusted parent context, original request identity, native fencing, receipts and
accounting remain in the controller. Cleanup uses try/finally. The real subprocess
integration denies all SQLite connection attempts in the client while the actual
CommandWorker log/heartbeat pump serves a native call exceeding its parent lease.

The B-memory/C evidence loop stays within one sustained worker. Source refresh,
negative evidence, experiment revision and problem reselection preserve independent
B05/D/formal-E gates. Review is static; execution results are in adjacent GPU logs.

The 2-second synthetic parent lease expired during real admission validation in
the full run (runtime-short-lease.log). The integration fixture now uses a
10-second lease and deliberately waits 12 seconds before native execution;
production's existing 60-second lease and ownership checks are unchanged.
The isolated real mailbox test passed in 17.617s (real-mailbox.log).
