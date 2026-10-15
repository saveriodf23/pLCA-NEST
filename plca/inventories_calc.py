# Derived from LCA4DHC (RUN.ipynb (running the energy-system notebooks)) -
# Copyright 2026 Kevin Autelitano and Jacopo Famiglietti, licensed under the
# Apache License 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module;
# input validation added; rewritten to compute every energy system's inventory
# in one call.

"""
inventories_calc.py - compute every technology's inventory, once per run.

For each technology in plca.config.SYSTEMS whose worksheet is present, calls
energy_systems.<module>.compute() and collects the result (activity_data, sf,
replacements, bd_names, bd_areas; see energy_systems/__init__.py). No
Brightway work happens here; plca/lca_model.py takes it from there.
"""

import importlib

from . import config


def compute_all(sc, eol, systems=None, verbose=True):
    """Compute the inventory of every technology present in the scenario.

    A technology whose worksheet is missing is absent from the result.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open.
    eol : plca.eol.EolParameters
        End-of-life parameters.
    systems : list of str, optional
        Registry keys to compute; defaults to all of config.SYSTEMS.
    verbose : bool, default True
        Print one line per technology.

    Returns
    -------
    dict
        {registry key: inventory dict}
    """
    wanted = list(config.SYSTEMS) if systems is None else list(systems)

    inventories = {}
    computed = {}                 # energy_systems module name -> what it returned

    for system in wanted:
        entry = config.SYSTEMS[system]
        sheet = entry["sheet"]

        if not sheet or not sc.has_sheet(sheet):
            if verbose:
                print(f"Sheet '{sheet}' not found. Skipping {system}.")
            continue

        module_name = entry["module"]
        if module_name in computed:
            # Geothermal: one module, three registry entries, computed once.
            if verbose:
                print(f"Sheet '{sheet}' found. Reusing the {module_name} "
                      f"inventory for {system}.")
        else:
            if verbose:
                print(f"Sheet '{sheet}' found. Computing the {system} inventory.")
            computed[module_name] = compute_system(sc, eol, system)

        inventories[system] = _system_view(computed[module_name], system)

    if verbose:
        print(f"{len(inventories)} of {len(wanted)} system(s) present in "
              f"{len(computed)} inventory calculation(s).")
    return inventories


def compute_system(sc, eol, system):
    """Run one technology's compute() and return its result.

    Parameters
    ----------
    sc : plca.scenario.Scenario
    eol : plca.eol.EolParameters
    system : str
        Registry key in config.SYSTEMS.

    Returns
    -------
    dict
        What energy_systems.<module>.compute() returned.

    Raises
    ------
    RuntimeError
        If the computation fails, naming the system, file and worksheet.
    """
    entry = config.SYSTEMS[system]
    module = importlib.import_module(f"energy_systems.{entry['module']}")
    try:
        return module.compute(sc, eol)
    except Exception as error:
        raise RuntimeError(
            f"{system}: energy_systems/{entry['module']}.py failed on sheet "
            f"{entry['sheet']!r} of {sc.path} - {type(error).__name__}: {error}"
        ) from error


def _system_view(result, system):
    """One registry system's slice of its energy_systems module's result.

    For a composite (Geothermal) `sf` and `replacements` are dicts keyed by
    registry name; the system's own entry is picked out here (the parent has
    no replacement count of its own). activity_data, bd_names and bd_areas
    are shared by the three geothermal entries.
    """
    view = dict(result)

    # A composite must provide a scaling factor for every part.
    sf = result["sf"]
    if isinstance(sf, dict):
        if system not in sf:
            raise KeyError(
                f"{system}: no scaling factor - energy_systems returned SFs for "
                f"{sorted(sf)}"
            )
        view["sf"] = sf[system]

    # The geothermal parent has no replacement count (its B4 is its parts').
    replacements = result["replacements"]
    if isinstance(replacements, dict):
        view["replacements"] = replacements.get(system)

    return view
