
from dataclasses import dataclass
from typing import Optional
from cfd_setup.mesh.base import *

@dataclass
class OpenFOAMConfig:
    mesh:             MeshGenerator
    filepath:         str
    mach:             float                  = 5
    altitude:         float                  = 30000
    scale:            int                    = 1
    end_time:         float                  = 0.005
    write_interval:   float                  = 1e-5
    max_co:           float                  = 0.5
    max_delta_t:      float                  = 1e-8