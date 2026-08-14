class WoyofalMeter:
    def __init__(self, initial_balance):
        self.balance = initial_balance

    def consume(self, energy_kwh):
        self.balance -= energy_kwh

        if self.balance < 0:
            self.balance = 0.0

        return self.balance
    