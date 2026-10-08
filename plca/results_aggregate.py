"""
results_aggregate.py - roll the per-system frames up into the reported totals.

lca_model.calculate_all() returns one frame per (system, module), each holding
one technology's per-building, per-m2 scores. This module turns them into the
reported frames in four steps:

    per system   ->  per category      Heating = the sum over its technologies,
                                       Cooling likewise, Appliances is one
    per module   ->  whole life cycle  WLC = the sum over the 12 modules,
                                       WLC_noD = the same without D1 and D3
    per category ->  per building      Heating + Cooling (+ Appliances for B6
                                       and for WLC)
    per building ->  per neighbourhood an area-weighted mean over the buildings
                                       (see _hood_intensity)

Aggregate frames are indexed 0..n-1 in worksheet order, and each technology's
rows are matched to buildings by name (a technology's frame holds only the
buildings it serves). A building a technology does not serve contributes 0 in
the category step; later steps use plain addition, so a NaN there propagates.

Per-system frames come in two shapes:

    calculated   index = building names (sorted), 15 impact columns
    zero-filled  index = 0..n-1, 16 columns with 'Bd_Name' first - for a
                 technology whose worksheet is absent
"""

import pandas as pd

from . import config

# The impact columns every aggregate frame carries, in alphabetical order (the
# per-system frames use impact_methods.RESULT_COLUMNS order instead).
AGGREGATE_COLUMNS = ["A", "CC", "CCbio", "CCfossil", "CCluc", "EF", "EM",
                     "ERnren", "ET", "OD", "PENRT", "PM", "POF", "RUMM", "WU"]

# The three reported categories, and which systems each is the sum of (added in
# list order, see config.py).
CATEGORY_SYSTEMS = {
    "Heating": config.HEATING_SYSTEMS,
    "Cooling": config.COOLING_SYSTEMS,
    "Appliances": config.APPLIANCE_SYSTEMS,
}

# Which modules each category reports. No cooling machine has a module B1, so
# the cooling workbook has no B1 sheet.
HEATING_MODULES = list(config.WLC_MODULES)
COOLING_MODULES = [m for m in config.WLC_MODULES if m != "B1"]

# Category totals that are not simply "this module of every system in the
# category". Only the two heat pumps have a B1 (refrigerant leakage).
SOURCE_OVERRIDES = {
    ("Heating", "B1"): [("ElectricHeatPump", "B1"), ("GasEngineHeatPump", "B1")],
}


def sources(category, module):
    """List the per-system frames one category total is the sum of, in order.

    Parameters
    ----------
    category : str
        'Heating', 'Cooling' or 'Appliances'.
    module : str
        EN 15804 module code.

    Returns
    -------
    list of tuple
        (system, module) keys into what calculate_all() produced.
    """
    if (category, module) in SOURCE_OVERRIDES:
        return list(SOURCE_OVERRIDES[(category, module)])
    return [(system, module) for system in CATEGORY_SYSTEMS[category]]


def identity_columns(sc, category):
    """The leading, non-numeric columns of an aggregate frame.

    Building name and floor area, plus the heating and/or cooling system
    columns for the 'Heating', 'Cooling' and 'Total' categories.

    Parameters
    ----------
    sc : plca.scenario.Scenario
    category : str

    Returns
    -------
    pandas.DataFrame
        Indexed 0..n-1 in worksheet order.
    """
    columns = {"Bd_Name": sc.bd_names, "Bd_Area": sc.bd_areas}
    if category in ("Heating", "Total"):
        columns["Heating Energy Systems"] = sc.heating_systems
    if category in ("Cooling", "Total"):
        columns["Cooling Energy Systems"] = sc.cooling_systems
    return pd.DataFrame(columns)


def _aligned(frame, bd_names):
    """Line one technology's frame up with the scenario's building list.

    Matches by building name; buildings the technology does not serve become
    0.0. Accepts both frame shapes (see the module docstring).
    """
    if "Bd_Name" in frame.columns:
        frame = frame.set_index("Bd_Name")
    aligned = frame.reindex(list(bd_names))[AGGREGATE_COLUMNS].fillna(0.0)
    # Back to positional row labels, so that it adds onto the identity frame.
    aligned.index = pd.RangeIndex(len(aligned))
    return aligned


def category_module(sc, results, category, module):
    """Sum one module of one category over that category's technologies.

    Parameters
    ----------
    sc : plca.scenario.Scenario
    results : dict
        {(system, module): DataFrame}, from lca_model.calculate_all().
    category : str
    module : str

    Returns
    -------
    pandas.DataFrame
        Identity columns plus AGGREGATE_COLUMNS, one row per building.

    Raises
    ------
    KeyError
        If a source frame is missing.
    """
    frame = identity_columns(sc, category)
    total = pd.DataFrame(0.0, index=frame.index, columns=AGGREGATE_COLUMNS)
    for key in sources(category, module):
        if key not in results:
            raise KeyError(
                f"no result frame for system {key[0]!r} module {key[1]!r}; "
                f"calculate_all() produces one for every system in "
                f"config.SYSTEMS, zero-filled when its worksheet is missing")
        total = total.add(_aligned(results[key], sc.bd_names))
    return pd.concat([frame, total], axis=1)


def appliances(sc, results):
    """The appliances frame: the appliance results merged onto the building list.

    Unlike the other aggregates it keeps impact_methods.RESULT_COLUMNS order,
    and a building without an appliance result stays NaN.

    Parameters
    ----------
    sc : plca.scenario.Scenario
    results : dict
        {(system, module): DataFrame}, from lca_model.calculate_all().

    Returns
    -------
    pandas.DataFrame
    """
    identity = pd.DataFrame({"Bd_Name": sc.bd_names, "Bd_Area": sc.bd_areas})
    frame = results[("Appliances", "B6")]
    if "Bd_Name" in frame.columns:
        # zero-filled shape: names in a column, positional index
        return identity.merge(frame, left_on="Bd_Name", right_on="Bd_Name",
                              how="left")
    return identity.merge(frame, left_on="Bd_Name", right_index=True, how="left")


def whole_life_cycle(sc, frames, category, modules):
    """WLC or WLC_noD for one category: the sum over its module frames.

    WLC covers all twelve modules; WLC_noD leaves out D1 and D3, the credits
    beyond the system boundary that EN 15804 reports separately.

    Parameters
    ----------
    sc : plca.scenario.Scenario
    frames : dict
        Aggregate frames built so far, {(category, module): DataFrame}.
    category : str
    modules : list of str
        Modules to sum.

    Returns
    -------
    pandas.DataFrame
    """
    total = frames[(category, modules[0])][AGGREGATE_COLUMNS]
    for module in modules[1:]:
        total = total.add(frames[(category, module)][AGGREGATE_COLUMNS])
    return pd.concat([identity_columns(sc, category), total], axis=1)


def building_module(sc, frames, module):
    """One module summed over everything a building has.

    Heating + cooling, except B1 (heating only) and B6 (heating + cooling +
    appliances, the only module appliances have).

    Parameters
    ----------
    sc : plca.scenario.Scenario
    frames : dict
        Aggregate frames built so far.
    module : str

    Returns
    -------
    pandas.DataFrame
    """
    total = frames[("Heating", module)][AGGREGATE_COLUMNS]
    if module in COOLING_MODULES:
        total = total.add(frames[("Cooling", module)][AGGREGATE_COLUMNS])
    if module == "B6":
        total = total.add(frames[("Appliances", "B6")][AGGREGATE_COLUMNS])
    return pd.concat([identity_columns(sc, "Total"), total], axis=1)


def building_total(sc, frames, with_d):
    """The whole-life-cycle total for each building: heating + cooling + appliances.

    Appliances have no module D, so their WLC frame is added to both totals.

    Parameters
    ----------
    sc : plca.scenario.Scenario
    frames : dict
        Aggregate frames built so far.
    with_d : bool
        True for WLC, False for WLC_noD.

    Returns
    -------
    pandas.DataFrame
    """
    which = "WLC" if with_d else "WLC_noD"
    total = frames[("Heating", which)][AGGREGATE_COLUMNS]
    total = total.add(frames[("Cooling", which)][AGGREGATE_COLUMNS])
    total = total.add(frames[("Appliances", "WLC")][AGGREGATE_COLUMNS])
    return pd.concat([identity_columns(sc, "Total"), total], axis=1)


def _hood_intensity(frame, areas):
    """The neighbourhood intensity: sum(x_i * a_i) / sum(a_i).

    Each row of `frame` is an impact per m2 of one building, so weighting by
    floor area gives the neighbourhood's total impact per m2 of its total
    useful floor area - the functional unit. (pLCA-NEST v1.0 used a plain
    column sum instead.)

    Parameters
    ----------
    frame : pandas.DataFrame
        Per-building results, row for row with `areas`.
    areas : array-like of float
        Building floor areas [m2].

    Returns
    -------
    pandas.Series
        One value per impact category.
    """
    assert len(frame) == len(areas), (
        f"frame has {len(frame)} rows, areas has {len(areas)}; "
        f"they must correspond row for row")
    a = pd.Series(areas, index=frame.index, dtype=float)
    return frame[AGGREGATE_COLUMNS].mul(a, axis=0).sum(axis=0) / a.sum()


def neighbourhood_total(sc, frames, with_d):
    """The neighbourhood WLC or WLC_noD: one value per impact category.

    The area-weighted mean of the per-building totals (see _hood_intensity).

    Parameters
    ----------
    sc : plca.scenario.Scenario
    frames : dict
        Aggregate frames built so far.
    with_d : bool
        True for WLC, False for WLC_noD.

    Returns
    -------
    pandas.Series
    """
    key = ("Total", "WLC" if with_d else "WLC_noD")
    return _hood_intensity(frames[key], sc.bd_areas)


def neighbourhood_by_function(sc, frames, with_d):
    """Neighbourhood WLC or WLC_noD, kept separate for heating, cooling and appliances.

    The same area-weighted mean as neighbourhood_total(), applied to each
    category's own total. Appliances have no module D, so their WLC frame is
    used for both.

    Parameters
    ----------
    sc : plca.scenario.Scenario
    frames : dict
        Aggregate frames built so far.
    with_d : bool
        True for WLC, False for WLC_noD.

    Returns
    -------
    pandas.DataFrame
        Rows 'Heating', 'Cooling', 'Appliances'.
    """
    which = "WLC" if with_d else "WLC_noD"
    rows = {
        "Heating": _hood_intensity(frames[("Heating", which)], sc.bd_areas),
        "Cooling": _hood_intensity(frames[("Cooling", which)], sc.bd_areas),
        "Appliances": _hood_intensity(frames[("Appliances", "WLC")], sc.bd_areas),
    }
    return pd.DataFrame(rows).T


def neighbourhood_module(sc, frames, module):
    """One module's neighbourhood total: the area-weighted mean of ('Total', module).

    Parameters
    ----------
    sc : plca.scenario.Scenario
    frames : dict
        Aggregate frames built so far.
    module : str

    Returns
    -------
    pandas.Series
    """
    return _hood_intensity(frames[("Total", module)], sc.bd_areas)


def original_name(category, module):
    """Legacy variable name of an aggregate frame, e.g. 'dfresults_A13_Heating'.

    Used by plca.validation to name frames the way pLCA-NEST v1.0 did.
    """
    if category == "Neighbourhood":
        return f"dfresults_{module}_hood"
    if category == "Total":
        return f"dfresults_{module}"
    return f"dfresults_{module}_{category}"


def aggregate_all(sc, results, verbose=True):
    """Build every reported aggregate from the per-system results.

    The order is fixed: whole-life-cycle totals read the module frames,
    per-building totals read the category frames, and the neighbourhood
    totals read the per-building ones.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Provides the building list, areas and energy-system columns.
    results : dict
        {(system, module): DataFrame}, from lca_model.calculate_all().
    verbose : bool, default True
        Print a summary.

    Returns
    -------
    dict
        {(category, module): frame}:

        ('Heating', m)       12 modules, plus 'WLC' and 'WLC_noD'
        ('Cooling', m)       11 modules (no B1), plus 'WLC' and 'WLC_noD'
        ('Appliances', 'B6') and ('Appliances', 'WLC')
        ('Total', m)         12 modules, plus 'WLC' and 'WLC_noD'
        ('Neighbourhood', m) 12 modules, plus 'WLC' and 'WLC_noD' - Series,
                             one value per impact category
        ('Neighbourhood_ByFunction', 'WLC'/'WLC_noD') - frames with one row
                             each for Heating, Cooling and Appliances
    """
    frames = {}

    # --- each category, module by module -------------------------------------
    for module in HEATING_MODULES:
        frames[("Heating", module)] = category_module(sc, results, "Heating",
                                                      module)
    for module in COOLING_MODULES:
        frames[("Cooling", module)] = category_module(sc, results, "Cooling",
                                                      module)

    # --- appliances, merged rather than summed ----------------------------------
    frames[("Appliances", "B6")] = appliances(sc, results)
    # A copy, not the same object: results_export renames the columns of both
    # in place.
    frames[("Appliances", "WLC")] = frames[("Appliances", "B6")].copy()

    # --- the whole-life-cycle sums for each category -------------------------
    for category, modules in (("Heating", HEATING_MODULES),
                              ("Cooling", COOLING_MODULES)):
        frames[(category, "WLC")] = whole_life_cycle(
            sc, frames, category, modules)
        frames[(category, "WLC_noD")] = whole_life_cycle(
            sc, frames, category,
            [m for m in modules if m in config.WLC_NO_D_MODULES])

    # --- per building, heating + cooling (+ appliances) ----------------------
    for module in HEATING_MODULES:
        frames[("Total", module)] = building_module(sc, frames, module)
    frames[("Total", "WLC")] = building_total(sc, frames, with_d=True)
    frames[("Total", "WLC_noD")] = building_total(sc, frames, with_d=False)

    # --- per neighbourhood -----------------------------------------------------
    frames[("Neighbourhood", "WLC")] = neighbourhood_total(sc, frames, with_d=True)
    frames[("Neighbourhood", "WLC_noD")] = neighbourhood_total(sc, frames,
                                                               with_d=False)
    for module in HEATING_MODULES:
        frames[("Neighbourhood", module)] = neighbourhood_module(sc, frames, module)
    frames[("Neighbourhood_ByFunction", "WLC")] = neighbourhood_by_function(
        sc, frames, with_d=True)
    frames[("Neighbourhood_ByFunction", "WLC_noD")] = neighbourhood_by_function(
        sc, frames, with_d=False)

    if verbose:
        print(f"{len(frames)} aggregate frame(s) from "
              f"{len(results)} per-system frame(s).")
    return frames
