# Warning-level continuation — 2026-10-18

Supersedes the pressure admission condition in host-protection-20261018.md. The user requested continued research and questioned indefinite waiting on pressure 2. Apple XNU kern_memorystatus_notify.c converts this sysctl to dispatch notification levels; bsd/sys/event_private.h defines normal=1, warning=2, critical=4. Warning alone does not establish imminent panic.

Observed at 09:53 UTC: pressure 2, Swap 1952.12 MiB (decreased from earlier 2024.12 MiB), free disk about33 GiB. vm_stat compressor occupied about6.8 GiB, so real memory pressure remains; no claim of zero risk or a diagnosed panic cause. memory_pressure -Q reported40%, which is not a direct count of unused physical RAM.

Only pressure admission changed: allow 1 or2 for lightweight local orchestration. Unknown/critical values still stop. Owned RSS2GiB, Swap6GiB, disk10GiB stop checks, resumeSwap4GiB/disk15GiB/60seconds, singleton and descendant cleanup remain. Heavy experiments stay on the authorized remoteGPU. No research cursor or history reset.17focused tests passed after adapting warning expectations and checking warning does not bypass other thresholds.

Sources:
- https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_memorystatus_notify.c
- https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/event_private.h
