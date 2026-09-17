import pytest

from blink_challenge import BlinkChallenge

OPEN = (0.32, 0.32)
CLOSED = (0.14, 0.14)


def started(monkeypatch, target=2):
    monkeypatch.setattr('blink_challenge.secrets.choice', lambda choices: target if target in choices else choices[0])
    challenge = BlinkChallenge(confirmations=2)
    challenge.update('ana', True, OPEN, 0)
    challenge.update('ana', True, OPEN, 0.1)
    assert challenge.target == target
    return challenge


def blink(challenge, now, key='ana'):
    for eyes in (OPEN, OPEN, CLOSED, CLOSED, OPEN, OPEN):
        now += 0.1
        assert challenge.update(key, False, eyes, now) is None
    return now


@pytest.mark.parametrize('target', range(1, 6))
def test_exact_count_and_new_identity_observation_required(monkeypatch, target):
    c = started(monkeypatch, target)
    now = 0.1
    for n in range(target):
        now = blink(c, now)
        assert c.count == n + 1
    assert c.update('ana', False, OPEN, now+0.1) is None
    assert c.update('ana', True, OPEN, now+0.2) == c.token


def test_static_open_or_closed_photo_never_completes(monkeypatch):
    for eyes in (OPEN, CLOSED):
        c = started(monkeypatch)
        for i in range(1, 200):
            assert c.update('ana', True, eyes, 0.1+i*0.1) is None
        assert c.count == 0


def test_single_noisy_frame_or_one_eye_does_not_count(monkeypatch):
    c = started(monkeypatch)
    for i, eyes in enumerate((OPEN, OPEN, CLOSED, OPEN, OPEN, (0.1, 0.3), OPEN, OPEN)):
        c.update('ana', False, eyes, 0.2+i*0.1)
    assert c.count == 0


@pytest.mark.parametrize('failure', ['missing', 'identity', 'invalid', 'gap'])
def test_failure_discards_partial_progress(monkeypatch, failure):
    c = started(monkeypatch)
    now = blink(c, 0.1)
    assert c.count == 1
    old_token = c.token
    key = None if failure == 'missing' else 'bia' if failure == 'identity' else 'ana'
    ears = None if failure == 'invalid' else OPEN
    c.update(key, True, ears, now + (0.7 if failure == 'gap' else 0.1))
    assert c.count == 0 and c.token != old_token


def test_nonfinite_measurement_does_not_pass(monkeypatch):
    c = started(monkeypatch)
    c.update('ana', True, (float('nan'), 0.3), 0.2)
    assert c.token is None


def test_each_new_challenge_differs_from_previous():
    c = BlinkChallenge(confirmations=1)
    previous = None
    for i in range(100):
        c.reset()
        c.update('ana', True, OPEN, float(i))
        assert 1 <= c.target <= 5 and c.target != previous
        previous = c.target


def test_long_closure_resets(monkeypatch):
    c = started(monkeypatch)
    c.update('ana', False, OPEN, 0.2)
    c.update('ana', False, OPEN, 0.3)
    for i in range(4, 22):
        c.update('ana', False, CLOSED, i*0.1)
    assert c.count == 0 and c.target is None


def test_completed_challenge_expires_and_extra_blink_invalidates(monkeypatch):
    c = started(monkeypatch, 1)
    now = blink(c, 0.1)
    for i in range(1, 8):
        c.update('ana', False, OPEN, now+i*0.5)
    assert c.token is None
    c = started(monkeypatch, 1)
    now = blink(c, 0.1)
    assert c.update('ana', True, CLOSED, now+0.1) is None
    assert c.token is None


def test_challenge_deadline_resets_even_with_continuous_frames(monkeypatch):
    c = started(monkeypatch, 1)
    for i in range(1, 53):
        assert c.update('ana', False, OPEN, 0.1+i*0.5) is None
    assert c.target is None
