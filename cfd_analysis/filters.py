"""
filters.py — Spatial filters for OpenFOAM post-processing
==========================================================
All filters share a common base: mask(), filter(), union(), intersection().
Filters of any type can be mixed freely in union/intersection.

Usage:
    from filters import Box, DiagonalStrip

    box   = Box(Point(0, -1, 0), Point(10, 1, 5))
    strip = DiagonalStrip(Point(0, 0, 0), Point(10, 0, 2), thickness=0.05)

    df_box          = box.filter(df)
    df_strip        = strip.filter(df)
    df_union        = Filter.union(df, box, strip)
    df_intersection = Filter.intersection(df, box, strip)
"""

import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from cfd_setup.mesh.point import Point


# ─────────────────────────────────────────────────────────────────────────────
# BASE
# ─────────────────────────────────────────────────────────────────────────────

class Filter(ABC):

    @abstractmethod
    def mask(self, df: pd.DataFrame) -> pd.Series:
        pass

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[self.mask(df)].copy()

    def __or__(self, other: 'Filter') -> 'UnionFilter':
        return UnionFilter(self, other)

    def __and__(self, other: 'Filter') -> 'IntersectionFilter':
        return IntersectionFilter(self, other)

    @staticmethod
    def union(df: pd.DataFrame, *filters: 'Filter') -> pd.DataFrame:
        mask = pd.Series(False, index=df.index)
        for f in filters:
            mask |= f.mask(df)
        return df[mask].copy()

    @staticmethod
    def intersection(df: pd.DataFrame, *filters: 'Filter') -> pd.DataFrame:
        mask = pd.Series(True, index=df.index)
        for f in filters:
            mask &= f.mask(df)
        return df[mask].copy()


# ─────────────────────────────────────────────────────────────────────────────
# COMPOSITE FILTERS — enables box | strip and box & strip syntax
# ─────────────────────────────────────────────────────────────────────────────

class UnionFilter(Filter):

    def __init__(self, *filters: Filter):
        self.filters = filters

    def mask(self, df: pd.DataFrame) -> pd.Series:
        mask = pd.Series(False, index=df.index)
        for f in self.filters:
            mask |= f.mask(df)
        return mask

    def __repr__(self):
        return f"UnionFilter({', '.join(repr(f) for f in self.filters)})"


class IntersectionFilter(Filter):

    def __init__(self, *filters: Filter):
        self.filters = filters

    def mask(self, df: pd.DataFrame) -> pd.Series:
        mask = pd.Series(True, index=df.index)
        for f in self.filters:
            mask &= f.mask(df)
        return mask

    def __repr__(self):
        return f"IntersectionFilter({', '.join(repr(f) for f in self.filters)})"


# ─────────────────────────────────────────────────────────────────────────────
# BOX
# ─────────────────────────────────────────────────────────────────────────────

class Box(Filter):
    """
    Axis-aligned bounding box defined by two Point corners.
    For 2D meshes set lo.y=-1, hi.y=1.
    """

    def __init__(self, lo: Point, hi: Point):
        self.lo = lo
        self.hi = hi

    def mask(self, df: pd.DataFrame) -> pd.Series:
        return (
            (df['x'] >= self.lo.x) & (df['x'] <= self.hi.x) &
            (df['y'] >= self.lo.y) & (df['y'] <= self.hi.y) &
            (df['z'] >= self.lo.z) & (df['z'] <= self.hi.z)
        )

    def __repr__(self):
        return f"Box(lo={self.lo}, hi={self.hi})"


# ─────────────────────────────────────────────────────────────────────────────
# DIAGONAL STRIP
# ─────────────────────────────────────────────────────────────────────────────

class DiagonalStrip(Filter):
    """
    Selects all cells within `thickness` perpendicular distance of a line
    segment defined by two Points. Distance computed in x-z plane only.
    Y axis ignored — mesh is always one cell thick in y.
    Cells outside the segment endpoints are never selected.
    """

    def __init__(self, p0: Point, p1: Point, thickness: float):
        self.p0        = np.array([p0.x, p0.z])
        self.p1        = np.array([p1.x, p1.z])
        self.thickness = thickness

    def mask(self, df: pd.DataFrame) -> pd.Series:
        pts    = df[['x', 'z']].values
        seg    = self.p1 - self.p0
        len_sq = np.dot(seg, seg)

        v         = pts - self.p0
        t         = np.dot(v, seg) / len_sq
        in_bounds = (t >= 0.0) & (t <= 1.0)

        closest = self.p0 + t[:, None] * seg
        diff    = pts - closest
        dist    = np.sqrt(diff[:, 0]**2 + diff[:, 1]**2)

        dist[~in_bounds] = np.inf

        return pd.Series(dist <= self.thickness, index=df.index)

    def __repr__(self):
        return f"DiagonalStrip(p0={self.p0}, p1={self.p1}, thickness={self.thickness})"