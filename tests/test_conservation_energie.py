from test_env import _build_demo_env
import pytest


def test_balance_drop_equals_sum_of_consumptions_over_episode():
    env = _build_demo_env(n_steps=4)
    env.reset()

    initial_balance = env.meter.balance
    total_consumed = 0.0

    terminated = truncated = False
    while not (terminated or truncated):
        _, _, terminated, truncated, info = env.step(1)
        total_consumed += info["energy_consumption"]

    final_balance = env.meter.balance

    assert final_balance == pytest.approx(initial_balance - total_consumed, rel=1e-6)


def test_cumulative_consumption_matches_manual_sum():
    env = _build_demo_env(n_steps=4)
    env.reset()

    manual_sum = 0.0
    terminated = truncated = False
    while not (terminated or truncated):
        _, _, terminated, truncated, info = env.step(0)
        manual_sum += info["energy_consumption"]
        assert info["cumulative_consumption"] == pytest.approx(manual_sum, rel=1e-6)


def test_balance_never_negative():
    # Un credit tres faible doit provoquer une coupure avant que le solde
    # ne devienne negatif : le compteur ne doit jamais laisser passer une
    # consommation qui ferait passer le solde sous zero de maniere durable.
    env = _build_demo_env(credit_initial_kwh=0.05, n_steps=4)
    env.reset()

    terminated = truncated = False
    while not (terminated or truncated):
        _, _, terminated, truncated, info = env.step(1)
        assert info["balance"] >= 0.0