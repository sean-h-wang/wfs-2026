from abc import ABC, abstractmethod
from cfd_setup.mesh.point import *
import math

def sin(x): return math.sin(math.radians(x))
def cos(x): return math.cos(math.radians(x))
def tan(x): return math.tan(math.radians(x))
def cot(x): return 1 / math.tan(math.radians(x))
def arctan(x): return math.degrees(math.atan(x))

class MeshGenerator(ABC):
    
    def __init__(self, geo_df):
        self.geo_df = geo_df
        self.vertices = self._compute_vertices()

    @abstractmethod
    def _compute_vertices(self):
        """Return list of Point objects defining the mesh geometry."""
        pass

    @abstractmethod
    def _build_blocks_section(self, scale: int) -> str:
        pass

    @abstractmethod
    def _build_boundary_section(self) -> str:
        pass

    def generate(self, scale: int = 1) -> str:
        mesh_dict  = self._build_header()
        mesh_dict += self._build_vertices_section()
        mesh_dict += self._build_edges_section()
        mesh_dict += self._build_blocks_section(int(scale))
        mesh_dict += self._build_boundary_section()
        mesh_dict += self._build_mergepatchpairs_section()
        return mesh_dict

    def _build_header(self) -> str:
        return """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

scale 0.001;

"""

    def _build_vertices_section(self) -> str:
        verts_str = "\n    ".join(
            f"{v} // {i}" for i, v in enumerate(self.vertices)
        )
        return f"""
vertices
(
    {verts_str}
);
"""

    def _build_edges_section(self) -> str:
        return """
edges
(

);
"""

    def _build_mergepatchpairs_section(self) -> str:
        return """
mergePatchPairs
(

);
"""