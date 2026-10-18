# Resume-condition correction

Actual post-adoption observation: pressure=2, swap_bytes=4370989056,
owned_rss=0, no stop reason. The supervisor nevertheless waited because its resume
hysteresis required pressure=1 once residual swap exceeded4 GiB. This contradicted
the existing allowance for pressure2 lightweight control.

can_resume now permits low-load recovery at either allowed pressure1 or2, while
retaining the existing swap/disk/process resource checks and60-second stable window.
Only the project supervisor changed; this is separate from plugin .11.
19 behavior tests passed on hn01. The Mac LaunchAgent was then restarted at the
idle boundary. Program revision403 remains active at B02, preserving all work.
Actual worker startup is recorded separately; a resume request is not GPU activity.
