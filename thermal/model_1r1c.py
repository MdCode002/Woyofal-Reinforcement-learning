class Thermal1R1C:
    def __init__(self, T_int, R, C):
        self.T_int = T_int
        self.R = R
        self.C = C

    def step(self, T_ext, dt):
        dT = (dt / (self.R * self.C)) * (T_ext - self.T_int)

        self.T_int += dT

        return self.T_int