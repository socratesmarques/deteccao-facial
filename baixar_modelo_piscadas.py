"""Download explicit, pinned upstream LBF model with integrity validation."""
from __future__ import annotations

import hashlib
import os
import tempfile
from urllib.request import urlopen

from eye_landmarks import LBF_MODEL

MODEL_URL = ('https://raw.githubusercontent.com/kurnianggoro/GSOC2017/'
             '7523caa8539ef58c5f4132bf99b13c617fbb58df/data/lbfmodel.yaml')
MODEL_SHA256 = '70dd8b1657c42d1595d6bd13d97d932877b3bed54a95d3c4733a0f740d1fd66b'


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    if LBF_MODEL.is_file() and digest(LBF_MODEL) == MODEL_SHA256:
        print('Modelo de piscadas já instalado e verificado.')
        return
    LBF_MODEL.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=LBF_MODEL.parent, suffix='.download')
    try:
        hasher = hashlib.sha256()
        with os.fdopen(fd, 'wb') as target, urlopen(MODEL_URL, timeout=60) as source:
            total = 0
            while chunk := source.read(1024*1024):
                total += len(chunk)
                if total > 65 * 1024 * 1024:
                    raise RuntimeError('Modelo excedeu o tamanho esperado.')
                hasher.update(chunk)
                target.write(chunk)
        if hasher.hexdigest() != MODEL_SHA256:
            raise RuntimeError('SHA-256 diferente do esperado. Modelo não instalado.')
        os.replace(temporary, LBF_MODEL)
        print('Modelo de piscadas instalado e verificado.')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == '__main__':
    main()
