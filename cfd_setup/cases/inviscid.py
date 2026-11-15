from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
from cfd_setup.cases.config import *
from analytical.atmosphere import *
from analytical.constants import *
from analytical.isentropic import *


class InviscidCase:
    def __init__(self, cfg: OpenFOAMConfig):
        
        self.cfg    = cfg
        self.mesh_gen = cfg.mesh
        self.vertices = self.mesh_gen.vertices

        self.T_inf, self.P_inf, self.rho_inf = standard_atmosphere(cfg.altitude)
        self.a_inf = math.sqrt(GAMMA * R * self.T_inf)
        self.U_inf = cfg.mach * self.a_inf

        self.T0_inf = IsentropicRelations.T0_T(cfg.mach) * self.T_inf
        self.P0_inf = IsentropicRelations.P0_P(cfg.mach) * self.P_inf
        self.rho0_inf = IsentropicRelations.rho0_rho(cfg.mach) * self.rho_inf
        self.h0_inf = CP * self.T0_inf


    def write(self):
        for d in ["0", "constant", "system"]:
            os.makedirs(os.path.join(self.cfg.filepath, d), exist_ok=True)

        block_mesh = self.mesh_gen.generate(scale=self.cfg.scale)
        self._write("system/blockMeshDict",  block_mesh)
        self._write("system/controlDict",    self._control_dict())
        self._write("system/fvSchemes",      self._fv_schemes())
        self._write("system/fvSolution",     self._fv_solution())

        self._write("constant/thermophysicalProperties", self._thermo())
        self._write("constant/turbulenceProperties",     self._turbulence())

        self._write("0/U",   self._U())
        self._write("0/p",   self._p())
        self._write("0/T",   self._T())
        self._write("0/rho", self._rho())
        self._write("0/h",   self._h())

        self._write("case.foam", "")

        print(
            f"\n{'='*52}\n"
            f"  Wang Flight Systems Research Division LLC - Inviscid Case\n"
            f"{'='*52}\n"
            f"  path     : {self.cfg.filepath}\n"
            f"  mesh     : {self.cfg.mesh.__class__}\n"
            f"  Mach     : {self.cfg.mach}\n"
            f"  altitude : {self.cfg.altitude/1000:.1f} km\n"
            f"  T_inf    : {self.T_inf:.1f} K\n"
            f"  P_inf    : {self.P_inf:.0f} Pa\n"
            f"  U_inf    : {self.U_inf:.1f} m/s\n"
            f"{'='*52}\n"
        )

    def _header(self, cls: str, obj: str) -> str:
        return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""

    def _write(self, relpath: str, content: str) -> None:
        fullpath = os.path.join(self.cfg.filepath, relpath)
        with open(fullpath, "w") as f:
            f.write(content)

    def _inlet_bc(self, field: str) -> str:
        bcs = {
            "U":   f"fixedValue;\n        value           uniform ({-self.U_inf:.4f} 0 0);",
            "p":   f"fixedValue;\n        value           uniform {self.P_inf:.4f};",
            "T":   f"fixedValue;\n        value           uniform {self.T_inf:.4f};",
            "rho": f"calculated;\n        value           uniform {self.rho_inf:.6f};",
            "h":   f"calculated;\n        value           uniform {CP * self.T_inf:.4f};",
        }
        return bcs[field]

    def _outlet_bc(self, field: str) -> str:
        bcs = {
            "U":   "zeroGradient;",
            "p":   "zeroGradient;",
            "T":   "zeroGradient;",
            "rho": f"calculated;\n        value           uniform {self.rho_inf:.6f};",
            "h":   f"calculated;\n        value           uniform {CP * self.T_inf:.4f};",
        }
        return bcs[field]

    def _wall_bc(self, field: str) -> str:
        """Inviscid slip wall."""
        bcs = {
            "U":   "slip;",
            "p":   "zeroGradient;",
            "T":   "zeroGradient;",
            "rho": f"calculated;\n        value           uniform {self.rho_inf:.6f};",
            "h":   f"calculated;\n        value           uniform {CP * self.T_inf:.4f};",
        }
        return bcs[field]

    # ------------------------------------------------------------------
    # system/
    # ------------------------------------------------------------------

    def _control_dict(self) -> str:
        return self._header("dictionary", "controlDict") + f"""
application     rhoCentralFoam;

startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {self.cfg.end_time};

adjustTimeStep  yes;
maxCo           {self.cfg.max_co};
maxAcousticCo   {self.cfg.max_co};
maxDeltaT       {self.cfg.max_delta_t};
deltaT          1e-9;

writeControl    adjustableRunTime;
writeInterval   {self.cfg.write_interval};

purgeWrite      0;
writeFormat     binary;
writePrecision  8;
writeCompression off;
timeFormat      fixed;
timePrecision   10;
runTimeModifiable true;
"""

    def _fv_schemes(self) -> str:
        return self._header("dictionary", "fvSchemes") + """
fluxScheme      Kurganov;

ddtSchemes
{
    default         Euler;
}

gradSchemes
{
    default         Gauss linear limited 1;
}

divSchemes
{
    default         none;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default          linear;
    reconstruct(rho) vanLeer;
    reconstruct(U)   vanLeerV;
    reconstruct(T)   vanLeer;
    reconstruct(p)   vanLeer;
}

snGradSchemes
{
    default         corrected;
}
"""

    def _fv_solution(self) -> str:
        return self._header("dictionary", "fvSolution") + """
solvers
{
    "(rho|rhoU|rhoE)"
    {
        solver          diagonal;
    }

    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-9;
        relTol          0.01;
        minIter         1;
    }

    h
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-9;
        relTol          0.01;
        minIter         5;
    }
}
"""

    # ------------------------------------------------------------------
    # constant/
    # ------------------------------------------------------------------

    def _thermo(self) -> str:
        return self._header("dictionary", "thermophysicalProperties") + f"""
thermoType
{{
    type            hePsiThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleEnthalpy;
}}

Tmin            10;
Tmax            100000;

mixture
{{
    specie
    {{
        molWeight   28.96;
    }}
    thermodynamics
    {{
        Cp          1004;
        Hf          0;
    }}
    transport
    {{
        mu          0;
        Pr          1;
    }}
}}
"""

    def _turbulence(self) -> str:
        return self._header("dictionary", "turbulenceProperties") + """
simulationType    laminar;
"""

    # ------------------------------------------------------------------
    # 0/
    # ------------------------------------------------------------------

    def _field_0(self, cls: str, obj: str, dims: str, internal: str, patches: dict) -> str:
        patch_str = ""
        for name, bc in patches.items():
            patch_str += f"""
    {name}
    {{
        type            {bc}
    }}
    """
        return self._header(cls, obj) + f"""
dimensions      {dims};

internalField   uniform {internal};

boundaryField
{{{patch_str}
}}
"""

    def _patches(self, field: str) -> dict:
        return {
            "upstream":      self._inlet_bc(field),
            "downstream":    self._outlet_bc(field),
            "farfield":      self._outlet_bc(field),
            "walls":         self._wall_bc(field),
            "centerline":    "symmetryPlane;",
            "defaultFaces":  "empty;",
        }
    
    def _U(self) -> str:
        init_u = -0.8 * self.a_inf if self.cfg.mach >= 1 else -self.U_inf # FLOW GOES FROM RIGHT TO LEFT!!!
        return self._field_0("volVectorField", "U", "[0 1 -1 0 0 0 0]",
                            f"({init_u:.4f} 0 0)", self._patches("U"))

    def _p(self) -> str:
        return self._field_0("volScalarField", "p", "[1 -1 -2 0 0 0 0]",
                             f"{self.P_inf:.4f}", self._patches("p"))

    def _T(self) -> str:
        return self._field_0("volScalarField", "T", "[0 0 0 1 0 0 0]",
                             f"{self.T_inf:.4f}", self._patches("T"))

    def _rho(self) -> str:
        return self._field_0("volScalarField", "rho", "[1 -3 0 0 0 0 0]",
                             f"{self.rho_inf:.6f}", self._patches("rho"))

    def _h(self) -> str:
        return self._field_0("volScalarField", "h", "[0 2 -2 0 0 0 0]",
                             f"{CP * self.T_inf:.4f}", self._patches("h"))


if __name__ == "__main__":

    
    from cfd_setup.onshape.api import *
    from data.links import *
    from cfd_setup.mesh.div_single import *
    from cfd_setup.mesh.dri_module import *

    api = OnshapeAPI(DRI_MODULE_LINK, DRI_MODULE_FILE)

    cfg = OpenFOAMConfig(
        
        mesh           = DRIModuleMesh(api.get_evaluated_variables_df()),
        filepath       = "runs/dri_module_scale3",
        mach           = 5,
        altitude       = 30000,
        max_delta_t    = 1e-7,
        write_interval = 1e-4,
        end_time       = 0.010,
        scale          = 3
    )

    case = InviscidCase(cfg)
    case.write()