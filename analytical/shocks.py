from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytical.constants import *
import math
from scipy.optimize import brentq, minimize_scalar

class NormalShocks:

    @staticmethod
    def pressure_ratio(M1):
        if M1 < 1:
            raise ValueError("Normal shocks cannot form in subsonci flow.")
        return (2 * GAMMA * M1**2 - (GAMMA - 1)) / (GAMMA + 1)
    
    @staticmethod
    def temperature_ratio(M1):
        if M1 < 1:
            raise ValueError("Normal shocks cannot form in subsonci flow.")
        return (2 * GAMMA * M1**2 - (GAMMA - 1)) * ((GAMMA - 1) * M1**2 + 2) / ((GAMMA + 1)**2 * M1**2)
    
    @staticmethod
    def density_ratio(M1):
        if M1 < 1:
            raise ValueError("Normal shocks cannot form in subsonci flow.")
        return (GAMMA + 1) * M1**2 / ((GAMMA-1) * M1**2 + 2)
    
    @staticmethod
    def post_shock_mach(M1):
        if M1 < 1:
            raise ValueError("Normal shocks cannot form in subsonci flow.")
        return math.sqrt(((GAMMA - 1)* M1**2 + 2) / (2 * GAMMA * M1**2 - (GAMMA - 1)))
    

class ObliqueShocks:

    @staticmethod
    def solve_beta(M, theta):
        # theta in DEGREES!!!!!!!!!!!!!!!!
        theta_rad = math.radians(theta)

        def residual(beta_rad):
            return math.tan(theta_rad) - (2 / math.tan(beta_rad)) * (M**2 * math.sin(beta_rad)**2 - 1) / (M**2 * (GAMMA + math.cos(2 * beta_rad)) + 2)

        def theta_of_beta(beta_rad):
            num = (2 / math.tan(beta_rad)) * (M**2 * math.sin(beta_rad)**2 - 1)
            den = M**2 * (GAMMA + math.cos(2 * beta_rad)) + 2
            return math.atan(num / den)

        mu = math.asin(1.0 / M)
        result = minimize_scalar(lambda b: -theta_of_beta(b), bounds=(mu + 1e-6, math.pi / 2 - 1e-6), method='bounded')
        beta_critical = result.x
        theta_max = math.degrees(-result.fun)

        if theta > theta_max:
            raise ValueError(f"theta={theta} deg exceeds theta_max={theta_max:.2f} deg for M={M}")

        return math.degrees(brentq(residual, mu + 1e-6, beta_critical - 1e-6))
    

if __name__ == "__main__":
    M = 3.0
    theta = 12.0
    beta = ObliqueShocks.solve_beta(M, theta)
    print(f"M={M}, theta={theta} deg -> beta={beta:.4f} deg")