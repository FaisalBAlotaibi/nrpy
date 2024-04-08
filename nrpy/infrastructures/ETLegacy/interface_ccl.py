"""
Module for constructing interface.ccl for Cactus thorns.

Author: Zachariah B. Etienne
        zachetie **at** gmail **dot* com
        Samuel Cupp
"""

from pathlib import Path
import nrpy.grid as gri
from nrpy.helpers.conditional_file_updater import ConditionalFileUpdater


def construct_interface_ccl(
    project_dir: str,
    thorn_name: str,
    inherits: str,
    USES_INCLUDEs: str,
    is_evol_thorn: bool = False,
    enable_NewRad: bool = False,
) -> None:
    """
    Generate `interface.ccl` file required for the specified Thorn.

    :param project_dir: The directory where the project is located.
    :param thorn_name: The name of the thorn for which the interface.ccl file is generated.
    :param inherits: Thorn names from which this thorn inherits.
    :param USES_INCLUDEs: Additional includes or functions required by the thorn.
    :param is_evol_thorn: Flag indicating if the thorn is an evolution thorn. Defaults to False.
    :param enable_NewRad: Flag to enable NewRad boundary conditions. Defaults to False.
    """
    outstr = f"""
# This interface.ccl file was automatically generated by NRPy+.
#   You are advised against modifying it directly; instead
#   modify the Python code that generates it.

# With "implements", we give our thorn its unique name.
implements: {thorn_name}

# By "inheriting" other thorns, we tell the Toolkit that we
#   will rely on variables/function that exist within those
#   functions.
inherits: {inherits}

# Needed functions and #include's:
{USES_INCLUDEs}
"""

    if is_evol_thorn:
        outstr += """
# Needed Method of Lines function
CCTK_INT FUNCTION MoLRegisterEvolvedGroup(CCTK_INT IN EvolvedIndex, CCTK_INT IN RHSIndex)
REQUIRES FUNCTION MoLRegisterEvolvedGroup

# Needed Boundary Conditions function
CCTK_INT FUNCTION GetBoundarySpecification(CCTK_INT IN size, CCTK_INT OUT ARRAY nboundaryzones, CCTK_INT OUT ARRAY is_internal, CCTK_INT OUT ARRAY is_staggered, CCTK_INT OUT ARRAY shiftout)
USES FUNCTION GetBoundarySpecification

CCTK_INT FUNCTION SymmetryTableHandleForGrid(CCTK_POINTER_TO_CONST IN cctkGH)
USES FUNCTION SymmetryTableHandleForGrid

CCTK_INT FUNCTION Boundary_SelectVarForBC(CCTK_POINTER_TO_CONST IN GH, CCTK_INT IN faces, CCTK_INT IN boundary_width, CCTK_INT IN table_handle, CCTK_STRING IN var_name, CCTK_STRING IN bc_name)
USES FUNCTION Boundary_SelectVarForBC

CCTK_INT FUNCTION Driver_SelectVarForBC(CCTK_POINTER_TO_CONST IN GH, CCTK_INT IN faces, CCTK_INT IN boundary_width, CCTK_INT IN table_handle, CCTK_STRING IN group_name, CCTK_STRING IN bc_name)
USES FUNCTION Driver_SelectVarForBC
"""

    if enable_NewRad:
        outstr += r"""
# Needed to convert ADM initial data into BSSN initial data (Gamma extrapolation)
CCTK_INT FUNCTION ExtrapolateGammas(CCTK_POINTER_TO_CONST IN cctkGH, CCTK_REAL ARRAY INOUT var)
REQUIRES FUNCTION ExtrapolateGammas

# Needed for EinsteinEvolve/NewRad outer boundary condition driver:
CCTK_INT FUNCTION                         \
    NewRad_Apply                          \
        (CCTK_POINTER_TO_CONST IN cctkGH, \
         CCTK_REAL ARRAY IN var,          \
         CCTK_REAL ARRAY INOUT rhs,       \
         CCTK_REAL IN var0,               \
         CCTK_REAL IN v0,                 \
         CCTK_INT IN radpower)
REQUIRES FUNCTION NewRad_Apply
"""

    outstr += """
# FIXME: add info for symmetry conditions:
#    https://einsteintoolkit.org/thornguide/CactusBase/SymBase/documentation.html

# Tell the Toolkit that we want all gridfunctions
#    to be visible to other thorns by using
#    the keyword "public". Note that declaring these
#    gridfunctions *does not* allocate memory for them;
#    that is done by the schedule.ccl file.

public:
"""

    (
        evolved_variables_list,
        auxiliary_variables_list,
        auxevol_variables_list,
    ) = gri.CarpetXGridFunction.gridfunction_lists()[0:3]

    if is_evol_thorn:
        if evolved_variables_list:
            # First, EVOL type:
            evol_gfs = ", ".join([f"{evol_gf}GF" for evol_gf in evolved_variables_list])
            outstr += f"""CCTK_REAL evol_variables type = GF Timelevels=3
{{
  {evol_gfs}
}} "Evolved gridfunctions."

"""

            # Second EVOL right-hand-sides
            rhs_gfs = ", ".join(
                [f"{evol_gf}_rhsGF" for evol_gf in evolved_variables_list]
            )
            outstr += f"""CCTK_REAL evol_variables_rhs type = GF Timelevels=1 TAGS='InterpNumTimelevels=1 prolongation="none" checkpoint="no"'
{{
  {rhs_gfs}
}} "Right-hand-side gridfunctions."

"""

            # Then AUXEVOL type:
            if auxevol_variables_list:
                auxevol_gfs = ", ".join(
                    [f"{auxevol_gf}GF" for auxevol_gf in auxevol_variables_list]
                )
                outstr += f"""CCTK_REAL auxevol_variables type = GF Timelevels=1 TAGS='InterpNumTimelevels=1 prolongation="none" checkpoint="no"'
{{
  {auxevol_gfs}
}} "Auxiliary gridfunctions needed for evaluating the RHSs."

"""

        # Then AUX type:
        if auxiliary_variables_list:
            aux_gfs = ", ".join([f"{aux_gf}GF" for aux_gf in auxiliary_variables_list])
            outstr += f"""CCTK_REAL aux_variables type = GF Timelevels=3
{{
  {aux_gfs}
}} "Auxiliary gridfunctions for e.g., diagnostics."

"""

    output_Path = Path(project_dir) / thorn_name
    output_Path.mkdir(parents=True, exist_ok=True)

    with ConditionalFileUpdater(
        output_Path / "interface.ccl", encoding="utf-8"
    ) as file:
        file.write(outstr)
