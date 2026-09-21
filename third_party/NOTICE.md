# Silent-Face-Anti-Spoofing / MiniFASNet

Copyright 2020 Minivision. Licensed under Apache License 2.0.
License copy: `Silent-Face-Anti-Spoofing-LICENSE.txt`.

Source: https://github.com/minivision-ai/Silent-Face-Anti-Spoofing
Revision: b6d5f04ad78778917853b25c778acef6d5626d15

This distribution includes ONNX conversions of the original pretrained weights:

- `2.7_80x80_MiniFASNetV2.pth`
- `4_0_0_80x80_MiniFASNetV1SE.pth`

Converted by `tools/export_antispoof.py`, with PyTorch 2.6.0 CPU, ONNX 1.17.0,
fixed input 1×3×80×80, opset 11, evaluation mode and constant folding.
The weights were not retrained. Original and converted SHA-256 hashes and
conversion checks are recorded in `modelos/antispoof/manifest.json`.

`anti_spoof.py` adapts the crop algorithm in `src/generate_patches.py` and uses the
same BGR, float32, 0..255 preprocessing as `src/data_io/functional.py`. Modifications:
input checks, OpenCV inference, separate approval by both models, temporal voting,
integrity checks and error handling. No vendor dataset or sample face photos are
included in the application package.

These models produce model scores, not a calibrated guarantee of real presence.
No affiliation with or endorsement by Minivision is implied.
