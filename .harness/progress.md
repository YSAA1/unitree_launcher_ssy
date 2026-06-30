# Progress

## 2026-06-29

- Collected repository evidence from `study_plan.md`, `README.md`, `CLAUDE.md`, `pyproject.toml`, `src/`, `tests/`, and git history.
- Confirmed the repository initially had no `AGENTS.md`, no `.harness/`, and no `docs/plans/`.
- Ran `uv run pytest tests/ -q`; it initially failed because the environment was not fully synced.
- Ran `uv sync --extra dev --extra sim` to install required dev and simulation dependencies.
- Ran `uv run pytest tests/ -x -q`; result: PASS, `505 passed in 22.18s`.
- Installed project-local harness files and the learning executable plan after user approval.
- Ran `uv run pytest tests/ -x -q` after writing harness files; result: PASS, `505 passed in 21.76s`.
- Started teaching workflow. Created `MISSION.md`, `RESOURCES.md`, `assets/teaching.css`, `reference/0001-mode-map.html`, and `lessons/0001-entry-modes-config.html`.
- Ran `uv run pytest tests/test_main.py tests/test_config.py -x -q`; result: PASS, `85 passed in 8.68s`.
- User observed GUI simulation standing still and learned that GUI requires command/start input.
- Created `NOTES.md`, `reference/0002-command-cheatsheet.html`, and `lessons/0002-how-to-use-and-read-main.html`.
- Ran `uv run pytest tests/test_main.py tests/test_runtime.py -q`; result: PASS, `80 passed in 8.98s`.
- User asked for a deeper explanation of CLI argument flow, especially `args.preset`, parser/subparser, and shell-to-argparse data movement.
- Created `reference/0003-argparse-flow.html` and `lessons/0003-argparse-and-preset-data-flow.html`.
- User stated they now broadly understand `main.py` usage and asked to continue the course.
- Created learning record `learning-records/0001-main-cli-argparse-baseline.md`.
- Created `reference/0004-runtime-data-contract.html` and `lessons/0004-runtime-data-contract.html`.
- Ran `uv run pytest tests/test_runtime.py tests/test_sim_robot.py tests/test_real_robot.py tests/test_factory.py -q`; result: PASS, `83 passed in 2.65s`.
- User asked how real robot control and connection work.
- Read `real_robot.py`, `configs/real.yaml`, deployment/build scripts, `wireless.py`, README real deployment notes, and DDS test script.
- Created `reference/0005-real-robot-control-chain.html` and `lessons/0005-real-robot-control-connection.html`.
- Ran `uv run pytest tests/test_real_robot.py tests/test_main.py tests/test_gamepad.py -q`; result: PASS, `71 passed in 10.65s`.
- Created `docs/tutorials/trained-policy-to-g1-deployment.md` and generated/copied `docs/assets/trained-policy-to-g1-flow.png` to explain the full trained-policy-to-G1 deployment chain.
- Created `CONTEXT.md` and `docs/understanding/robot-sdk-porting-workflow.md` to explain the G1 runtime data flow and what must change when porting to another robot SDK.
- Created `docs/understanding/README.md` and `docs/understanding/lesson-01-cli-to-runtime-assembly.md` as the first data-flow lesson from CLI input to Runtime assembly.
- Regenerated `docs/understanding/lesson-01-cli-to-runtime-assembly.md` with a source-evidenced CLI-to-Runtime data-flow walkthrough, Mermaid graph, glossary links, self-check questions, and copied `docs/understanding/assets/lesson-01-cli-runtime-intuition.png`.
- Created `docs/understanding/lesson-02-realrobot-connect-to-sdk-dds.md` with the `robot.connect()` -> `RealRobot.connect()` -> `unitree_cpp.UnitreeController` -> Unitree SDK2/DDS chain, Mermaid graph, evidence map, self-check questions, and copied `docs/understanding/assets/lesson-02-realrobot-connect-intuition.png`.
- Created `docs/understanding/lesson-03-runtime-step-control-tick.md` with the `Runtime.step()` control tick data flow, branch map, evidence map, self-check questions, and copied `docs/understanding/assets/lesson-03-runtime-step-intuition.png`.

## 2026-06-30

- Ran a `grill-with-docs` session for T4 low-level deployment. Decisions: low-level policy control, 29-DoF-first assumption, Python Zvalley SDK bridge, `t4_29dof` variant, shared `real` entrypoint, real-robot NaN base pose convention, staged safety gates, first slice as read-only SDK probe.
- Created `docs/adr/0001-t4-low-level-policy-control.md` and `docs/adr/0002-add-t4-as-robot-variant.md`.
- Created `docs/plans/2026-06-30--t4-porting-grill.md`, `docs/prd/t4-low-level-deployment.md`, and `docs/issues/t4-low-level-deployment-issues.md`.
- Started TDD for Issue 1. Added `tests/test_t4_probe_state.py`, confirmed RED on missing `scripts/t4_probe_state.py`, then implemented the read-only probe.
- Ran `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_probe_state.py -q`; result: PASS, `2 passed in 0.12s`.
- Ran `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_probe_state.py tests/test_main.py -q`; result: PASS, `47 passed in 9.15s`.
- Ran `python scripts/t4_probe_state.py --help`; result: PASS.
- Attempted issue tracker verification. `git remote -v` points to `https://github.com/YSAA1/unitree_launcher_ssy.git`, but `gh auth status` reports the active account token is invalid and `gh repo view` returns Forbidden. PRD/issues remain as local source files for later publication.
- Continued TDD with Issue 2. Added `T4_29DOF_JOINTS`, `Q_HOME_T4_29DOF`, config validation for `t4_29dof`, and factory support for loading a T4 BeyondMimic policy through `JointMapper`.
- Moved root-level T4 assets into `assets/t4/policies/`, `assets/t4/motions/`, and `assets/robots/t4/`; kept `zv_robot_sdk/` as the local Zvalley SDK checkout.
- Read local `zv_robot_sdk/` with a subagent. Key result: documented state topic is `rt/all_joint_state`, command topic is `rt/all_joint_cmd`, navigation/IMU-like topic is `rt/nav_all`, and SDK examples still show only 23 low-level command joints.
- Updated `scripts/t4_probe_state.py` to support `--sdk-root zv_robot_sdk` and read-only `rt/nav_all` probing.
- Ran `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_probe_state.py tests/test_config.py tests/test_factory.py tests/test_main.py -q`; result: PASS, `113 passed in 8.51s`.
- Ran `python scripts/t4_probe_state.py --help`; result: PASS.
