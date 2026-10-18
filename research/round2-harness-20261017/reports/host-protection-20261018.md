# Local host protection — 2026-10-18

## Evidence and limits
The local retired panic report dated 2026-10-18 01:52:21 contains watchdogd's 90-second timeout, compressor segment limit 100%, and 24 swapfiles with LOW swap space. This supports investigating severe memory pressure; it does not establish which historical process caused it or prove a unique root cause. Full private diagnostic reports are not included.

## Deployed repair
The local LaunchAgent now runs ops/host_guard.py in the existing Harness venv. It retains the same database, research project, model and accounting history. The previous caffeinate wrapper was removed. Research has no new aggregate round/time cap.

The guard polls every 5 seconds and stops/admission-blocks its own consumer at non-normal or unavailable memory pressure, owned process-tree RSS >=2 GiB, Swap >=6 GiB, or free disk <10 GiB. Resume requires 60 seconds of healthy observations, Swap <=4 GiB and free disk >=15 GiB. These are host protection thresholds, not a research budget. Polling is not a hard memory limit and cannot guarantee prevention of another kernel panic.

A singleton lock, consumer-lock check, bounded rotating logs, restart backoff, process creation identities and a persistent descendant ledger prevent duplicate launch and reduce orphan/PID-reuse cleanup risks. Only owned local processes are targeted. User applications and remote GPU jobs are not terminated. Unknown process identity causes waiting rather than an unsafe signal. Local interruption reconciliation requires recorded command ownership and an interruption journal; external jobs must still be reconciled before retry.

## Adoption and research status
The local planner worker 23 was stopped for maintenance; its recorded 86.8548 seconds were preserved and the interrupted invocation reconciled as failed due to maintenance, not a scientific result. B01 scoring qualification remains unfinished; no new training result is claimed.

At the post-deployment observation the guard was running in resource_wait, kernel pressure value 2, Swap about 1.98 GiB and free disk about 33.2 GiB. The research consumer was absent. It resumes automatically only after healthy admission conditions and no unresolved owned processes.

## Validation
17 focused mocked unit tests passed. Coverage includes pressure/Swap/disk/RSS thresholds, hysteresis, unrelated processes, PID reuse, exec identity, orphan accounting, consumer locks, unavailable identities, final descendant ledger persistence and cleanup after ledger-write failure. No deliberate memory exhaustion or panic reproduction was performed. Static review findings were addressed before deployment.
