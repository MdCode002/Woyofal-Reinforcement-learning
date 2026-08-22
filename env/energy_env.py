from __future__ import annotations
from datetime import timedelta
import gymnasium as gym
import numpy as np
from gymnasium import spaces
from thermal.model_1r1c import Thermal1R1C
from woyofal.meter import WoyofalMeter
from common.models import Scenario, ProfilChargePas, Observation, Action, ReportCharge
from common.units import PAS_DECISION_MINUTES, MINUTES_PAR_HEURE, convertir_en_kwh

# COP par defaut de la climatisation.
# Appareil ou au Scenario par M1/M2 (pour l'instant Appareil n'a pas de champ COP).
AC_COP_DEFAUT = 3.0

# Valeurs de repli si le scenario ne contient pas d'appareil nomme
# "climatisation" / "ventilateur" (ne devrait pas arriver avec un vrai scenario).
FAN_POWER_W_DEFAUT = 60.0
AC_COOLING_POWER_KW_DEFAUT = 3.0

# Noms d'appareils geres directement par l'environnement (via les actions RL) et
# non par le profil RAMP, pour eviter de les compter deux fois.
NOMS_APPAREILS_CONTROLES_PAR_ENV = {"climatisation", "ventilateur"}


class EnergyEnv(gym.Env):
    def __init__(
        self,
        scenario: Scenario,
        load_profile: list[ProfilChargePas],
        weather_profile: list[dict],
    ):
        super().__init__()

        if scenario.pas_minutes != PAS_DECISION_MINUTES:
            raise ValueError(
                f"Le scenario doit utiliser le pas commun de {PAS_DECISION_MINUTES} minutes"
            )

        self.scenario = scenario
        self.load_profile = load_profile
        self.weather_profile = weather_profile

        self.dt_hours = PAS_DECISION_MINUTES / MINUTES_PAR_HEURE

        # Durée totale de l'épisode déduite de date_debut / date_cible (contrat M1)
        self.target_hours = (
            scenario.date_cible - scenario.date_debut
        ).total_seconds() / 3600.0

        # Appareil flexible ET décalable, s'il existe (pour l'action "reporter")
        self.flexible_appareil = next(
            (a for a in scenario.appareils if a.flexible and a.decalage_autorise),
            None,
        )

        # Puissances electriques reelles de la clim et du ventilo
        self.ac_appareil = next(
            (a for a in scenario.appareils if a.nom == "climatisation"), None
        )
        self.fan_appareil = next(
            (a for a in scenario.appareils if a.nom == "ventilateur"), None
        )

        if self.ac_appareil is not None:
            electrical_ac_kw = self.ac_appareil.puissance_w / 1000.0
            self.cooling_power_kw = electrical_ac_kw * AC_COP_DEFAUT
        else:
            self.cooling_power_kw = AC_COOLING_POWER_KW_DEFAUT

        self.fan_power_w = (
            self.fan_appareil.puissance_w
            if self.fan_appareil is not None
            else FAN_POWER_W_DEFAUT
        )

        # Actions:
        # 0 = clim OFF
        # 1 = clim ON
        # 2 = ventilateur OFF
        # 3 = ventilateur ON
        # 4 = reporter la charge flexible décalable (si elle existe dans le scénario)
        self.action_space = spaces.Discrete(5)

        # Vecteur Box aligné dans l'ordre sur common.model.Observation :
        # credit_restant, heure, jour_semaine, temps_avant_cible, T_int, T_ext,
        # humidite, occupation, conso_cumulee, rythme_kwh_jour, ac_on, fan_on
        self.observation_space = spaces.Box(
            low=np.array([
                0.0,    # credit_restant_kwh
                0.0,    # heure (0-24, cyclique)
                0.0,    # jour_semaine (0-6)
                0.0,    # temps_avant_date_cible (heures)
                -20.0,  # temperature_interieure_c
                -20.0,  # temperature_exterieure_c
                0.0,    # humidite_pourcent
                0.0,    # occupation
                0.0,    # consommation_cumulee_kwh
                0.0,    # rythme_actuel_kwh_par_jour
                0.0,    # etat clim
                0.0,    # etat ventilateur
            ], dtype=np.float32),
            high=np.array([
                1000.0,
                24.0,
                6.0,
                float(max(self.target_hours, 1.0)),
                60.0,
                60.0,
                100.0,
                1.0,
                1000.0,
                200.0,
                1.0,
                1.0,
            ], dtype=np.float32),
            dtype=np.float32,
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.step_index = 0
        self.hour = 0.0
        self.current_datetime = self.scenario.date_debut

        self.meter = WoyofalMeter(initial_balance=self.scenario.credit_initial_kwh)

        T_int_initial = (
            self.scenario.temperature_interieure_initiale_c
            if self.scenario.temperature_interieure_initiale_c is not None
            else self.scenario.temperature_exterieure_initiale_c
        )
        self.thermal = Thermal1R1C(
            T_int=T_int_initial,
            R=2.0,
            C=10.0,
            cooling_power_kw=self.cooling_power_kw,
            cop=AC_COP_DEFAUT,
        )

        self.ac_on = False
        self.fan_on = False

        # Énergie flexible reportée d'un pas sur l'autre (report d'un seul pas dans ce MVP)
        self.deferred_flexible_kwh = 0.0

        self.cumulative_consumption = 0.0
        self.current_consumption = 0.0
        self.historique_consommation_kwh: list[float] = []

        info = {"observation": self._get_observation_object()}
        return self._get_observation_array(), info

    def step(self, action):
        action = int(action)
        report_charge: ReportCharge | None = None

        if action == 0:
            self.ac_on = False
        elif action == 1:
            self.ac_on = True
        elif action == 2:
            self.fan_on = False
        elif action == 3:
            self.fan_on = True
        elif action == 4 and self.flexible_appareil is not None:
            report_charge = ReportCharge(
                appareil=self.flexible_appareil.nom,
                report_minutes=PAS_DECISION_MINUTES,
            )

        weather = self.weather_profile[self.step_index]
        T_ext = weather["temperature_ext"]

        T_int = self.thermal.step(T_ext=T_ext, dt_hours=self.dt_hours, ac_on=self.ac_on)

        # Charge non-thermique issue de RAMP (M2), au format commun ProfilChargePas
        profil_pas = self.load_profile[self.step_index]
        non_thermal_energy = profil_pas.energie_non_thermique_totale_kwh

        # Garde-fou anti double-comptage : la clim et le ventilo sont pilotes par
        # l'action RL (ci-dessous), pas par RAMP. Si le profil RAMP fourni par M2
        # inclut malgre tout leur energie dans energie_par_appareil_kwh, on la retire
        # ici pour ne pas la compter deux fois. A confirmer avec M1/M2.
        for nom_appareil in NOMS_APPAREILS_CONTROLES_PAR_ENV:
            non_thermal_energy -= profil_pas.energie_par_appareil_kwh.get(
                nom_appareil, 0.0
            )

        # 1) On réinjecte d'abord l'énergie différée par un report demandé au pas
        #    précédent, puis on remet le compteur de report à zéro.
        non_thermal_energy += self.deferred_flexible_kwh
        self.deferred_flexible_kwh = 0.0

        # 2) Si un report est demandé *ce pas-ci*, on retire l'énergie de l'appareil
        #    flexible du pas courant et on la met de côté pour le pas suivant
        #    (report d'un seul pas dans ce MVP).
        if report_charge is not None and self.flexible_appareil is not None:
            flexible_energy_this_step = profil_pas.energie_par_appareil_kwh.get(
                self.flexible_appareil.nom, 0.0
            )
            non_thermal_energy -= flexible_energy_this_step
            self.deferred_flexible_kwh += flexible_energy_this_step

        fan_energy = (
            convertir_en_kwh(self.fan_power_w, PAS_DECISION_MINUTES)
            if self.fan_on
            else 0.0
        )
        ac_energy = self.thermal.electric_consumption_kwh(
            dt_hours=self.dt_hours, ac_on=self.ac_on
        )

        total_energy = non_thermal_energy + fan_energy + ac_energy

        new_balance = self.meter.consume(total_energy)

        self.current_consumption = total_energy
        self.cumulative_consumption += total_energy
        self.historique_consommation_kwh.append(total_energy)

        self.step_index += 1
        self.hour += self.dt_hours
        self.current_datetime += timedelta(hours=self.dt_hours)

        terminated = self.meter.is_cutoff
        truncated = (
            self.hour >= self.target_hours
            or self.step_index >= len(self.load_profile)
        )

        comfort_penalty = abs(T_int - 25.0)
        energy_penalty = total_energy
        cutoff_penalty = 20.0 if self.meter.is_cutoff else 0.0

        reward = -(comfort_penalty + energy_penalty + cutoff_penalty)
        if truncated and not terminated:
            reward += 10.0

        info = {
            "observation": self._get_observation_object(),
            "action": Action(
                climatisation_active=self.ac_on,
                ventilateur_actif=self.fan_on,
                report_charge=report_charge,
            ),
            "balance": new_balance,
            "temperature": T_int,
            "temperature_ext": T_ext,
            "energy_consumption": total_energy,
            "cumulative_consumption": self.cumulative_consumption,
        }

        return self._get_observation_array(), reward, terminated, truncated, info

    def _get_observation_object(self) -> Observation:
        if self.step_index < len(self.weather_profile):
            weather = self.weather_profile[self.step_index]
        else:
            weather = self.weather_profile[-1]

        temps_avant_cible_h = max(0.0, self.target_hours - self.hour)
        jours_ecoules = self.hour / 24.0
        rythme = (
            self.cumulative_consumption / jours_ecoules if jours_ecoules > 0 else 0.0
        )

        return Observation(
            credit_restant_kwh=self.meter.balance,
            heure=self.hour % 24.0,
            jour_semaine=self.current_datetime.weekday(),
            temps_avant_date_cible_minutes=int(temps_avant_cible_h * 60),
            temperature_interieure_c=self.thermal.T_int,
            temperature_exterieure_c=weather["temperature_ext"],
            humidite_pourcent=weather["humidity"],
            occupation=True,
            consommation_cumulee_kwh=self.cumulative_consumption,
            rythme_actuel_kwh_par_jour=rythme,
            historique_consommation_kwh=tuple(self.historique_consommation_kwh),
            etat_appareils={"climatisation": self.ac_on, "ventilateur": self.fan_on},
        )

    def _get_observation_array(self) -> np.ndarray:
        obs = self._get_observation_object()
        return np.array([
            obs.credit_restant_kwh,
            obs.heure,
            float(obs.jour_semaine),
            obs.temps_avant_date_cible_minutes / 60.0,
            obs.temperature_interieure_c,
            obs.temperature_exterieure_c,
            obs.humidite_pourcent,
            float(obs.occupation),
            obs.consommation_cumulee_kwh,
            obs.rythme_actuel_kwh_par_jour,
            float(self.ac_on),
            float(self.fan_on),
        ], dtype=np.float32)