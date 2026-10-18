# B01 command-dispatch incident and required recovery

Parent observed repeated consumer_failed ContractError: multiple outputs require a separate command_response_path receipt. Source: program_cli.py command adapter preflight, before CommandWorker claims any run. Task spectrum.B01.scorer-source-binding.000002 has two artifact outputs, no parameters.command_response_path, state pending and attempt=null. This is a task-contract defect, not scientific failure or completed source work. Automatic process restart repeats it unchanged.

Recovery uses Controller.cancel_pending for this never-started task with its observed reason; preserve its immutable contract and history. Program execute will read the cancellation receipt and return to the SAME B01 step for an independently reviewed replacement. Do not skip B01 or mark source binding completed.

Replacement task must declare a FRESH standalone .json receipt in outputs and set parameters.command_response_path to that exact path, separate from the report and evidence JSON. Follow command-agent response schema and retain old cancellation receipt in inputs. Reviewer must check this before acceptance. Do not use the evidence JSON as the final-response receipt or overwrite historical outputs. Apply this transport check to every later command-agent child task with multiple outputs. Native tasks retain their own schema.
