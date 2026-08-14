from woyofal.meter import WoyofalMeter


def test_balance_decreases_after_consumption():
    meter = WoyofalMeter(initial_balance=10.0)

    new_balance = meter.consume(2.5)

    assert new_balance == 7.5


def test_balance_remains_unchanged_when_consumption_is_zero():
    meter = WoyofalMeter(initial_balance=10.0)

    new_balance = meter.consume(0.0)

    assert new_balance == 10.0


def test_balance_cannot_be_negative():
    meter = WoyofalMeter(initial_balance=5.0)

    new_balance = meter.consume(7.0)

    assert new_balance == 0.0