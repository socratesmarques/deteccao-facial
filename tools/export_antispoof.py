"""Conversão reproduzível dos pesos upstream. Não usado no Orange Pi em execução.
Dependências de desenvolvimento: torch 2.6.0 CPU, onnx 1.17.0 e OpenCV.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np
import onnx
import torch

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT = 'b6d5f04ad78778917853b25c778acef6d5626d15'
MODELS = [('2.7_80x80_MiniFASNetV2.pth', 'MiniFASNetV2', 2.7),
          ('4_0_0_80x80_MiniFASNetV1SE.pth', 'MiniFASNetV1SE', 4.0)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True, help='Checkout do repositório oficial Silent-Face-Anti-Spoofing')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != UPSTREAM_COMMIT:
        raise RuntimeError('O checkout não corresponde ao commit revisado.')
    spec = importlib.util.spec_from_file_location('minifasnet', args.source/'src/model_lib/MiniFASNet.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    torch.set_num_threads(1); cv2.setNumThreads(1)
    destination = ROOT/'modelos/antispoof'
    destination.mkdir(parents=True, exist_ok=True)
    manifest = dict(source='https://github.com/minivision-ai/Silent-Face-Anti-Spoofing',
                    revision=revision, license='Apache-2.0', input='BGR float32 NCHW 1x3x80x80, range 0..255',
                    real_class=1, opset=11, torch=torch.__version__, opencv=cv2.__version__, models=[])
    rng = np.random.default_rng(12)
    inputs = [np.zeros((1,3,80,80),np.float32), np.full((1,3,80,80),127,np.float32),
              rng.uniform(0,255,(1,3,80,80)).astype(np.float32)]
    for filename, architecture, scale in MODELS:
        weights = args.source/'resources/anti_spoof_models'/filename
        model = getattr(module, architecture)(conv6_kernel=(5,5), num_classes=3)
        state = torch.load(weights, map_location='cpu', weights_only=True)
        model.load_state_dict({key.removeprefix('module.'):value for key,value in state.items()})
        model.eval()
        output = destination/(weights.stem+'.onnx')
        torch.onnx.export(model, torch.from_numpy(inputs[0]), str(output), input_names=['input'],
                          output_names=['logits'], opset_version=11, do_constant_folding=True, dynamo=False)
        onnx.checker.check_model(onnx.load(str(output)))
        net = cv2.dnn.readNetFromONNX(str(output))
        max_error = 0
        for sample in inputs:
            with torch.no_grad():
                expected = model(torch.from_numpy(sample)).numpy()
            net.setInput(sample)
            actual = net.forward()
            np.testing.assert_allclose(actual,expected,atol=2e-4,rtol=2e-4)
            max_error = max(max_error,float(np.max(np.abs(actual-expected))))
        entry = dict(file=output.name, sha256=sha(output), scale=scale,
                     original_file=filename, original_sha256=sha(weights), max_logit_error=max_error)
        manifest['models'].append(entry)
        print(json.dumps(entry))
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    main()
