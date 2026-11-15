import numpy as np
from cfd_analysis.filters import *


def _cell_sizes(centers: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """
    Recover cell sizes from cell center coordinates and boundary limits.
    Works for any direction (x or z). Centers must be sorted ascending.

    The first cell size is derived from the distance to the boundary,
    each subsequent size is recovered from the gap between centers.
    """
    n    = len(centers)
    h    = np.empty(n)
    h[0] = (centers[0] - lo) * 2.0
    for i in range(n - 1):
        h[i + 1] = 2.0 * (centers[i + 1] - centers[i]) - h[i]
    # assert np.isclose(np.sum(h), hi - lo, rtol=0.05), \
    #     f"Cell size sum {np.sum(h):.4f} does not match span {hi - lo:.4f}"
    return h

def line_average(property: str, df: pd.DataFrame, box: Box) -> float:
    df_box    = box.filter(df).sort_values('z').reset_index(drop=True)
    dz        = _cell_sizes(df_box['z'].values, box.lo.z, box.hi.z)
    return np.sum(df_box[property].values * dz) / np.sum(dz)