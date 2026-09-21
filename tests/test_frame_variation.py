import numpy as np
from frame_variation import FrameVariation


FACE = np.array([10,10,80,80]+[0]*10+[.99])


def frame(offset=0):
    result = np.full((100,100,3), 80, dtype=np.uint8)
    result[30:55, 25+offset:45+offset] = 200
    return result


def observe(window, frames):
    for index, image in enumerate(frames):
        window.observe(image, FACE, index+1, index*.35)
    return window.snapshot()


def test_five_identical_samples_are_not_different():
    state = observe(FrameVariation(), [frame()]*5)
    assert state['count'] == 5
    assert not state['different']


def test_one_changed_image_among_five_is_enough():
    state = observe(FrameVariation(), [frame(),frame(),frame(20),frame(),frame()])
    assert state['count'] == 5
    assert state['different']


def test_four_changed_samples_still_need_fifth():
    state = observe(FrameVariation(), [frame(),frame(20)]*2)
    assert state['different']
    assert state['count'] == 4


def test_noise_and_uniform_brightness_are_ignored():
    rng = np.random.default_rng(123)
    images = [np.clip(frame().astype(int)+rng.integers(-2,3,(100,100,3)),0,255).astype(np.uint8) for _ in range(5)]
    assert not observe(FrameVariation(), images)['different']
    assert not observe(FrameVariation(), [frame(),frame()+15,frame(),frame()+15,frame()])['different']


def test_background_change_does_not_count():
    other = frame()
    other[:12] = 255
    other[92:] = 255
    assert not observe(FrameVariation(), [frame(),other,frame(),other,frame()])['different']


def test_old_variation_expires_from_sliding_window():
    window = FrameVariation()
    assert observe(window, [frame(),frame(20),frame(),frame(),frame()])['different']
    for index in range(5,10):
        window.observe(frame(), FACE, index+1, index*.35)
    assert not window.snapshot()['different']
    assert window.snapshot()['first_observation'] == 6


def test_too_fast_frames_and_capture_gap():
    window = FrameVariation()
    for index in range(5):
        window.observe(frame(index*2), FACE, index+1, index*.01)
    assert window.snapshot()['count'] == 1
    window.observe(frame(), FACE, 6, 3)
    assert window.snapshot()['count'] == 1


def test_invalid_face_resets_samples():
    window = FrameVariation()
    observe(window, [frame()]*4)
    window.observe(frame(), np.array([0,0,1,1]), 5, 2)
    assert window.snapshot()['count'] == 0
