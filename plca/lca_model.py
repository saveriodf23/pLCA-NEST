"""
Build the scenario database and calculate its LCA results.

Each energy system contributes one group of activities per EN 15804 module,
with one activity per building. The file has two halves:

BUILD
    build_activities, wire_exchanges and add_production_exchange, driven by
    build_all. Creates nodes and edges; calculates nothing.
CALCULATE
    run_lca and the arithmetic around it (SF scaling, derived module B4, the
    D1/D3 replacement inclusion, composite systems), driven by calculate_all.

The per-technology exchange rows are data and live in plca/exchange_configs.py.

Brightway is imported inside the functions that need it, so this module can be
imported and tested without a Brightway project.
"""

import numpy as np
import pandas as pd

from . import config, exchange_configs

# Columns of the zero-filled frame used when a technology's worksheet is
# missing: 'Bd_Name' plus the 15 impact categories, in the order MultiLCA
# returns them. Must match impact_methods.RESULT_COLUMNS.
MISSING_SHEET_COLUMNS = ["Bd_Name", "PM", "A", "CCbio", "CCfossil", "CCluc", "CC",
                         "ERnren", "EF", "EM", "ET", "RUMM", "OD", "POF", "WU",
                         "PENRT"]


# ---------------------------------------------------------------------------
# BUILD - the nodes and edges of the scenario database
# ---------------------------------------------------------------------------

def build_activities(db, module, prefix, bd_names):
    """Create one activity per building for one (module, system) group.

    The activity code and name are the same string, e.g.
    'A13_Boiler_Bd2432709'.

    Parameters
    ----------
    db : bw2data.Database
        Registered, empty scenario database (see plca.scenario_db).
    module : str
        EN 15804 module code, e.g. 'A13'.
    prefix : str
        System prefix, ``config.SYSTEMS[key]['prefix']``, e.g. 'Boiler'.
    bd_names : list of str
        Buildings served by this technology, in worksheet order.

    Returns
    -------
    dict
        {building name: activity}

    Raises
    ------
    RuntimeError
        If an activity cannot be created, typically because two buildings in
        the worksheet share a name.
    """
    # A4 and C2: transport work; B6: kWh; all other modules: 'unit'.
    unit = config.unit_for(module)

    acts = {}
    for bd_name in bd_names:
        code = config.activity_code(module, prefix, bd_name)
        data = {
            "code": code,
            "name": code,
            "location": config.LOCATION,
            "unit": unit,
        }
        try:
            acts[bd_name] = db.new_activity(**data)
            acts[bd_name].save()
        except Exception as error:
            raise RuntimeError(
                f"could not create activity {code!r} in {db.name!r} - "
                f"{type(error).__name__}: {error}"
            ) from error
    return acts


def wire_exchanges(acts, module, prefix, activity_data, datasets, bd_names):
    """Attach one group's technosphere and biosphere exchanges.

    Groups with no rows in exchange_configs (e.g. a passive storage's B6) get
    no exchanges and score zero. Zero amounts are not written.

    Parameters
    ----------
    acts : dict
        {building name: activity}, from build_activities.
    module, prefix : str
        As in build_activities.
    activity_data : dict
        Inventory quantities for this system, from plca.inventories_calc.
    datasets : dict
        {'EF_...': node}, from plca.ecoinvent_datasets.load().
    bd_names : list of str
        Buildings, in the order the activities were created.

    Returns
    -------
    int
        Number of exchanges written.

    Raises
    ------
    KeyError
        If a row refers to a missing inventory quantity or background dataset.
    """
    rows = exchange_configs.EXCHANGES.get((prefix, module))
    if not rows:
        return 0

    # Resolve names once per group. Each amount is in the unit of the dataset
    # it points at.
    resolved = []
    for ef_name, quantity_name, exchange_type in rows:
        if quantity_name not in activity_data:
            raise KeyError(
                f"{prefix} {module}: the exchange rows want {quantity_name!r}, "
                f"which the technology's energy_systems module did not "
                f"produce - check the name in plca/exchange_configs.py"
            )
        if ef_name not in datasets:
            raise KeyError(
                f"{prefix} {module}: the exchange rows want the background "
                f"dataset {ef_name!r}, which ecoinvent_datasets.load() did not "
                f"return"
            )
        # atleast_1d lets a scalar quantity be indexed per building. Known
        # limitation: a scalar only covers a technology with one building.
        values = np.atleast_1d(activity_data[quantity_name])
        resolved.append((datasets[ef_name].key, values, exchange_type))

    written = 0
    for i, bd_name in enumerate(bd_names):
        for input_key, values, exchange_type in resolved:
            amount = float(values[i])
            # NaN is not zero, so it gets through and Brightway reports
            # 'Invalid amount in exchange'.
            if amount == 0:
                continue
            acts[bd_name].new_exchange(
                amount=amount,
                type=exchange_type,
                input=input_key,
            ).save()
            written += 1
    return written


def add_production_exchange(acts):
    """Give each activity a production exchange of one unit of itself.

    This is the activity's reference product (the diagonal of the
    technosphere matrix). The functional unit, 1 / floor area, is applied
    later in functional_units.

    Parameters
    ----------
    acts : dict
        {building name: activity}
    """
    for act in acts.values():
        act.new_exchange(
            input=act.key,
            output=act.key,
            amount=1,
            type="production",
        ).save()


def build_group(db, system, module, inventory, datasets):
    """Build one (system, module) group: activities, exchanges, production.

    Parameters
    ----------
    db : bw2data.Database
        Scenario database.
    system : str
        Registry key in config.SYSTEMS.
    module : str
        EN 15804 module code.
    inventory : dict
        This system's entry from plca.inventories_calc.compute_all().
    datasets : dict
        {'EF_...': node}, from plca.ecoinvent_datasets.load().

    Returns
    -------
    acts : dict
        {building name: activity}
    written : int
        Number of exchanges written.
    """
    prefix = config.SYSTEMS[system]["prefix"]
    bd_names = inventory["bd_names"]

    acts = build_activities(db, module, prefix, bd_names)
    written = wire_exchanges(acts, module, prefix, inventory["activity_data"],
                             datasets, bd_names)
    add_production_exchange(acts)
    return acts, written


def build_all(db, inventories, datasets, verbose=True):
    """Build every group of every technology present in the scenario.

    Technologies missing from `inventories` (no worksheet) are skipped. The
    database is processed at the end, ready for calculation.

    Parameters
    ----------
    db : bw2data.Database
        Registered, empty scenario database.
    inventories : dict
        Output of plca.inventories_calc.compute_all().
    datasets : dict
        {'EF_...': node}, from plca.ecoinvent_datasets.load().
    verbose : bool, default True
        Print progress.

    Returns
    -------
    dict
        {(system, module): {building name: activity}}, keyed by the
        config.SYSTEMS registry key.
    """
    groups = {}
    exchanges = 0
    for system, inventory in inventories.items():
        for module in config.SYSTEMS[system]["modules"]:
            acts, written = build_group(db, system, module, inventory, datasets)
            groups[(system, module)] = acts
            exchanges += written
        if verbose:
            print(f"{system}: {len(config.SYSTEMS[system]['modules'])} module(s) built")

    if verbose:
        activities = sum(len(a) for a in groups.values())
        print(f"{len(groups)} activity group(s), {activities} activity(ies), "
              f"{exchanges} exchange(s).")

    # Process the database once the graph is complete. Otherwise its `depends`
    # stays empty, bd.get_multilca_data_objs returns the scenario datapackage
    # alone (no ecoinvent, no biosphere) and the first lci() raises
    # NonsquareTechnosphere. Must stay AFTER the build loop: building again
    # would mark the database dirty.
    db.process()
    return groups


# ---------------------------------------------------------------------------
# CALCULATE - the LCA and the arithmetic around it
# ---------------------------------------------------------------------------

def functional_units(acts, bd_names, bd_areas):
    """Functional units: 1 m2 of each building's net floor area.

    Every activity produces one unit of itself, so a demand of 1 / area gives
    the building's result per m2, which makes buildings of different sizes
    comparable.

    Parameters
    ----------
    acts : dict
        {building name: activity}, from build_activities.
    bd_names : list of str
        Buildings, in worksheet order.
    bd_areas : array-like of float
        Net floor areas [m2], in the same order.

    Returns
    -------
    dict
        {building name: {activity id: 1 / area}}. Brightway 2.5's MultiLCA
        requires string labels and integer node ids.
    """
    return {bd_name: {acts[bd_name].id: 1 / bd_area}
            for bd_name, bd_area in zip(bd_names, bd_areas)}


def shared_inputs(methods, sample_units):
    """Build the inputs shared by every LCA of the scenario, once.

    The datapackages depend only on the database the demands live in, and all
    groups live in the same scenario database. Must be called after
    build_all(). Building everything first and calculating afterwards gives
    the same results as interleaving the two, because scenario activities only
    consume ecoinvent and biosphere flows.

    Parameters
    ----------
    methods : dict
        {short code: method tuple}, from impact_methods.load().
    sample_units : dict
        Functional units of any group; only their database is read.

    Returns
    -------
    dict
        Keys 'data_objs', 'method_config' and 'method_lookup'.
    """
    # Imported here rather than at the top of the file: see the module docstring.
    import bw2data as bd

    method_config = {"impact_categories": list(methods.values())}
    data_objs = bd.get_multilca_data_objs(functional_units=sample_units,
                                          method_config=method_config)
    # Maps method tuples back to short codes ('CC', 'A', ...).
    method_lookup = {v: k for k, v in methods.items()}
    return {"data_objs": data_objs,
            "method_config": method_config,
            "method_lookup": method_lookup}


def run_lca(acts, bd_names, bd_areas, shared):
    """Calculate one (system, module) group: 15 impact scores per building.

    Parameters
    ----------
    acts : dict
        {building name: activity} for this group.
    bd_names : list of str
        Buildings, in worksheet order.
    bd_areas : array-like of float
        Net floor areas [m2], in the same order.
    shared : dict
        Output of shared_inputs().

    Returns
    -------
    pandas.DataFrame
        Unscaled results; SF is applied by the caller. Rows are buildings
        sorted by name (not in worksheet order); columns are the 15 impact
        categories in impact_methods.RESULT_COLUMNS order.
    """
    # Imported here rather than at the top of the file: see the module docstring.
    import bw2calc as bc

    units = functional_units(acts, bd_names, bd_areas)
    mlca = bc.MultiLCA(demands=units,
                       method_config=shared["method_config"],
                       data_objs=shared["data_objs"])
    mlca.lci()
    mlca.lcia()

    # Keep only the scores: the MultiLCA object holds one inventory matrix
    # per building, so dropping it keeps peak memory to one group.
    scores = mlca.scores
    del mlca

    # {(method, building): score} -> buildings x methods
    results = pd.DataFrame.from_dict(scores, orient="index")
    results.index = pd.MultiIndex.from_tuples(results.index,
                                              names=["Column", "Row"])
    results = results.unstack(level=0)
    # Drop the '0' the single value column was named, leaving the method tuples.
    results.columns = results.columns.droplevel(0)
    results.rename(columns=shared["method_lookup"], inplace=True)
    return results


def by_building(values, bd_names):
    """Turn a per-building factor into a Series indexed by building name.

    Inventory factors (SF, NumberReplacements) are arrays in worksheet order,
    while result frames are sorted by building name. Indexing the factor by
    name makes ``.mul(..., axis=0)`` align by label instead of position.

    Parameters
    ----------
    values : array-like, scalar or None
        The inventory's 'sf' or 'replacements' for one system. Scalars and
        None are returned unchanged.
    bd_names : list of str
        Buildings, in the order of `values` (worksheet order).

    Returns
    -------
    pandas.Series, scalar or None
    """
    if values is None or np.ndim(values) == 0:
        return values
    return pd.Series(np.asarray(values), index=list(bd_names))


def mul_by_building(frame, factor):
    """Multiply `frame` by a per-building `factor`, aligned by building name.

    Shared by scale(), derive_b4() and include_b4().

    Parameters
    ----------
    frame : pandas.DataFrame
        Results indexed by building name.
    factor : pandas.Series or scalar
        Output of by_building().

    Returns
    -------
    pandas.DataFrame

    Raises
    ------
    KeyError
        If the factor's labels do not match the frame's rows, which would
        otherwise silently produce NaN.
    """
    if isinstance(factor, pd.Series):
        unlabelled = frame.index.difference(factor.index)
        unmatched = factor.index.difference(frame.index)
        if len(unlabelled) or len(unmatched):
            raise KeyError(
                f"per-building factor does not line up with the result frame: "
                f"{list(unlabelled)[:3]} have no factor and {list(unmatched)[:3]} "
                f"have no row (frame has {len(frame.index)} rows, factor has "
                f"{len(factor.index)} entries). A zero-filled frame carries its "
                f"names in a 'Bd_Name' column rather than in the index - see "
                f"empty_results()")
    return frame.mul(factor, axis=0)


def scale(results, sf):
    """Scale a module's results to the study period: SF = RSP / Lifespan.

    Applied to every module except B6 (config.UNSCALED_MODULES), whose
    operational energy already covers the whole study period.

    Parameters
    ----------
    results : pandas.DataFrame
        Unscaled results from run_lca().
    sf : pandas.Series or scalar
        Scaling factor per building, from by_building().

    Returns
    -------
    pandas.DataFrame
    """
    return mul_by_building(results, sf)


def empty_results(bd_names):
    """Zero-filled results for a technology whose worksheet is missing.

    The shape differs from a calculated frame, and the aggregation relies on
    it (it merges on 'Bd_Name')::

        calculated   index = building names (sorted), 15 impact columns
        zero-filled  index = 0..n-1, 16 columns with 'Bd_Name' first

    Parameters
    ----------
    bd_names : list of str
        Every building in the scenario (Scenario.bd_names), so n is the whole
        scenario, not the buildings served by this technology.

    Returns
    -------
    pandas.DataFrame
    """
    results = pd.DataFrame(0, index=range(len(bd_names)),
                           columns=MISSING_SHEET_COLUMNS)
    results["Bd_Name"] = bd_names
    return results


def derive_b4(results, system, replacements):
    """Derive module B4 (replacement) from other modules; no LCA is run.

        B4 = (A13 + A4 + C3 + C4) * NumberReplacements

    Each replacement repeats manufacture (A1-3), delivery (A4) and end of life
    (C3, C4). Missing source modules count as zero.
    NumberReplacements = max(RSP / Lifespan - 1, 0) (pro-rated), so B4 is
    zero whenever RSP <= Lifespan.

    Parameters
    ----------
    results : dict
        Frames calculated so far, {(system, module): DataFrame}.
    system : str
        Registry key in config.SYSTEMS.
    replacements : pandas.Series or scalar
        Replacements per building, from by_building().

    Returns
    -------
    pandas.DataFrame

    Raises
    ------
    KeyError
        If one of the source modules was not calculated.
    """
    missing = [m for m in config.B4_SOURCE_MODULES if (system, m) not in results]
    if missing:
        raise KeyError(
            f"{system}: B4 needs {list(config.B4_SOURCE_MODULES)} and "
            f"{missing} were not calculated - config.SYSTEMS says this system "
            f"has {config.SYSTEMS[system]['modules']}"
        )

    total = None
    for module in config.B4_SOURCE_MODULES:
        frame = results[(system, module)]
        total = frame if total is None else total.add(frame, fill_value=0)
    return mul_by_building(total, replacements)


def include_b4(results, replacements):
    """Add the replaced units' share to a module D credit.

        D = D * (1 + NumberReplacements)

    Used for D1 (exported secondary materials) and D3 (energy recovered from
    incineration): each replaced unit reaches end of life too. Must be applied
    after SF scaling and after B4 is derived.

    Parameters
    ----------
    results : pandas.DataFrame
        Scaled D1 or D3 results.
    replacements : pandas.Series or scalar
        Replacements per building, from by_building().

    Returns
    -------
    pandas.DataFrame
    """
    return results.add(mul_by_building(results, replacements))


def missing_sheet_modules(system):
    """List the modules to zero-fill for a technology with no worksheet.

    Its own modules plus B4, except for:

    - Appliances: no B4, there is nothing to replace.
    - Parts of a composite system (the geothermal children): no B4; the parent
      gets one instead.

    Parameters
    ----------
    system : str
        Registry key in config.SYSTEMS.

    Returns
    -------
    list of str
    """
    modules = list(config.SYSTEMS[system]["modules"])
    parts = {part for spec in config.COMPOSITE_SYSTEMS.values()
             for part in spec["parts"]}

    # For a composite parent the B4 source modules belong to its parts, so
    # check the composite's module list rather than the parent's own.
    sources = set(config.COMPOSITE_SYSTEMS[system]["modules"]
                  if system in config.COMPOSITE_SYSTEMS else modules)
    if system not in parts and set(config.B4_SOURCE_MODULES) <= sources:
        modules.append("B4")
    return modules


def assemble_composite(results, parent, present):
    """Sum a composite system's parts into its parent, module by module.

    Geothermal is currently the only composite::

        Geothermal = Geothermal_DeepWell + Geothermal_HeatExchanger
                     for A13, A4, A5, B4, C2, C3, C4, D1, D3

    The deep well (50 years) and the heat exchanger (15 years) are scaled and
    replaced independently; B2 and B6 are calculated directly on the parent.
    Must run last, after the D1/D3 inclusion. Modifies `results` in place.

    Parameters
    ----------
    results : dict
        {(system, module): DataFrame}
    parent : str
        Key in config.COMPOSITE_SYSTEMS.
    present : bool
        Whether the technology's worksheet is in the workbook.
    """
    spec = config.COMPOSITE_SYSTEMS[parent]
    modules = list(spec["modules"])

    if not present:
        # The parent's B4 is already zero-filled (see missing_sheet_modules).
        modules.remove("B4")

    for module in modules:
        total = None
        for part in spec["parts"]:
            frame = results[(part, module)]
            total = frame if total is None else total.add(frame)
        # Zero-filled frames carry a 'Bd_Name' column, which .add() would
        # concatenate, so take the names from the first part. copy() because
        # with a single part `total` is that part's own frame.
        if "Bd_Name" in getattr(total, "columns", ()):
            total = total.copy()
            total["Bd_Name"] = results[(spec["parts"][0], module)]["Bd_Name"]
        results[(parent, module)] = total


def calculate_all(sc, groups, inventories, methods, verbose=True):
    """Run every group's LCA and derive the remaining modules.

    The steps, in the only order that works:

    1. zero-fill  technologies whose worksheet is absent
    2. calculate  one MultiLCA per group, scaled by SF (except B6)
    3. derive     B4 = (A13 + A4 + C3 + C4) * NumberReplacements
    4. include    D1, D3 = D * (1 + NumberReplacements)
    5. assemble   composite parents, from their final parts

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Provides the scenario-wide building list for zero-filled frames.
    groups : dict
        Output of build_all().
    inventories : dict
        Output of plca.inventories_calc.compute_all().
    methods : dict
        {short code: method tuple}, from impact_methods.load().
    verbose : bool, default True
        Print progress.

    Returns
    -------
    dict
        {(system, module): DataFrame} of impact scores per building, per m2.
    """
    results = {}

    # --- 1. technologies with no worksheet -----------------------------------
    for system in config.SYSTEMS:
        if system in inventories:
            continue
        for module in missing_sheet_modules(system):
            results[(system, module)] = empty_results(sc.bd_names)
        if verbose:
            print(f"Sheet '{config.SYSTEMS[system]['sheet']}' not found. "
                  f"Zero results for {system}.")

    # --- 2. the LCA, group by group ------------------------------------------
    if groups:
        # Any group's demands resolve to the same databases, so the first one
        # is used to build the shared inputs.
        (first_system, _module), first_acts = next(iter(groups.items()))
        first = inventories[first_system]
        shared = shared_inputs(methods,
                               functional_units(first_acts, first["bd_names"],
                                                first["bd_areas"]))

    calculated = 0
    for (system, module), acts in groups.items():
        inventory = inventories[system]
        frame = run_lca(acts, inventory["bd_names"], inventory["bd_areas"],
                        shared)

        # B6 is not scaled: operational energy already covers the study period.
        if module not in config.UNSCALED_MODULES:
            sf = by_building(inventory["sf"], inventory["bd_names"])
            frame = scale(frame, sf)

        results[(system, module)] = frame
        calculated += 1
        if verbose and module == config.SYSTEMS[system]["modules"][-1]:
            print(f"{system}: {len(config.SYSTEMS[system]['modules'])} "
                  f"module(s) calculated")

    # --- 3. module B4, derived -----------------------------------------------
    # `replacements` is None for Appliances (nothing to replace) and for the
    # geothermal parent (its B4 is the sum of its parts').
    for system, inventory in inventories.items():
        if inventory["replacements"] is None:
            continue
        results[(system, "B4")] = derive_b4(
            results, system,
            by_building(inventory["replacements"], inventory["bd_names"]))

    # --- 4. the D1 / D3 replacement inclusion --------------------------------
    # Consistency check: every pair in config.B4_INCLUSION_SKIPPED must still
    # have no exchange rows.
    still_empty = {pair for pair in config.B4_INCLUSION_SKIPPED
                   if not exchange_configs.EXCHANGES.get(pair)}
    if still_empty != set(config.B4_INCLUSION_SKIPPED):
        raise ValueError(
            f"config.B4_INCLUSION_SKIPPED lists blocks that are skipped by the "
            f"D1/D3 replacement inclusion because they have no exchange rows. "
            f"These now HAVE rows, so the inclusion would apply to them: "
            f"{sorted(set(config.B4_INCLUSION_SKIPPED) - still_empty)}. "
            f"That changes the results - confirm it and update "
            f"config.B4_INCLUSION_SKIPPED.")

    for system, inventory in inventories.items():
        if inventory["replacements"] is None:
            continue
        replacements = by_building(inventory["replacements"],
                                   inventory["bd_names"])
        for module in config.B4_INCLUDED_MODULES:
            if (system, module) not in results:
                continue
            if not exchange_configs.EXCHANGES.get((system, module)):
                # No exchange rows: the frame is all zeros, nothing to include.
                continue
            results[(system, module)] = include_b4(results[(system, module)],
                                                   replacements)

    # --- 5. the composite parents --------------------------------------------
    for parent in config.COMPOSITE_SYSTEMS:
        assemble_composite(results, parent, parent in inventories)

    if verbose:
        print(f"{calculated} LCA(s), {len(results)} result frame(s).")
    return results
