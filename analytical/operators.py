from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import math
import numpy as np
from abc import ABC, abstractmethod

from analytical.constants import *
from analytical.isentropic import *
from analytical.shocks import *

class BaseDuct(ABC):
    
    def __init__(self, A1: float, A2: float):
        self.A1 = A1
        self.A2 = A2
    
    @abstractmethod
    def flow(self, M1, P1, T1, rho1):
        pass

class StraightDuct(BaseDuct):

    def flow(self, M1, P1, T1, rho1):
        if self.A1 != self.A2:
            raise ValueError(f"StraightDuct requires A1 == A2, got A1={self.A1}, A2={self.A2}")
        return M1, P1, T1, rho1

class IsentropicDuct(BaseDuct):

    def flow(self, M1, P1, T1, rho1):
        A1_Astar = IsentropicRelations.area_mach(M1)
        Astar = self.A1 / A1_Astar
        if (self.A1 <= Astar <= self.A2) or (self.A2 <= Astar <= self.A1):
            raise ValueError(f"This duct will choke. Got A1 = {self.A1:.3f}, A* = {Astar:.3f}, A2 = {self.A2:.3f}")

        M2 = IsentropicRelations.area_mach_inv_rel(self.A1, M1, self.A2)
        
        P2 = P1 * IsentropicRelations.P0_P(M1) / IsentropicRelations.P0_P(M2)
        T2 = T1 * IsentropicRelations.T0_T(M1) / IsentropicRelations.T0_T(M2)
        rho2 = rho1 * IsentropicRelations.rho0_rho(M1) / IsentropicRelations.rho0_rho(M2)

        return M2, P2, T2, rho2
    
class ShockDuct(BaseDuct):

    def flow(self, M1, P1, T1, rho1):
        if self.A1 != self.A2:
            raise ValueError(f"ShockDuct requires A1 == A2, got A1={self.A1}, A2={self.A2}")
        
        if M1 <= 1:
            return M1, P1, T1, rho1
        
        P2 = P1 * NormalShocks.pressure_ratio(M1)
        T2 = T1 * NormalShocks.temperature_ratio(M1)
        rho2 = rho1 * NormalShocks.density_ratio(M1)
        M2 = NormalShocks.post_shock_mach(M1)
        return M2, P2, T2, rho2

class ObliqueShockDuct(BaseDuct):

    def flow(self, M1, P1, T1, rho1, theta_deg):
        if self.A1 != self.A2:
            raise ValueError(f"ObliqueShockDuct requires A1 == A2, got A1={self.A1}, A2={self.A2}")

        if M1 <= 1:
            return M1, P1, T1, rho1, 'S'
        try:
            beta_deg = ObliqueShocks.solve_beta(M1, theta_deg)
            beta_rad = math.radians(beta_deg)
        except ValueError:
            M2, P2, T2, rho2 = ShockDuct(1, 1).flow(M1, P1, T1, rho1)
            return M2, P2, T2, rho2, 'N'

        M1n = M1 * math.sin(beta_rad)
        M1t = M1 * math.cos(beta_rad)

        # Isentropic Invertibility - area contraction and reexpansion = no area change - this means that M2 is a good approximation for the post-disturbance horizontal flow.
        # Flow can turn if the angle is not big enough to separate.
        M2n, P2, T2, rho2 = ShockDuct(1, 1).flow(M1n, P1, T1, rho1)
        M2t = M1t * math.sqrt(T1 / T2)
        M2 = math.sqrt(M2n**2 + M2t**2)
        return M2, P2, T2, rho2, 'O'

class PrandtlMeyerDuct(BaseDuct):

    def flow(self, M1, P1, T1, rho1, theta_deg):
        if self.A1 != self.A2:
            raise ValueError(f"PrandtlMeyerDuct requires A1 == A2, got A1={self.A1}, A2={self.A2}")

        M2 = IsentropicRelations.prandtl_meyer_mach(M1, theta_deg)
        P2 = P1 * IsentropicRelations.P0_P(M1) / IsentropicRelations.P0_P(M2)
        T2 = T1 * IsentropicRelations.T0_T(M1) / IsentropicRelations.T0_T(M2)
        rho2 = rho1 * IsentropicRelations.rho0_rho(M1) / IsentropicRelations.rho0_rho(M2)

        return M2, P2, T2, rho2
            
