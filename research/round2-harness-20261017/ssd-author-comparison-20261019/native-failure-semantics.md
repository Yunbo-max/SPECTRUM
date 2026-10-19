# Native failure and timeout semantics

Source: SSD author commit 2637d2021f1bc523385b48a1f88ea9aa4812b0a9, evaluation/livecodebench_utils.py:655–716 and evaluation/benchmark.py:134–214, preserved in adapted/evaluation with unchanged scoring functions. This is source inspection plus read-only test metadata analysis on hn01, not a model result.

The author child executes tests in order and returns on the first failed test. lcb_run fills every unreturned slot with a failure whose text says `Error: Time out!`, including slots skipped after an ordinary incorrect answer. Thus num_tests_failed counts both observed failures and unexecuted padded slots. It is not a count of independently observed incorrect tests. A timeout label in a padded slot is not evidence that this test ran or timed out.

The native benchmark saves the first failing output, while retaining the binary status list. That first output can help diagnose a failure, but an early process crash can also leave no results and trigger timeout padding. Do not infer an exact failure cause from the padded binary list, or treat its pass fraction as an unbiased partial-credit measure: it depends on test order and early stopping. The official all-tests correctness and pass@k metrics are retained unchanged.

The actual timeout is a parent join budget `(6+1)*number_of_tests+5` seconds for the completion's entire test subprocess. There is no independent six-second alarm on every test in this source. Metadata from the actual 131 examples shows 4,852 private tests, minimum 1 and median/maximum 40. No zero-test tasks were found. The largest native join budget is therefore 285 seconds per completion. An individual slow test can consume that shared budget. A later evaluation may legitimately spend several minutes on one completion; this alone is not a hung supervisor.

Summing all native join budgets over ten repeats gives 346,190 seconds. This is a serial budget sum, not a wall-time forecast: two workers overlap, normal code usually finishes early, and setup/IPC overhead is additional. Preserve this protocol for the current author-native comparison. Any independently instrumented cause analysis would need a separate diagnostic artifact and cannot silently replace these scores.

No scoring or timeout code was changed. The postprocessor now explicitly labels failed-test counts as including upstream padding. The current model generator and its subsequent isolated evaluator remain the sole experiment program.
