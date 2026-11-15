import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cfd_setup.mesh.base import *
from cfd_setup.mesh.point import *
from cfd_setup.onshape.api import *
from data.links import *

import math
from types import SimpleNamespace

NX_FREESTREAM = 100
GX_FREESTREAM = """6"""

NX_FREESTREAM_INV = 150
GX_FREESTREAM_INV = """0.5"""

NX_DIV = 75
GX_DIV = """1"""

NX_WEDGE = 10
GX_WEDGE = """1"""

NX_ISO = 38
GX_ISO = """1"""

NZ_DUCT = 32
GZ_DUCT = """1"""


class DRIModuleMesh(MeshGenerator):

    def _compute_vertices(self):
        DV = SimpleNamespace(**self.geo_df.set_index("Name")["Value"].to_dict())
        num_points = 28
        gap = 1000
        P = [None] * num_points

        P[0] = Point(0, 0)
        P[2] = Point(-gap, 0)
        P[4] = Point(-DV.L_div, 0, P[2])
        P[6] = Point(-DV.h_wedge / tan(DV.theta_wedge), DV.h_wedge, P[4])
        P[8] = Point(-DV.h_wedge / tan(DV.theta_wedge), -DV.h_wedge, P[6])
        P[10] = Point(-DV.L_isolation, 0, P[8])
        P[12] = Point(-gap, 0, P[10])

        P[26] = Point(0, DV.h_inlet)
        P[24] = Point(P[2].x, P[26].z)
        P[22] = Point(-DV.L_div, DV.L_div * tan(DV.theta_div), P[24])
        P[20] = Point(P[6].x, P[22].z)
        P[18] = Point(P[8].x, P[20].z)
        P[16] = Point(P[10].x, P[18].z)
        P[14] = Point(P[12].x, P[16].z)
        
        for i in range(1, num_points, 2):
            if P[i] is None and P[i-1] is not None:
                P[i] = P[i-1].reflect_xz()

        return P

    def _build_blocks_section(self, scale: int) -> str:
        return f"""
// FLOW GOES FROM +X TO -X
blocks
(
    hex (2 0 1 3 24 26 27 25) // 1
    ({NX_FREESTREAM * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_FREESTREAM}
        1
        {GZ_DUCT}
    )

    hex (4 2 3 5 22 24 25 23) // 2
    ({NX_DIV * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_DIV}
        1
        {GZ_DUCT}
    )

    hex (6 4 5 7 20 22 23 21) // 3
    ({NX_WEDGE * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_WEDGE}
        1
        {GZ_DUCT}
    )

    hex (8 6 7 9 18 20 21 19) // 4
    ({NX_WEDGE * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_WEDGE}
        1
        {GZ_DUCT}
    )

    hex (10 8 9 11 16 18 19 17) // 5
    ({NX_ISO * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_ISO}
        1
        {GZ_DUCT}
    )

    hex (12 10 11 13 14 16 17 15) // 6
    ({NX_FREESTREAM_INV * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_FREESTREAM_INV}
        1
        {GZ_DUCT}
    )
);
"""

    def _build_boundary_section(self) -> str:
        return """
boundary
(
    upstream
    {
        type patch;
        faces 
        (
            (26 0 1 27)
        );
    }

    farfield
    {
        type patch;
        faces 
        (
            (24 26 27 25)
            (16 18 19 17)
            (14 16 17 15)
        );
    }

    downstream
    {
        type patch;
        faces
        (
            (12 14 15 13)
        );
    }

    walls
    {
        type wall;
        faces
        (
            (22 24 25 23)
            (20 22 23 21)
            (18 20 21 19)

            (4 6 7 5)
            (6 8 9 7)
        );
    }

    centerline
    {
        type symmetryPlane;
        faces 
        (
            (0 2 3 1)
            (2 4 5 3)
            (8 10 11 9)
            (10 12 13 11)
        );
    }

    defaultFaces
    {
        type empty;
        faces
        (
            (24 2 0 26)
            (22 4 2 24)
            (20 6 4 22)
            (18 8 6 20)
            (16 10 8 18)
            (14 12 10 16)

            (27 1 3 25)
            (25 3 5 23)
            (23 5 7 21)
            (21 7 9 19)
            (19 9 11 17)
            (17 11 13 15)
        );
    }
);
"""


if __name__ == "__main__":
    # Engine
    api = OnshapeAPI(DRI_MODULE_LINK, DRI_MODULE_FILE)
    geo_df = api.get_evaluated_variables_df()

    mesh = DRIModuleMesh(geo_df)
    for i, v in enumerate(mesh.vertices):
        print(f"P[{i}] = {v}")