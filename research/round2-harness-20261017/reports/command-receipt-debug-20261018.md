# Command-agent receipt dispatch fix

A B01 child declared two artifact outputs without a separate command_response_path; dispatcher raised before claiming a run and LaunchAgent restarted the same error. The never-started task was retained as cancelled and B01 returned through its standard inspection/repair path. No scientific execution was fabricated.

Runtime source commit: 32e3746 (full revision in patch). Fix shares receipt preflight between proposal admission and dispatch. Invalid proposals are rejected early. A legacy malformed execution task is cancelled transactionally only if never started, then program consumes its cancellation in the same step. Running/previously attempted tasks cannot be retired by this path.

Validation: reproduced original ContractError in a failing regression, then 5 focused tests passed, including real SQLite cancellation and attempted-task preservation. Independent static review found no blocking issue. Skill bytes unchanged. Source patch is supplied here; live adoption waits for a no-running-task boundary and records receipt-fix-adoption-20261018.json. This report itself does not claim adoption or completed GPU experiments.

## Deployment observed
Runtime source 32e37467bfad424655f10dc844a318275018e9b5 adopted at a no-running-task boundary; same SQLite/cursor/budget retained, service restarted. Five focused regression tests and 38 existing controller tests passed. The repaired B01 child was independently reviewed and materialized. Adoption ledger records old/new policy; this does not claim that child completed or GPU training began.
