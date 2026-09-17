import pytest
from blink_challenge import BlinkChallenge

OPEN = (0.32, 0.32)
CLOSED = (0.14, 0.14)


def observe(c, eyes=OPEN, fresh=False, dt=0.1, key='ana'):
    now = (c.last_sample if c.last_sample is not None else 0) + dt
    return c.update(key, fresh, eyes, now)


def calibrated(monkeypatch, target=2, opened=OPEN, closed=CLOSED, dt=0.1):
    monkeypatch.setattr('blink_challenge.secrets.choice', lambda choices: target if target in choices else choices[0])
    c = BlinkChallenge(confirmations=2)
    observe(c, opened, True, dt)
    observe(c, opened, True, dt)
    for _ in range(100):
        if c.phase != 'calibrate_open':
            break
        observe(c, opened, True, dt)
    assert c.phase == 'calibrate_closed'
    for _ in range(100):
        if c.phase != 'calibrate_closed':
            break
        observe(c, closed, False, dt)
    assert c.phase == 'reopen'
    observe(c, opened, True, dt)
    observe(c, opened, True, dt)
    assert c.phase == 'challenge' and c.target == target
    assert c.count == 0  # guided closure is not a challenge blink
    return c


def blink(c, opened=OPEN, closed=CLOSED, dt=0.1, closed_samples=2):
    for eyes in [opened, opened] + [closed]*closed_samples + [opened, opened]:
        assert observe(c, eyes, False, dt) is None


@pytest.mark.parametrize('target', range(1, 6))
def test_exact_count_and_post_blink_fresh_identity(monkeypatch, target):
    c = calibrated(monkeypatch, target)
    for n in range(target):
        blink(c)
        assert c.count == n + 1
    assert observe(c, OPEN, False) is None
    assert observe(c, OPEN, True) == c.token


@pytest.mark.parametrize('opened,closed', [((.32,.32),(.14,.14)), ((.38,.34),(.26,.24)), ((.19,.18),(.12,.11))])
def test_calibrates_eyes_that_never_cross_old_fixed_thresholds(monkeypatch, opened, closed):
    c = calibrated(monkeypatch, 1, opened, closed)
    blink(c, opened, closed)
    assert c.count == 1
    assert observe(c, opened, True) == c.token


def test_single_closed_sample_at_five_fps_counts(monkeypatch):
    c = calibrated(monkeypatch, 1, dt=0.2)
    blink(c, dt=0.2, closed_samples=1)
    assert c.count == 1
    assert observe(c, OPEN, True, .2) == c.token


def test_high_fps_single_frame_noise_and_wink_do_not_count(monkeypatch):
    c = calibrated(monkeypatch, dt=0.05)
    blink(c, dt=0.05, closed_samples=1)
    assert c.count == 0
    for eyes in [(0.1, 0.3)]*3 + [OPEN]*3:
        observe(c, eyes, dt=.05)
    assert c.count == 0


@pytest.mark.parametrize('eyes', [OPEN, CLOSED])
def test_constant_input_cannot_calibrate_or_get_permit(eyes):
    c = BlinkChallenge(confirmations=1)
    for i in range(300):
        assert c.update('ana', True, eyes, i*.1) is None
        assert c.target is None


def test_insufficient_open_closed_contrast_cannot_calibrate():
    c = BlinkChallenge(confirmations=1)
    for i in range(20):
        c.update('ana', True, OPEN, i*.1)
    for i in range(20, 100):
        assert c.update('ana', False, (.30, .30), i*.1) is None
    assert c.phase == 'calibrate_closed' and c.target is None


@pytest.mark.parametrize('failure', ['missing', 'identity', 'invalid', 'gap'])
def test_failure_discards_progress(monkeypatch, failure):
    c = calibrated(monkeypatch)
    blink(c)
    assert c.count == 1
    now = c.last_sample
    key = None if failure == 'missing' else 'bia' if failure == 'identity' else 'ana'
    eyes = None if failure == 'invalid' else OPEN
    assert c.update(key, True, eyes, now + (.7 if failure == 'gap' else .1)) is None
    assert c.count == 0 and c.token is None
    assert c.reason


def test_nonfinite_measurement_resets(monkeypatch):
    c = calibrated(monkeypatch)
    observe(c, (float('nan'), .3))
    assert c.token is None


def test_new_challenge_excludes_previous_count(monkeypatch):
    c = calibrated(monkeypatch, 1)
    previous = c.target
    c.reset()
    # Preserve the previous draw even when resetting calibration.
    assert c.previous_target == previous
    for _ in range(2):
        observe(c, OPEN, True)
    while c.phase == 'calibrate_open':
        observe(c, OPEN)
    while c.phase == 'calibrate_closed':
        observe(c, CLOSED)
    observe(c, OPEN)
    observe(c, OPEN)
    assert 1 <= c.target <= 5 and c.target != previous


def test_long_closure_and_completion_expiry(monkeypatch):
    c = calibrated(monkeypatch, 1)
    for _ in range(18):
        observe(c, CLOSED)
    assert c.token is None
    c = calibrated(monkeypatch, 1)
    blink(c)
    for _ in range(7):
        observe(c, OPEN, dt=.5)
    assert c.token is None


def test_deadlines_and_extra_blink(monkeypatch):
    c = calibrated(monkeypatch, 1)
    for _ in range(52):
        assert observe(c, OPEN, dt=.5) is None
    assert c.token is None
    c = calibrated(monkeypatch, 1)
    blink(c)
    assert observe(c, CLOSED, True) is None
    assert c.token is None


def test_defers_identity_inference_while_closed_and_resumes_on_reopen(monkeypatch):
    c = calibrated(monkeypatch)
    assert not c.allow_recognition(CLOSED)
    assert not c.allow_recognition(None)
    assert c.allow_recognition(OPEN)


def test_diagnostics_show_measurement_limits_and_reset_reason(monkeypatch):
    c = calibrated(monkeypatch)
    assert '0.320/0.320' in c.diagnostic(OPEN)
    assert 'fechado' in c.diagnostic(OPEN)
    observe(c, None)
    assert 'inválida' in c.diagnostic(None)


def test_calibration_also_completes_at_sixty_fps(monkeypatch):
    c = calibrated(monkeypatch, dt=1/60)
    assert c.phase == 'challenge'
