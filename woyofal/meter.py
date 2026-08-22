class WoyofalMeter:
    def __init__(self, initial_balance):
        if initial_balance < 0:
            raise ValueError("Initial balance must be non-negative.")

        self.balance = float(initial_balance)
        self.is_cutoff = False

    def consume(self, energy_kwh):
        if energy_kwh < 0:
            raise ValueError("Energy consumption must be non-negative.")

        self.balance -= float(energy_kwh)

        if self.balance <= 0:
            self.balance = 0.0
            self.is_cutoff = True

        return self.balance