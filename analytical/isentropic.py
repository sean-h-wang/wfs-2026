from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytical.constants import *
import math

class IsentropicRelations:

    @staticmethod
    def _bisect(func, a, b, tol=1e-9, max_iter=10000):
        fa = func(a)
        fb = func(b)
        if fa * fb > 0:
            raise ValueError("❌ Bisection requires a sign change in interval!")
        for _ in range(max_iter):
            c = 0.5 * (a + b)
            fc = func(c)
            if abs(fc) < tol or (b - a) < tol:
                return c
            if fa * fc < 0:
                b = c
                fb = fc
            else:
                a = c
                fa = fc
        return 0.5 * (a + b)

    @staticmethod
    def T0_T(M1):
        return 1 + (GAMMA - 1)/2 * M1**2
    
    @staticmethod
    def P0_P(M1):
        return IsentropicRelations.T0_T(M1) ** (GAMMA / (GAMMA - 1))
    
    @staticmethod
    def rho0_rho(M1):
        return IsentropicRelations.T0_T(M1) ** (1 / (GAMMA - 1))
    
    @staticmethod
    def area_mach(M):
        base = 2 / (GAMMA + 1) * (1 + (GAMMA-1)/2 * M**2)
        exponent = (GAMMA + 1) / 2 / (GAMMA - 1)

        return 1/M * base ** exponent
    
    @staticmethod
    def area_mach_inv(A_Astar, supersonic):
        if abs(A_Astar - 1) < 1e-7:
            return 1
        
        def f(m):
            return IsentropicRelations.area_mach(m) - A_Astar
        
        if supersonic:
            M = IsentropicRelations._bisect(f, 1 + 1e-6, 50)
        else:
            M = IsentropicRelations._bisect(f, 1e-6, 1 - 1e-6)
        
        return M
    
    @staticmethod
    def area_mach_inv_rel(A1, M1, A2):
        A1_Astar = IsentropicRelations.area_mach(M1)
        Astar = A1 / (A1_Astar)

        if A2 < Astar:
            raise ValueError("A2 < Astar - will choke")

        A2_Astar = A2 / Astar
        M2 = IsentropicRelations.area_mach_inv(A2_Astar, M1 >= 1)
        return M2

    @staticmethod
    def prandtl_meyer(M):
        # A arctan B - arctan C
        A = math.sqrt((GAMMA + 1)/(GAMMA - 1))
        B = math.sqrt((GAMMA - 1)/(GAMMA + 1) * (M**2 - 1))
        C = math.sqrt(M**2 - 1)
        return A * math.atan(B) - math.atan(C)

    @staticmethod
    def prandtl_meyer_mach(M1, theta_deg):
        theta_rad = theta_deg * math.pi / 180
        if M1 < 1:
            raise ValueError(f"M1 >= 1 required, got M1 = {M1}.")

        def f(M):
            return IsentropicRelations.prandtl_meyer(M) - (theta_rad + IsentropicRelations.prandtl_meyer(M1))

        M2 = IsentropicRelations._bisect(f, 1, 1000)
        return M2

    
def main():
    print("--- Running Prandtl-Meyer Verification Tests ---")
    
    # Test Case 1: M = 1.0 should yield nu = 0
    nu_1 = IsentropicRelations.prandtl_meyer(1.0)
    print(f"nu(1.0) = {nu_1:.5f} (Expected: 0.00000)")
    assert math.isclose(nu_1, 0.0, abs_tol=1e-6)

    # Test Case 2: M = 2.0 with gamma = 1.4
    # Standard gas table value for nu(2.0) is approx 0.46037 rad (~26.38 deg)
    nu_2 = IsentropicRelations.prandtl_meyer(2.0)
    print(f"nu(2.0) = {nu_2:.5f} rad ({math.degrees(nu_2):.2f} deg)")

    # Test Case 3: Inversion test
    # Start at M1 = 2.0, turn by theta = 10 degrees (0.1745 rad)
    M1 = 2.0
    theta_turn = 10.0
    M2 = IsentropicRelations.prandtl_meyer_mach(M1, theta_turn)
    
    print(f"Expanding from M1 = {M1} through theta = {theta_turn} deg:")
    print(f"Calculated post-expansion Mach (M2) = {M2:.4f}")
    
    # Round-trip check: does nu(M2) equal nu(M1) + theta_turn?
    nu_expected = IsentropicRelations.prandtl_meyer(M1) + math.radians(theta_turn)
    nu_actual = IsentropicRelations.prandtl_meyer(M2)
    print(f"Target Nu: {nu_expected:.5f} | Result Nu: {nu_actual:.5f}")
    assert math.isclose(nu_expected, nu_actual, rel_tol=1e-6)
    
    print("All tests passed successfully!")

if __name__ == "__main__":
    main()