"""
validation.py - save every result frame of a run to a pickle, under the
variable names pLCA-NEST v1.0 used ('dfresults_<module>_<system>' and so on),
so runs can be compared frame by frame.

Call save() after results_export.export_all(), which renames the aggregate
frames' columns in place. Details of the naming:

  * 'dfresults_B6_Appliances' is the appliances aggregate (it overwrites the
    per-system frame of the same name).
  * The neighbourhood frames are saved as the one-row frames written to Excel
    (results_export.hood_frames()); the two by-function frames are saved as
    'dfresults_<WLC|WLC_noD>_hood_by_function'.
  * 'dfresults_B6_Appliances_IND' holds the building names and areas.
"""

import pickle

from . import config
from . import results_aggregate
from . import results_export


def per_system_name(system, module):
    """Name of one technology's result frame, e.g. 'dfresults_A13_Boiler'.

    The aggregate frames are named by results_aggregate.original_name().
    """
    return f"dfresults_{module}_{config.SYSTEMS[system]['prefix']}"


def named_frames(sc, results, frames):
    """Every result frame of a run, by name.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        For the building list and areas.
    results : dict
        {(system, module): frame}, from lca_model.calculate_all().
    frames : dict
        From results_aggregate.aggregate_all(), after
        results_export.export_all() has renamed it in place.

    Returns
    -------
    dict
        {name: frame}
    """
    named = {}

    # The per-system frames.
    for (system, module), frame in results.items():
        named[per_system_name(system, module)] = frame

    # The aggregates, second, so the appliances aggregate overwrites the
    # per-system frame of the same name.
    for (category, module), frame in frames.items():
        if category in ("Neighbourhood", "Neighbourhood_ByFunction"):
            continue                 # handled below, as a frame rather than a Series
        named[results_aggregate.original_name(category, module)] = frame

    # The neighbourhood frames, as written to Excel.
    for (category, module), frame in results_export.hood_frames(frames).items():
        if category == "Neighbourhood_ByFunction":
            named[f"dfresults_{module}_hood_by_function"] = frame
            continue
        named[results_aggregate.original_name(category, module)] = frame

    # Building names and areas, as in v1.0.
    named["dfresults_B6_Appliances_IND"] = results_aggregate.identity_columns(
        sc, "Appliances")

    return named


def save(path, sc, results, frames, verbose=True):
    """Pickle a run's named frames (copied) to `path`.

    Name the file after the scenario database, like the result workbooks.

    Parameters
    ----------
    path : str
    sc, results, frames
        As for named_frames().
    verbose : bool, default True

    Returns
    -------
    str
        `path`.
    """
    named = named_frames(sc, results, frames)
    with open(path, "wb") as handle:
        pickle.dump({name: frame.copy() for name, frame in named.items()}, handle)
    if verbose:
        print(f"saved {len(named)} DataFrames to {path}")
    return path
