# Model artifacts

Runtime artifacts committed to this repository:

- `best_model.onnx`: CPU fallback and reference model.
- `best_model.hef`: compiled Hailo-8L model for Raspberry Pi AI HAT+.
- `model_metadata.json`: ONNX architecture and thresholds.
- `hailo8l_model_metadata.json`: HEF build, VStream, and validation metadata.
- `event_thresholds.json`: temporal event thresholds shared by both backends.

The parsed, optimized, and compiled HAR files are build intermediates. They are
kept outside Git because they are not required at runtime and are too large for
normal repository use. The canonical build intermediates remain in
`F:\macos\HailoWorkspace\shared_with_docker\output` on the build workstation.

The HEF compiled and passed `hailortcli parse-hef`. Physical regression against
the ONNX output on the Hailo-8L device is still required before promoting the
Hailo backend to production.
