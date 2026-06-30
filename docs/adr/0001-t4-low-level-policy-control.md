# Use Low-Level Policy Control for T4

We will integrate T4 through the low-level SDK path, not by calling the vendor high-level built-in action interface. The given T4 asset is a 29-DoF BeyondMimic ONNX policy with matching tracking motion data, so the useful deployment path is to reuse this project's Runtime and map `RobotCommand` to Zvalley SDK joint commands.

**Considered Options**

- High-level SDK action/model switching: simpler, but it would not run the provided ONNX policy.
- Low-level position-PD policy control: higher integration and safety burden, but it matches the provided policy artifact and this repository's architecture.

**Consequences**

The port must explicitly verify T4 joint count, joint order, command topic semantics, state topic semantics, safety fallback, and control ownership before any real-robot run.
