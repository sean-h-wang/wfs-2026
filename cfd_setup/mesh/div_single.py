import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cfd_setup.mesh.base import *
from cfd_setup.mesh.point import *
from cfd_setup.onshape.api import *
from data.links import *

import math
from types import SimpleNamespace

NX_FREESTREAM = 69
GX_FREESTREAM = """2"""

NX_FREESTREAM_INV = 277
GX_FREESTREAM_INV = """0.5"""

NX_DIV = 40
GX_DIV = """1"""

NX_CONV = 10
GX_CONV = """1"""

NZ_DUCT = 28
GZ_DUCT = """1"""

class DivSingleMeshGenerator(MeshGenerator):

    def _compute_vertices(self):
        DV = SimpleNamespace(**self.geo_df.set_index("Name")["Value"].to_dict())
        num_points = 20
        gap = 2000
        gap_front = 500
        P = [None] * num_points

        P[0] = Point(-gap, 0)
        P[2] = Point(0, 0)
        P[4] = Point(DV.L_conv, 0)
        P[6] = Point(DV.L_div, 0, P[4])
        P[8] = Point(gap_front, 0, P[6])

        # ---

        P[10] = Point(0, DV.h_inlet, P[8])
        P[12] = Point(-gap_front, 0, P[10])
        P[14] = Point(-DV.L_div, DV.L_div * tan(DV.theta_div), P[12])
        P[16] = Point(-DV.L_conv, -DV.L_conv * tan(DV.theta_conv), P[14])
        P[18] = Point(-gap, 0, P[16])



        for i in range(1, num_points, 2):
            if P[i] is None and P[i-1] is not None:
                P[i] = P[i-1].reflect_xz()

        return P

    def _build_blocks_section(self, scale: int) -> str:
        return f"""
// FLOW GOES FROM +X TO -X
blocks
(
    hex (0 2 3 1 18 16 17 19) // 1
    ({NX_FREESTREAM_INV * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_FREESTREAM_INV}
        1
        {GZ_DUCT}
    )

    hex (2 4 5 3 16 14 15 17) // 2
    ({NX_CONV * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_CONV}
        1
        {GZ_DUCT}
    )

    hex (4 6 7 5 14 12 13 15) // 3
    ({NX_DIV * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_DIV}
        1
        {GZ_DUCT}
    )

    hex (6 8 9 7 12 10 11 13) // 4
    ({NX_FREESTREAM * scale} 1 {NZ_DUCT * scale})
    simpleGrading
    (
        {GX_FREESTREAM}
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
            (8 9 11 10)
        );
    }

    farfield
    {
        type patch;
        faces 
        (
            (12 10 11 13)
            (18 16 17 19)
        );
    }

    downstream
    {
        type patch;
        faces
        (
            (0 18 19 1)
        );
    }

    walls
    {
        type wall;
        faces
        (
            (14 12 13 15)
            (16 14 15 17)
        );
    }

    centerline
    {
        type symmetryPlane;
        faces 
        (
            (2 0 1 3)
            (4 2 3 5)
            (6 4 5 7)
            (8 6 7 9)
        );
    }

    defaultFaces
    {
        type empty;
        faces
        (
            (0 2 16 18)
            (2 4 14 16)
            (4 6 12 14)
            (6 8 10 12)

            (19 17 3 1)
            (17 15 5 3)
            (15 13 7 5)
            (13 11 9 7)
        );
    }
);
"""


if __name__ == "__main__":
    # Engine
    api = OnshapeAPI(INLET_LINK, INLET_FILE)
    geo_df = api.get_evaluated_variables_df()

    mesh = DivSingleMeshGenerator(geo_df)
    for i, v in enumerate(mesh.vertices):
        print(f"P[{i}] = {v}")