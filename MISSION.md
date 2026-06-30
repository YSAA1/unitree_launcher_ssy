# Mission: Unitree Launcher Project Fluency

## Why

Learn this Unitree G1 deployment stack well enough to run it, explain its
control path, and make safe, verified optimizations. The practical goal is to
connect trained ONNX policies, especially IsaacLab or BeyondMimic policies, to
simulation and eventually real G1 deployment without breaking safety-critical
behavior.

## Success looks like

- Explain how `sim`, `eval`, `real`, `mirror`, and `replay` modes are wired.
- Trace one control tick from CLI setup through `Runtime.step()` to robot command output.
- Identify high-risk surfaces before editing: real robot backend, safety, gains, joint order, DDS, and policy metadata.
- Choose and implement a small optimization with relevant tests passing.

## Constraints

- Move quickly, but keep real-robot changes out of scope until the software path is understood.
- Prefer source-backed lessons using this repository's code, tests, and docs.
- Use retrieval practice: short questions after each lesson, not just passive reading.

## Out of scope

- Training new policies.
- Real robot execution during the first learning slice.
- Changing ONNX policy files, joint mapping, E-stop behavior, or safety limits without a separate plan.
