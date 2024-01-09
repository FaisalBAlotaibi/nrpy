"""
Module containing functions that auto-generate a schedule.ccl file for an input thorn.

Author: Zachariah B. Etienne
        zachetie **at** gmail **dot* com
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path

import nrpy.c_function as cfc


class ScheduleCCL:
    """
    Class representing a ScheduleCCL object.

    :param function_name: The name of the function.
    :param schedule_bin: The scheduling bin.
    :param entry: The scheduling entry.
    :param has_been_output: Flag indicating whether this schedule entry has already been output.
    """

    def __init__(
        self,
        function_name: str,
        schedule_bin: str,
        entry: str,
    ) -> None:
        """
        Initialize a ScheduleCCL object.

        :param function_name: The name of the function.
        :param schedule_bin: The scheduling bin.
        :param entry: The scheduling entry.
        """
        self.function_name = function_name
        self.schedule_bin = schedule_bin
        self.entry = entry
        self.has_been_output = False


def construct_schedule_ccl(
    project_dir: str,
    thorn_name: str,
    STORAGE: str,
    extra_schedule_bins_entries: Optional[List[Tuple[str, str]]] = None,
) -> None:
    """
    Construct the ScheduleCCL string based on its properties.

    :param project_dir: The directory of the project.
    :param thorn_name: The name of the thorn.
    :param STORAGE: Storage information.
    :param extra_schedule_bins_entries: Additional scheduling bins and entries.
    :return: None
    """
    outstr = """# This schedule.ccl file was automatically generated by NRPy+.
#   You are advised against modifying it directly; instead
#   modify the Python code that generates it.
"""
    outstr += f"""\n##################################################
# Step 0: Allocate memory for gridfunctions, using the STORAGE: keyword.
{STORAGE}
"""
    schedule_ccl_dict: Dict[str, List[ScheduleCCL]] = {}
    for function_name, item in cfc.CFunction_dict.items():
        if item.ET_schedule_bins_entries:
            for schedule_bin, entry in item.ET_schedule_bins_entries:
                schedule_ccl_dict.setdefault(item.ET_thorn_name, []).append(
                    ScheduleCCL(
                        function_name=function_name,
                        schedule_bin=schedule_bin,
                        entry=entry,
                    )
                )
        else:
            print(
                f"Warning: No schedule.ccl information (ET_schedule_bins_entries) included for: {function_name}."
            )
    if extra_schedule_bins_entries:
        for schedule_bin, entry in extra_schedule_bins_entries:
            schedule_ccl_dict[thorn_name] += [
                ScheduleCCL(function_name="", schedule_bin=schedule_bin, entry=entry)
            ]

    step = 1
    for schedule_bin in [
        "STARTUP",
        "BASEGRID",
        "CCTK_INITIAL",
        "ODESolvers_RHS",
        "ODESolvers_PostStep",
    ]:
        already_output_header = False
        for sccl in schedule_ccl_dict[thorn_name]:
            if (
                sccl.schedule_bin.upper() == schedule_bin.upper()
                and not sccl.has_been_output
            ):
                if not already_output_header:
                    outstr += f"""\n##################################################
# Step {step}: Schedule functions in the {schedule_bin} scheduling bin.
"""
                    already_output_header = True
                    step += 1
                outstr += sccl.entry.replace("FUNC_NAME", sccl.function_name)
                sccl.has_been_output = True

    for sccl in schedule_ccl_dict[thorn_name]:
        if not sccl.has_been_output:
            outstr += f"""\n##################################################
# Step {step}: Schedule functions in the remaining scheduling bins.
"""
            outstr += sccl.entry.replace("FUNC_NAME", sccl.function_name)

    output_Path = Path(project_dir) / thorn_name
    output_Path.mkdir(parents=True, exist_ok=True)
    with open(output_Path / "schedule.ccl", "w", encoding="utf-8") as file:
        file.write(outstr)
