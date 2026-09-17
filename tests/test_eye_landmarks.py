import numpy as np
import pytest
from eye_landmarks import EyeLandmarks, eye_aspect_ratio


def test_eye_ratio_open_closed_and_degenerate():
    points = np.array([[0,0], [5,3], [15,3], [20,0], [15,-3], [5,-3]], dtype=float)
    assert eye_aspect_ratio(points) == pytest.approx(0.3)
    points[:, 1] *= 0.3
    assert eye_aspect_ratio(points) == pytest.approx(0.09)
    assert eye_aspect_ratio(np.zeros((6, 2))) is None
    assert eye_aspect_ratio(np.full((6, 2), np.nan)) is None


def test_missing_model_blocks_instead_of_fallback(tmp_path):
    with pytest.raises(RuntimeError, match='baixar_modelo_piscadas'):
        EyeLandmarks(tmp_path/'missing.yaml')


def test_small_or_partial_face_is_rejected_without_inference():
    eyes = EyeLandmarks.__new__(EyeLandmarks)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    assert eyes.measure(frame, [0, 0, 50, 50]) is None
    assert eyes.measure(frame, [-10, 0, 100, 100]) is None
