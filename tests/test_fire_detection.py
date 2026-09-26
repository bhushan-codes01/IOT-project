from backend.fire_detection import FireLevel, assess_fire_risk


def test_temperature_below_warning_is_normal():
    result = assess_fire_risk(30, 50)
    assert result.level is FireLevel.NORMAL
    assert result.fire_status is False


def test_temperature_near_threshold_is_warning_not_emergency():
    result = assess_fire_risk(40, 50)
    assert result.level is FireLevel.WARNING
    assert result.fire_status is False


def test_threshold_is_emergency():
    result = assess_fire_risk(50, 50)
    assert result.level is FireLevel.EMERGENCY
    assert result.fire_status is True
