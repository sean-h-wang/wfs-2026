"""
data_processing.py — OpenFOAM case loader
==========================================
Loads OpenFOAM fields into a pandas DataFrame.
Computes derived fields: Mach number, stagnation pressure.
No plotting. No spatial filtering — import filters.py for that.

Usage:
    from data_processing import Case
    case = Case('./runs/M5alt30')
    df   = case.load()
    df   = case.load(time='0.025')
    for t, df in case.iter_times(t_min=0.01, every=5):
        ...
"""

import os
import numpy as np
import pandas as pd
from typing import Iterator, List, Optional

try:
    import fluidfoam
except ImportError:
    raise ImportError("pip install fluidfoam")


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

GAMMA = 1.4
R_AIR = 287.0


# ─────────────────────────────────────────────────────────────────────────────
# CASE
# ─────────────────────────────────────────────────────────────────────────────

class Case:
    """
    Loads an OpenFOAM case into a pandas DataFrame.

    Standard columns : x, y, z, p, T, rho, Ux, Uy, Uz, U
    Derived columns  : a, M, p0
    """

    SCALARS = ['p', 'T', 'rho']

    def __init__(self, path: str):
        self.path   = str(path)
        self._times: Optional[List[str]] = None

    # ── time discovery ────────────────────────────────────────────────────────

    def times(self) -> List[str]:
        if self._times is None:
            dirs = [
                d for d in os.listdir(self.path)
                if os.path.isdir(os.path.join(self.path, d))
                and _is_numeric(d) and float(d) > 0
            ]
            self._times = sorted(dirs, key=float)
        return self._times

    def latest(self) -> str:
        t = self.times()
        if not t:
            raise FileNotFoundError(f"No time directories in {self.path}")
        return t[-1]

    # ── load ──────────────────────────────────────────────────────────────────

    def load(self, time: Optional[str] = None) -> pd.DataFrame:
        t = time if time is not None else self.latest()
        print(f"Loading {self.path}  t={t}")

        x, y, z = fluidfoam.readmesh(self.path, verbose=False)
        data = {'x': x, 'y': y, 'z': z}

        for field in self.SCALARS:
            data[field] = fluidfoam.readscalar(self.path, t, field, verbose=False)

        U_vec      = fluidfoam.readvector(self.path, t, 'U', verbose=False)
        data['Ux'] = U_vec[0]
        data['Uy'] = U_vec[1]
        data['Uz'] = U_vec[2]
        data['U']  = np.sqrt(U_vec[0]**2 + U_vec[1]**2 + U_vec[2]**2)

        # derived
        T          = data['T']
        p          = data['p']
        U          = data['U']
        a          = np.sqrt(np.maximum(GAMMA * R_AIR * T, 0.0))
        M          = np.where(a > 0, U / a, 0.0)
        p0         = p * (1.0 + 0.5 * (GAMMA - 1.0) * M**2) ** (GAMMA / (GAMMA - 1.0))

        data.update({'a': a, 'M': M, 'p0': p0})

        df = pd.DataFrame(data)
        print(f"  {len(df):,} cells  |  M=[{M.min():.2f}, {M.max():.2f}]  p=[{p.min():.0f}, {p.max():.0f}] Pa")
        return df

    # ── time series ───────────────────────────────────────────────────────────

    def iter_times(
        self,
        t_min: float = 0.0,
        t_max: float = float('inf'),
        every: int   = 1,
    ) -> Iterator[tuple[str, pd.DataFrame]]:
        selected = [
            t for t in self.times()
            if t_min <= float(t) <= t_max
        ][::every]
        for t in selected:
            yield t, self.load(time=t)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False