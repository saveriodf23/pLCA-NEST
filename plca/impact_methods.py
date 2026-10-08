"""
impact_methods.py - the 15 EN 15804+A2 impact categories the LCA is run against.

A Brightway method is identified by a tuple such as
    ('EF v3.1 EN15804', 'EN15804+A2 - Core impact categories and indicators',
     'acidification')
whose first element depends on how the LCIA data was imported. Each category is
therefore found by matching the last two elements - the section and the
category name.

config.IMPACT_CATEGORIES lists the same categories as short codes for
reporting; this module turns the codes into Brightway method tuples.
"""

import bw2data as bd

# The three EN 15804+A2 sections, as bd.methods spells them (element [1] of the
# method tuple). Which section a category sits in is part of its identity: the
# same name can appear under more than one section.
CORE = "EN15804+A2 - Core impact categories and indicators"
ADDITIONAL = "EN15804+A2 - Additional impact categories and indicators"
RESOURCE_USE = "EN15804+A2 - Indicators describing resource use"

# short code -> (section, category name as in bd.methods[...][2]), in the
# order handed to MultiLCA (not the order results come back in).
METHODS = {
    "CC":       (CORE, "climate change: total (EF v3.1 - IPCC 2021)"),
    "A":        (CORE, "acidification"),
    "ERnren":   (CORE, "energy resources: non-renewable"),
    "EF":       (CORE, "eutrophication: freshwater"),
    "EM":       (CORE, "eutrophication: marine"),
    "ET":       (CORE, "eutrophication: terrestrial"),
    "RUMM":     (CORE, "material resources: metals/minerals"),
    "OD":       (CORE, "ozone depletion"),
    "PM":       (ADDITIONAL, "particulate matter formation"),
    "POF":      (CORE, "photochemical oxidant formation: human health"),
    "WU":       (CORE, "water use"),
    "CCbio":    (CORE, "climate change: biogenic (EF v3.1 - IPCC 2021)"),
    "CCfossil": (CORE, "climate change: fossil (EF v3.1 - IPCC 2021)"),
    "CCluc":    (CORE, "climate change: land use and land use change (EF v3.1 - IPCC 2021)"),
    "PENRT":    (RESOURCE_USE, "total use of non-renewable primary energy resources "
                               "(primary energy and primary energy resources used as raw materials)"),
}

# The order the impact columns appear in every per-system result frame: MultiLCA
# results are reshaped with .unstack(), which sorts them by method tuple, i.e.
# alphabetically by (section, category).
RESULT_COLUMNS = ["PM", "A", "CCbio", "CCfossil", "CCluc", "CC", "ERnren", "EF",
                  "EM", "ET", "RUMM", "OD", "POF", "WU", "PENRT"]


def load():
    """Find the 15 method tuples in the current Brightway project.

    Requires the EN 15804+A2 LCIA methods in the project (imported with the
    ecoinvent release, lcia=True).

    Returns
    -------
    dict
        {short code: method tuple}, in METHODS order;
        list(load().values()) is what goes into a MultiLCA method_config.

    Raises
    ------
    ValueError
        If any category is not found.
    """
    found = {}
    missing = []
    for code, (section, category) in METHODS.items():
        matches = [m for m in bd.methods if category == m[2] and section == m[1]]
        if not matches:
            missing.append(f"{code}: {section!r} / {category!r}")
            continue
        # If several variants match, the last one is used.
        found[code] = matches.pop()

    if missing:
        raise ValueError(
            "impact categories not found in project "
            f"{bd.projects.current!r}:\n    " + "\n    ".join(missing) +
            "\nThe EN 15804+A2 methods come with the ecoinvent import; check that "
            "it ran with lcia=True.")
    return found


def reverse_lookup(methods):
    """Map method tuples back to short codes, for labelling result columns.

    Parameters
    ----------
    methods : dict
        Output of load().

    Returns
    -------
    dict
        {method tuple: short code}
    """
    return {method: code for code, method in methods.items()}
