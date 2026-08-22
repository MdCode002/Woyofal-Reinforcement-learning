class Thermal1R1C:
    def __init__(
        self,
        T_int=28.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0,
        cop=3.0
    ):
        self.T_int = T_int
        self.R = R
        self.C = C
        self.cooling_power_kw = cooling_power_kw
        self.cop = cop

    def step(self, T_ext, dt_hours, ac_on=False):
        """
        Met à jour la température intérieure pendant dt_hours.
        """

        # Échange thermique avec l'extérieur
        heat_flow = (T_ext - self.T_int) / self.R

        # Refroidissement fourni par la climatisation
        cooling = self.cooling_power_kw if ac_on else 0.0

        # Évolution de la température
        dT = (heat_flow - cooling) / self.C * dt_hours

        self.T_int += dT

        return self.T_int

    def electric_consumption_kwh(self, dt_hours, ac_on=False):
        """
        Calcule l'énergie électrique consommée par la climatisation.
        """

        if not ac_on:
            return 0.0

        electrical_power_kw = self.cooling_power_kw / self.cop

        return electrical_power_kw * dt_hours