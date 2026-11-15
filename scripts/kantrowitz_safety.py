from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytical.isentropic import *
from analytical.atmosphere import *
from analytical.constants import *
from analytical.shocks import *


def kantrowitz_safety(kappa):

    """

    For a given divergence ratio, find the allowed convergence.
    Y(M) = A/A*
    Y(M1) / A1 = Y(M2) / A2
    Y^-1 { A2/A1 Y(M1) } = M2 
    """

    M1 = 1
    M2 = IsentropicRelations.area_mach_inv(kappa, True) # expand flow first.
    M2s = NormalShocks.post_shock_mach(M2)

    Astar = kappa / IsentropicRelations.area_mach(M2s)

    CR = Astar / kappa

    print(f"M1 = {M1:.4f}")
    print(f"A1 = 1")
    print(f"M2 = {M2:.4f}")
    print(f"A2 = {kappa}")
    print(f"M2s = {M2s:.4f}")
    print(f"A3 = {Astar}")
    print(f"CR = {CR}")

if __name__ == "__main__":
    kantrowitz_safety(1.262)
    