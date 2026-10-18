# Deployment layout

These files archive the deployed local supervisor. Install host_guard.py as `<run-root>/ops/host_guard.py` and tests as `<run-root>/ops/tests/test_guard.py`; ROOT is derived from that location. The existing run root must contain venv/, runtime/controller.sqlite, project/ and logs/. This is a project-specific macOS supervisor, not a standalone generic installer. The private LaunchAgent uses the existing private CODEX_HOME and invokes the venv Python with ops/host_guard.py. Credentials and the private launch configuration are deliberately not exported.

Run focused tests with `PYTHONPATH=ops venv/bin/python -m unittest discover -s ops/tests` from the deployed run root. See ../reports/host-protection-20261018.md for thresholds and adoption evidence.
