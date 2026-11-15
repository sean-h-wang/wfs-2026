# =============================================================================
#
#            **********
#    <-----------------------------
#              ************
#               *************
#                **************
#        <---------------------------------
#                  ****************
#                   *****************
#                    ******************
#            <---------------------------------------
#                      ********************
#    W A N G    F L I G H T    S Y S T E M S
#
#    Wang Flight Systems Research Division LLC
#    Hypersonic Civilian Transport Program
#    RSC — Rectangular Scramjet Concept
# =============================================================================
"""
OpenFOAM geometric grading calculator.

Given first cell size, last cell size, and total length — computes
per-cell ratio r, raw cell count n, integer-rounded n, grading ratio g,
and back-calculates actual first and last cell sizes with deviations.

Location: src/mesh/grading_calculator.py
"""

import math


def calculate_grading(
    L: float,
    a: float,
    b: float,
    verbose: bool = True,
) -> dict:
    """
    Calculate OpenFOAM simpleGrading parameters from physical cell sizes.

    Args:
        L: total block length [mm or any consistent unit]
        a: desired first cell size [same unit as L]
        b: desired last cell size [same unit as L]
        verbose: print formatted report

    Returns:
        dict with keys: r, n, g, a_actual, b_actual, a_err_pct, b_err_pct
    """
    if a <= 0 or b <= 0 or L <= 0:
        raise ValueError("L, a, b must all be positive.")
    if a + b > L:
        raise ValueError("First + last cell size exceeds total length.")

    # ── per-cell ratio ────────────────────────────────────────────────
    # derived from geometric series: r = (L - a) / (L - b)
    r = (L - a) / (L - b)

    # ── raw (non-integer) cell count ──────────────────────────────────
    # from r^(n-1) = b/a → n = 1 + ln(b/a) / ln(r)
    if abs(r - 1.0) < 1e-12:
        # uniform mesh edge case
        n_raw = L / a
        r = 1.0
    else:
        n_raw = 1.0 + math.log(b / a) / math.log(r)

    # ── integer cell count ────────────────────────────────────────────
    n = round(n_raw)
    if n < 2:
        n = 2

    # ── grading ratio for OpenFOAM ────────────────────────────────────
    g = b / a  # target grading = last/first

    # ── back-calculate actual cell sizes with integer n ───────────────
    # recompute r exactly for integer n using the length constraint
    # L = a_actual * (1 - r^n) / (1 - r)
    # r is kept from the continuous solution — a_actual absorbs the error
    if abs(r - 1.0) < 1e-12:
        a_actual = L / n
        b_actual = L / n
    else:
        a_actual = L * (1.0 - r) / (1.0 - r ** n)
        b_actual = a_actual * r ** (n - 1)

    # ── deviations from ideal ─────────────────────────────────────────
    a_err = a_actual - a
    b_err = b_actual - b
    a_err_pct = 100.0 * a_err / a
    b_err_pct = 100.0 * b_err / b

    # ── verification: sum of geometric series ─────────────────────────
    if abs(r - 1.0) < 1e-12:
        L_check = n * a_actual
    else:
        L_check = a_actual * (1.0 - r ** n) / (1.0 - r)
    L_err_pct = 100.0 * (L_check - L) / L

    result = {
        "r":         r,
        "n_raw":     n_raw,
        "n":         n,
        "g":         g,
        "g_actual":  b_actual / a_actual,
        "a_actual":  a_actual,
        "b_actual":  b_actual,
        "a_err_pct": a_err_pct,
        "b_err_pct": b_err_pct,
        "L_check":   L_check,
        "L_err_pct": L_err_pct,
    }

    if verbose:
        _print_report(L, a, b, result)

    return result


def _print_report(L: float, a: float, b: float, res: dict) -> None:
    w = 60
    print("=" * w)
    print("  Wang Flight Systems — OpenFOAM Grading Calculator")
    print("=" * w)
    print(f"  {'Input':}")
    print(f"    Total length L       = {L:.4f}")
    print(f"    Target first cell a  = {a:.4f}")
    print(f"    Target last cell  b  = {b:.4f}")
    print(f"    Target grading    g  = {res['g']:.6f}  (= b/a)")
    print("-" * w)
    print(f"  {'Geometric Series Solution':}")
    print(f"    Per-cell ratio    r  = {res['r']:.8f}")
    print(f"    Raw cell count  n_raw= {res['n_raw']:.4f}")
    print(f"    Integer cells     n  = {res['n']}")
    print("-" * w)
    print(f"  {'Back-calculated actual values (integer n)':}")
    print(f"    Actual first cell    = {res['a_actual']:.4f}  "
          f"(error: {res['a_err_pct']:+.2f}%)")
    print(f"    Actual last cell     = {res['b_actual']:.4f}  "
          f"(error: {res['b_err_pct']:+.2f}%)")
    print(f"    Actual grading g     = {res['g_actual']:.6f}")
    print(f"    Length check         = {res['L_check']:.4f}  "
          f"(error: {res['L_err_pct']:+.4f}%)")
    print("=" * w)
    print(f"  OpenFOAM simpleGrading entry:")
    print(f"    n = {res['n']}    GR = {res['g_actual']:.6f}")
    print("=" * w)


if __name__ == "__main__":
    
    calculate_grading(L=2000, a=10, b=5)
    

    