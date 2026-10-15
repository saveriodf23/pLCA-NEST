# Derived from LCA4DHC (RUN.ipynb) - Copyright 2026 Kevin Autelitano and Jacopo
# Famiglietti, licensed under the Apache License 2.0
# (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module;
# substantially rewritten; only the general approach to exporting results is
# retained.

"""
results_export.py - write the five styled Excel workbooks.

Five workbooks come out of a run, all named after the scenario database:

    <db>_LCA_results_heating.xlsx           14 sheets, the heating category
    <db>_LCA_results_cooling.xlsx           13 sheets, the cooling category
    <db>_LCA_results_appliances.xlsx         2 sheets, the plug load
    <db>_LCA_results.xlsx                   14 sheets, per building, everything
    <db>_LCA_results_wholeneighbourhood.xlsx 16 sheets, one row each (except
                                             the two "by Function" sheets,
                                             one row per heating/cooling/
                                             appliances)

Nothing is computed here: columns are renamed from short codes to readable
headers, frames are assigned to sheets, and the sheets are formatted. The
rename is done in place on the aggregate frames, so after export_all() they
carry the same headers as the workbooks; calling it twice is harmless.
"""

import os

import pandas as pd
from openpyxl.styles import Alignment, Border, Side
from openpyxl.utils import get_column_letter

from . import config

# Short code -> the header written into the workbook. Every unit is per m2 of
# the building's net floor area (the functional unit, see
# lca_model.functional_units).
RENAME = {
    "Bd_Name": "Building Name",
    "Bd_Area": "Building Area [m²]",
    "CC": "Climate Change: Total [kg CO₂ eq / m²]",
    "A": "Acidification [mol H⁺ eq / m²]",
    "ERnren": "Energy Resources: Non-Renewable [MJₗₕᵥ / m²]",
    "EF": "Eutrophication: Freshwater [kg P eq / m²]",
    "EM": "Eutrophication: Marine [kg N eq / m²]",
    "ET": "Eutrophication: Terrestrial [mol N eq / m²]",
    "RUMM": "Material Resources: Metals/Minerals [kg Sb eq / m²]",
    "OD": "Ozone Depletion [kg CFC-11 eq / m²]",
    "PM": "Particulate Matter Formation [disease incidence / m²]",
    "POF": "Photochemical Oxidant Formation: Human Health [kg NMVOC eq / m²]",
    "WU": "Water Use [m³ / m²]",
    "CCbio": "Climate Change: Biogenic [kg CO₂ eq / m²]",
    "CCfossil": "Climate Change: Fossil [kg CO₂ eq / m²]",
    "CCluc": "Climate Change: Land Use And Land Use Change [kg CO₂ eq / m²]",
    "PENRT": "Total Use Of Non-Renewable Primary Energy Resources "
             "[MJₚₑ / m²]",
}

# The neighbourhood sheets have no building name or area.
HOOD_RENAME = {code: header for code, header in RENAME.items()
               if code not in ("Bd_Name", "Bd_Area")}

# Cell formatting. The neighbourhood workbook uses one fewer significant figure.
NUMBER_FORMAT = "0.000E+00"
HOOD_NUMBER_FORMAT = "0.00E+00"
STANDARD_WIDTH = 25

# Sheet names. 'WLC' and 'WLC_noD' are the two summary sheets and come first,
# then the modules.
MODULE_SHEET = {"WLC": "Whole Lifecycle", "WLC_noD": "Whole Lifecycle (no D)"}
APPLIANCE_SHEET = {"WLC": "Whole Lifecycle (only B6)", "B6": "Module B6"}
HOOD_SHEET = {"WLC": "Whole Lifecycle (hood)",
              "WLC_noD": "Whole Lifecycle (no D, hood)",
              **{m: f"Module {m} (hood)" for m in config.WLC_MODULES}}
# The neighbourhood totals broken out by function (heating/cooling/appliances).
BY_FUNCTION_SHEET = {"WLC": "WLC by Function (hood)",
                     "WLC_noD": "WLC no D by Function (hood)"}


def sheet_name(module):
    """The worksheet name a module's frame is written to, e.g. 'Module A13'."""
    return MODULE_SHEET.get(module, f"Module {module}")


def sheet_plan(category):
    """Which frames go on which sheets of one workbook, in order.

    The two summary sheets lead, then the modules in config.WLC_MODULES order
    (no B1 for cooling). The neighbourhood workbook adds the two by-function
    sheets.

    Parameters
    ----------
    category : str
        'Heating', 'Cooling', 'Appliances', 'Total' or 'Neighbourhood'.

    Returns
    -------
    list of tuple
        (sheet name, (category, module)) pairs.
    """
    if category == "Appliances":
        return [(APPLIANCE_SHEET[m], (category, m)) for m in ("WLC", "B6")]

    modules = ["WLC", "WLC_noD"] + [
        m for m in config.WLC_MODULES
        if not (category == "Cooling" and m == "B1")]
    if category == "Neighbourhood":
        plan = [(HOOD_SHEET[m], (category, m)) for m in modules]
        plan += [(BY_FUNCTION_SHEET[m], ("Neighbourhood_ByFunction", m))
                for m in ("WLC", "WLC_noD")]
        return plan
    return [(sheet_name(m), (category, m)) for m in modules]


def rename_frames(frames, category):
    """Rename one category's columns from short codes to workbook headers, in place."""
    for _sheet, key in sheet_plan(category):
        frames[key].rename(columns=RENAME, inplace=True)


def hood_frames(frames):
    """Turn the neighbourhood results into the frames written to Excel.

    Each neighbourhood Series becomes a one-row frame; the by-function frames
    get their index as a leading 'Function' column. Columns are renamed with
    HOOD_RENAME.

    Parameters
    ----------
    frames : dict
        Output of results_aggregate.aggregate_all().

    Returns
    -------
    dict
        {(category, module): DataFrame} for the neighbourhood sheets (a new
        dict; `frames` is not modified).
    """
    built = {}
    for _sheet, key in sheet_plan("Neighbourhood"):
        source = frames[key]
        if isinstance(source, pd.Series):
            frame = source.to_frame().T
        else:
            frame = source.copy()
            frame.insert(0, "Function", frame.index)
            frame.reset_index(drop=True, inplace=True)
        frame.rename(columns=HOOD_RENAME, inplace=True)
        built[key] = frame
    return built


def style_sheet(worksheet, number_format):
    """Format one written worksheet.

    Every cell gets centred, wrapped text and a thin border; numeric cells
    below the header and right of the first two columns get the scientific
    number format, and every column the standard width.
    Note: on the neighbourhood sheets the first two columns are results, so
    they are left unformatted (display only).
    """
    center_alignment = Alignment(horizontal="center", vertical="center",
                                 wrap_text=True)
    thin_border = Border(left=Side(style="thin"), right=Side(style="thin"),
                         top=Side(style="thin"), bottom=Side(style="thin"))

    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = center_alignment
            cell.border = thin_border
            if (cell.row > 1 and cell.column > 2
                    and isinstance(cell.value, (int, float))):
                cell.number_format = number_format

    for col_idx in range(1, worksheet.max_column + 1):
        worksheet.column_dimensions[get_column_letter(col_idx)].width = \
            STANDARD_WIDTH


def write_workbook(path, sheets, number_format=NUMBER_FORMAT):
    """Write one workbook (without the index) and format every sheet.

    Parameters
    ----------
    path : str
        Output file.
    sheets : list of tuple
        (sheet name, DataFrame), in the order they should appear.
    number_format : str
        Excel number format for the result cells.

    Returns
    -------
    str
        `path`.
    """
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in sheets:
            frame.to_excel(writer, sheet_name=name, index=False)
        for name in writer.sheets:
            style_sheet(writer.sheets[name], number_format)
    return path


def export_all(frames, scenario_db_name, output_dir=None, verbose=True):
    """Write all five workbooks.

    Renames the aggregate frames' columns in place first.

    Parameters
    ----------
    frames : dict
        Output of results_aggregate.aggregate_all().
    scenario_db_name : str
        The run's Brightway database name; every file is named after it.
    output_dir : str, optional
        Where to write; defaults to the working directory.
    verbose : bool, default True
        Print each file written.

    Returns
    -------
    list of str
        The paths written, in order.
    """
    if output_dir is None:
        output_dir = os.getcwd()

    for category in ("Heating", "Cooling", "Appliances", "Total"):
        rename_frames(frames, category)
    hood = hood_frames(frames)

    written = []
    for category, suffix in (("Heating", "_heating"),
                             ("Cooling", "_cooling"),
                             ("Appliances", "_appliances"),
                             ("Total", ""),
                             ("Neighbourhood", "_wholeneighbourhood")):
        source = hood if category == "Neighbourhood" else frames
        sheets = [(name, source[key]) for name, key in sheet_plan(category)]
        path = os.path.join(
            output_dir, f"{scenario_db_name}_LCA_results{suffix}.xlsx")
        number_format = (HOOD_NUMBER_FORMAT if category == "Neighbourhood"
                         else NUMBER_FORMAT)
        write_workbook(path, sheets, number_format)
        written.append(path)
        if verbose:
            print(f"wrote {path} ({len(sheets)} sheet(s))")

    return written
