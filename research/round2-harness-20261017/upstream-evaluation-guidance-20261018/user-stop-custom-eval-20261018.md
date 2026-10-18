# Explicit user stop and evaluator change

The user says to stop the current work and use official evaluation code for testing. Stop the current custom-evaluator runs and automatic continuation; preserve predictions, partial outputs and logs. Do not launch another custom scorer. Before resuming evaluation, identify the upstream author-maintained implementation, exact task/split/prompt/extraction settings and distinguish original MBPP from EvalPlus/MBPP+. Do not call a project-written adapter official. Harness supervision is retained, paused for this change.
