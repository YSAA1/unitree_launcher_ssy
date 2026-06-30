# Current State

updated: 2026-06-30

## Objective

Create a PRD and issue breakdown for T4 low-level deployment, then continue
TDD slices toward the staged T4 port.

## Active Slice

Issue 2 from the T4 issue breakdown:

```text
t4_29dof is a first-class robot variant with a 29-joint list, T4 home pose,
and BeyondMimic policy loading through the existing JointMapper/factory path.
```

## Current Phase

TDD Issue 1 and Issue 2 complete locally. Cleanup in progress.

## Active Artifact

`docs/prd/t4-low-level-deployment.md`

## Verification Path

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_probe_state.py tests/test_config.py tests/test_factory.py tests/test_main.py -q
python scripts/t4_probe_state.py --help
```

Latest evidence:

- `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_t4_probe_state.py tests/test_config.py tests/test_factory.py tests/test_main.py -q` passed with 113 tests.
- `python scripts/t4_probe_state.py --help` passed.
- GitHub issue publishing is blocked by invalid `gh` auth token: `gh auth status` reports the active account token is invalid and `gh repo view` returns Forbidden.
- T4 root assets were moved under `assets/t4/` and `assets/robots/t4/`; no root-level T4 ONNX or `motion.npz` files remain.
- Local SDK review found `rt/all_joint_state`, `rt/all_joint_cmd`, and `rt/nav_all`; `AllJointState_` does not document IMU fields, so navigation/IMU should be probed through `rt/nav_all`.

## Risks

- The read-only probe still needs to be run on the T4 official/onboard control environment.
- The real SDK may expose only 23 DoF; if so, current 29-DoF policy is incompatible with that control surface.
- GitHub issues have not been published because local `gh` authentication is invalid.

## Next Actions

1. Repair `gh` authentication and publish `docs/prd/t4-low-level-deployment.md` plus `docs/issues/t4-low-level-deployment-issues.md` to GitHub Issues.
2. Run `scripts/t4_probe_state.py` on the T4 control environment and capture `rt/all_joint_state` plus `rt/nav_all` output.
3. Use the probe output to decide whether Issue 3 can safely introduce a T4 backend or whether the 29-DoF policy must be retrained/exported for a different SDK control surface.
