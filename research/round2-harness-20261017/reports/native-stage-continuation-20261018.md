# Native-stage repair and B02 continuation

- Source: bd949b68d6eecb9feaf82ee3fe2dc0c666fc21ac, Work Harness 0.4.0-harness.7.
- Reviewed repair: separate scorer-independent preparation/check/calibration/training/export; full comparison, code/data and pending scoring obligations stay pinned. Runtime supplies actual execution identity; controller authenticates predecessor history; successful outputs publish exclusively to declared paths. Later scoring and M05 retain precise export lineage. Scientific gates are unchanged.
- hn01 software checks: 121 runtime, final 46 stage, 36 legacy runner/Harness, 18 host guard checks passed. Counts overlap where suites inherit fixtures. The 52 existing B02 diagnostic software checks also passed; none are claimed as scientific experiment results.
- Official plugin install succeeded for main and dedicated Harness profiles; all 413 exported Skill files matched. Other plugin manifests unchanged. GPU production Skill digest matches the adopted source.
- Live source adoption at revision237 preserved B02 cursor, accepted evidence and resource accounting. The old worker was already absent and its guard-interrupted attempt was reconciled as failed, not scientifically accepted. Physical DB backup retained locally. A one-off migration import error occurred before state mutation and was corrected before successful adoption.
- Guard stop thresholds remain; after 60 seconds stable normal pressure and low owned RSS, residual swap below the existing stop threshold no longer prevents restart indefinitely.
- Next work is the versioned B02 wrapper/stage-entry adapter, independent review and actual prepare/calibrate/diagnostic execution using the existing hn01 4090/environment/model/MBPP inputs. Final scorer remains unqualified; no six-arm predictions or benchmark score improvement is claimed.

Live worker readback and Git delivery are recorded separately.
