"""
scenario.py - the scenario workbook, opened once.

A Scenario holds the input workbook (DataInput_*.xlsm) and the scenario-level
values read from it - the study period, the building list and areas - and is
passed to every energy-system module. Sheets are read once and cached.

Input is validated on opening, so a blank cell, an all-zero energy split or an
unrecognised category is reported with the sheet, building and column instead
of surfacing later inside Brightway as 'Invalid amount in exchange ... nan'.
"""

import os

import numpy as np
import pandas as pd

from . import config

# Sheets that are configuration rather than technology data.
CONFIG_SHEETS = ("Scenario", "generatorsConfig")

# The label of the study-period row in the generatorsConfig sheet.
RSP_LABEL = "Reference Study Period (RSP) [Year]"

# Some systems split their electricity demand across sources by dividing each
# source by the total; if every source is zero (or a cell is blank) the shares
# become NaN. The source columns are found by this prefix.
ENERGY_INPUT_PREFIX = "Energy input from"


class ScenarioError(Exception):
    """Raised when the input workbook cannot be used as-is."""


class Scenario:
    """A pLCA-NEST scenario: one DataInput_*.xlsm workbook.

    Parameters
    ----------
    data_input : str
        Path to the DataInput_*.xlsm file.
    base_dir : str, optional
        Folder holding `eol_file`; defaults to the workbook's folder.
    eol_file : str, default 'EndOfLifeInputParameters.xlsx'
        End-of-life parameter file name, inside `base_dir`.
    strict : bool, default True
        If True, invalid input raises ScenarioError; if False the problems are
        printed and the run continues (results may then contain NaN).

    Attributes
    ----------
    rsp : float
        Reference study period [years].
    bd_names, bd_areas : pandas.Series
        Building names and net floor areas [m2], from the 'Scenario' sheet.
    problems : list of str
        Validation problems found on opening.

    Raises
    ------
    ScenarioError
        If the workbook is missing, a required value is absent, or (with
        strict=True) validation fails.
    """

    def __init__(self, data_input, base_dir=None, eol_file="EndOfLifeInputParameters.xlsx",
                 strict=True):
        self.path = os.path.abspath(data_input)
        if not os.path.exists(self.path):
            raise ScenarioError(f"scenario workbook not found: {self.path}")

        self.base_dir = os.path.abspath(base_dir or os.path.dirname(self.path))
        self.eol_path = os.path.join(self.base_dir, eol_file)

        # One handle for the whole run; individual sheets are read on demand and
        # cached in _sheets.
        self._book = pd.ExcelFile(self.path)
        self._sheets = {}

        self.generators_config = self.sheet("generatorsConfig")
        self.scenario_sheet = self.sheet("Scenario")

        # --- scenario-level values --------------------------------------------
        self.rsp = self._config_value(RSP_LABEL)          # study period [years]
        self.bd_names = self.scenario_sheet["Name"]
        self.bd_areas = self.scenario_sheet["Zone net floor area [m2]"]
        self.bd_uses = self.scenario_sheet["End Use"]
        self.heating_systems = self.scenario_sheet["Heating Energy Systems"]
        self.cooling_systems = self.scenario_sheet["Cooling Energy Systems"]

        self.problems = self.validate()
        if self.problems:
            report = "\n".join(f"    {p}" for p in self.problems)
            message = (f"{len(self.problems)} problem(s) in {os.path.basename(self.path)}:"
                       f"\n{report}")
            if strict:
                raise ScenarioError(message)
            print(f"WARNING: {message}")

    # -- sheets ---------------------------------------------------------------

    @property
    def sheet_names(self):
        return self._book.sheet_names

    def has_sheet(self, name):
        """Whether the workbook has a worksheet called `name`."""
        return name in self._book.sheet_names

    def sheet(self, name):
        """Read a worksheet, caching it after the first read."""
        if name not in self._sheets:
            if not self.has_sheet(name):
                raise ScenarioError(f"sheet {name!r} not in {os.path.basename(self.path)}")
            self._sheets[name] = pd.read_excel(self._book, sheet_name=name)
        return self._sheets[name]

    def systems_present(self):
        """Registry keys whose worksheet exists in this workbook."""
        return [key for key, entry in config.SYSTEMS.items()
                if entry["sheet"] and self.has_sheet(entry["sheet"])]

    # -- validation -----------------------------------------------------------

    # Categorical columns: values the energy-system code matches against a fixed
    # set, where an unrecognised value would silently become NaN.
    # {sheet: {column: (allowed values, what reads it)}}
    CATEGORICAL = {
        "Solar thermal system": {
            "Location": (("North-Italy", "Centre-Italy", "South-Italy"),
                         "solar_thermal.py picks the solar irradiance "
                         "[kW/m2] from it - 0.8 / 1.0 / 1.2"),
        },
    }

    def validate(self):
        """Check every technology sheet, returning a list of problem strings."""
        problems = []
        for key in self.systems_present():
            sheet_name = config.SYSTEMS[key]["sheet"]
            table = self.sheet(sheet_name)
            problems += self._check_blanks(sheet_name, table)
            problems += self._check_energy_split(sheet_name, table)
            problems += self._check_categories(sheet_name, table)
        return problems

    def _check_blanks(self, sheet_name, table):
        """A blank numeric cell becomes NaN and propagates into an exchange."""
        out = []
        for column in table.columns:
            values = table[column]
            if not pd.api.types.is_numeric_dtype(values):
                continue
            for row in values.index[values.isna()]:
                out.append(f"{sheet_name!r}, {self._row_label(table, row)}: "
                           f"column {column!r} is empty (becomes NaN)")
        return out

    def _check_energy_split(self, sheet_name, table):
        """The energy-input shares are each source divided by their total."""
        columns = [c for c in table.columns if str(c).startswith(ENERGY_INPUT_PREFIX)]
        if len(columns) < 2:
            return []
        out = []
        totals = table[columns].fillna(0).sum(axis=1)
        for row in totals.index[totals == 0]:
            out.append(f"{sheet_name!r}, {self._row_label(table, row)}: every "
                       f"{ENERGY_INPUT_PREFIX!r} column is zero, so the energy split "
                       f"is undefined (0/0). At least one must be non-zero.")
        return out

    def _check_categories(self, sheet_name, table):
        """Flag values outside the allowed set of a categorical column (see CATEGORICAL)."""
        out = []
        for column, (allowed, used_for) in self.CATEGORICAL.get(sheet_name, {}).items():
            if column not in table.columns:
                out.append(f"{sheet_name!r}: column {column!r} is missing, and "
                           f"{used_for}")
                continue
            for row, value in table[column].items():
                if value in allowed:
                    continue
                out.append(f"{sheet_name!r}, {self._row_label(table, row)}: "
                           f"column {column!r} is {value!r}, which is not one of "
                           f"{list(allowed)} - {used_for}, so an unrecognised "
                           f"value becomes NaN and reaches Brightway as "
                           f"'Invalid amount in exchange'")
        return out

    @staticmethod
    def _row_label(table, row):
        """Name a row by its building, so a problem points at something real."""
        if "Building Name" in table.columns:
            return f"building {table['Building Name'].iloc[row]!r}"
        return f"row {row + 2}"                     # +2: header plus 0-based index

    # -- internals ------------------------------------------------------------

    def _config_value(self, label):
        """Read one value from the generatorsConfig sheet by its 'Information' label."""
        found = self.generators_config.loc[
            self.generators_config["Information"] == label, "Data"]
        if found.empty:
            raise ScenarioError(
                f"{label!r} not found in the generatorsConfig sheet of "
                f"{os.path.basename(self.path)}")
        return found.values[0]

    def close(self):
        self._book.close()

    def __repr__(self):
        return (f"Scenario({os.path.basename(self.path)}, "
                f"{len(self.bd_names)} buildings, RSP={self.rsp}, "
                f"{len(self.systems_present())} systems)")
