# Derived from LCA4DHC (RUN.ipynb) - Copyright 2026 Kevin Autelitano and Jacopo
# Famiglietti, licensed under the Apache License 2.0
# (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module;
# generalised into a registry of energy systems and life cycle modules from
# information spread across the notebook.

"""
config.py - the registry: what exists in a pLCA-NEST run.

Pure data: which worksheet each technology reads, which EN 15804 modules it
has, which units its activities carry, and how results are grouped.

To add a technology: add one entry to SYSTEMS and one module in
energy_systems/. Activity creation, exchange wiring, the LCA and the
aggregation all loop over this table.
"""

# ---------------------------------------------------------------------------
# EN 15804 life-cycle modules
# ---------------------------------------------------------------------------
# A1-3  product stage: raw material supply, transport, manufacturing
# A4    transport of the finished unit to the building site
# A5    installation on site
# B1    use-stage emissions from the installed product (refrigerant leakage)
# B2    maintenance
# B4    replacement of the unit within the study period
# B6    operational energy use
# C2    transport of the discarded unit to treatment
# C3    waste processing (sorting, collection for recycling)
# C4    final disposal (landfill, incineration)
# D1    benefits beyond the boundary: exported secondary materials
# D3    benefits beyond the boundary: energy exported from waste incineration

# Modules that get a Brightway activity and a real LCA calculation.
LCA_MODULES = ["A13", "A4", "A5", "B1", "B2", "B6", "C2", "C3", "C4", "D1", "D3"]

# B6 is the one module NOT multiplied by the scaling factor SF = RSP / Lifespan:
# operational energy is already computed over the whole study period.
UNSCALED_MODULES = {"B6"}

# Groups scaled other than once by SF. Both are empty; kept for compatibility.
DOUBLE_SCALED_GROUPS = set()
MISDIRECTED_SCALING = {}

# B4 is derived arithmetically, not calculated - it has no Brightway activity.
# Replacing a unit repeats its production, delivery and end of life:
#     B4 = (A13 + A4 + C3 + C4) * NumberReplacements
B4_SOURCE_MODULES = ("A13", "A4", "C3", "C4")

# D1 and D3 are then recomputed to include the replacement units:
#     D = D * (1 + NumberReplacements)
# Applied after the SF scaling. Order: scale -> derive B4 -> include B4.
B4_INCLUDED_MODULES = ("D1", "D3")

# Blocks the D1/D3 inclusion skips because they have no exchange rows (they
# score zero). The skip itself is derived in lca_model.calculate_all(), which
# checks that every pair listed here still has no rows.
B4_INCLUSION_SKIPPED = {
    ("ConcreteThermalStorage", "D3"),
    ("SteelThermalStorage", "D3"),
    ("CompressionChiller", "D3"),
    ("DryCooler", "D3"),
    ("Geothermal_DeepWell", "D3"),
    ("Geothermal_HeatExchanger", "D3"),
}

# ---------------------------------------------------------------------------
# Brightway activity specification and physical constants
# ---------------------------------------------------------------------------
# Every activity in the scenario database is created with location 'IT'.
LOCATION = "IT"

# Composition of the gas blend burned by "Gas-blend" machines (boiler, gas
# engine heat pump, turbogas, combined cycle and waste-to-energy): A natural
# gas, B biomethane, C hydrogen. Set to pure natural gas: the prospective
# evolution is modelled in the background database (premise), not by changing
# the foreground fuel. The reference model LCA4DHC's year-dependent shares are,
# for reference: 2030 0.90/0.084/0.014, 2035 0.795/0.189/0.016, 2040
# 0.688/0.294/0.018, 2045 0.582/0.399/0.020, 2050 0/0.80/0.20.
GAS_BLEND = (1.0, 0.0, 0.0)          # A natural gas, B biomethane, C hydrogen

# LPG density [kg/m3], converting the LPG fuel rows of boiler.py and
# gas_engine_heat_pump.py from cubic metres (their heating values are per m3)
# to the kilograms the LPG dataset is sold in. A value for a commercial
# propane-butane mix (propane 1.88, butane 2.49 kg/m3 at 15 C).
LPG_DENSITY = 2.1                    # kg/m3, commercial propane-butane mix

# Concrete density [kg/m3], converting concrete between the cubic metres of
# the A1-3 and primary-concrete datasets and the kilograms of the end-of-life
# datasets (as in the source LCI).
CONCRETE_DENSITY = 2400              # kg/m3

# Converts module D3 electricity credits from MJ to the kWh of the electricity
# dataset.
MJ_PER_KWH = 3.6                     # MJ per kWh

# The activity unit depends only on the module. Activities are per m2 of floor
# area because the functional unit is 1 / building area.
MODULE_UNITS = {
    "A4": "ton kilometer / m2",   # transport work
    "C2": "ton kilometer / m2",   # transport to treatment
    "B6": "kilowatt hour / m2",   # operational energy
}
DEFAULT_UNIT = "unit / m2"

# ---------------------------------------------------------------------------
# Impact categories (EN 15804+A2)
# ---------------------------------------------------------------------------
# Short codes used as result columns; the Brightway method tuples are in
# impact_methods.py.
IMPACT_CATEGORIES = [
    "CC",        # climate change: total
    "CCbio",     # climate change: biogenic
    "CCfossil",  # climate change: fossil
    "CCluc",     # climate change: land use and land use change
    "A",         # acidification
    "EF",        # eutrophication: freshwater
    "EM",        # eutrophication: marine
    "ET",        # eutrophication: terrestrial
    "OD",        # ozone depletion
    "PM",        # particulate matter formation
    "POF",       # photochemical oxidant formation
    "RUMM",      # material resources: metals/minerals
    "WU",        # water use
    "ERnren",    # energy resources: non-renewable
    "PENRT",     # total use of non-renewable primary energy
]

# ---------------------------------------------------------------------------
# The energy systems
# ---------------------------------------------------------------------------
# key -> {sheet, module, prefix, modules}
#   sheet    the worksheet name in the DataInput_*.xlsm workbook.
#   module   the module under energy_systems/ that computes the inventory
#            (the three Geothermal entries share one).
#   prefix   the name the technology's identifiers are built from: the key of
#            its blocks in exchange_configs.py and the middle part of every
#            activity code ('A13_<prefix>_<building>'). Equal to the key.
#   modules  the LCA modules the technology gets activities for.

# The modules most technologies carry. Some activities have no inventory (a
# passive store has no B6, a chiller incinerates nothing for D3); they are
# created anyway and score zero, so every result workbook has the same columns.
_BASELINE = ["A13", "A4", "A5", "B2", "B6", "C2", "C3", "C4", "D1", "D3"]

SYSTEMS = {
    # --- heat generation -----------------------------------------------------
    "Boiler": {
        "sheet": "Boiler",
        "module": "boiler",
        "prefix": "Boiler",
        "modules": _BASELINE,
    },
    "BiomassBoiler": {
        "sheet": "Biomass boiler",
        "module": "biomass_boiler",
        "prefix": "BiomassBoiler",
        "modules": _BASELINE,
    },
    "FuelOilBoiler": {
        "sheet": "Fuel oil boiler",
        "module": "fuel_oil_boiler",
        "prefix": "FuelOilBoiler",
        "modules": _BASELINE,
    },
    # --- combined heat and power ---------------------------------------------
    "CHP_RICE": {
        "sheet": "CHP-Internal Combustion Engine",
        "module": "chp_rice",
        "prefix": "CHP_RICE",
        "modules": _BASELINE,
    },
    "CHP_ORC": {
        "sheet": "CHP-Organic Rankine Cycle",
        "module": "chp_orc",
        "prefix": "CHP_ORC",
        "modules": _BASELINE,
    },
    "CHP_WasteToEnergy": {
        "sheet": "CHP-Waste-to-Energy",
        "module": "chp_waste_to_energy",
        "prefix": "CHP_WasteToEnergy",
        "modules": _BASELINE,
        # Contributes nothing at present: its allocation factors are set to 0
        # (see chp_waste_to_energy.py).
    },
    "CHP_CombinedCycle": {
        "sheet": "CHP-Combined Cycle",
        "module": "chp_combined_cycle",
        "prefix": "CHP_CombinedCycle",
        "modules": _BASELINE,
    },
    "CHP_Turbogas": {
        "sheet": "CHP-Turbogas",
        "module": "chp_turbogas",
        "prefix": "CHP_Turbogas",
        "modules": _BASELINE,
    },
    # --- heat recovery and solar ---------------------------------------------
    "HeatRecovery": {
        "sheet": "Heat recovery",
        "module": "heat_recovery",
        "prefix": "HeatRecovery",
        # passive unit: B6 and D3 activities exist but have no exchanges (zero)
        "modules": _BASELINE,
    },
    "SolarThermal": {
        "sheet": "Solar thermal system",
        "module": "solar_thermal",
        "prefix": "SolarThermal",
        "modules": _BASELINE,
    },
    # --- heat pumps ----------------------------------------------------------
    "ElectricHeatPump": {
        "sheet": "Electric Heat Pump",
        "module": "electric_heat_pump",
        "prefix": "ElectricHeatPump",
        # B1: refrigerant leakage during use
        "modules": ["A13", "A4", "A5", "B1", "B2", "B6", "C2", "C3", "C4", "D1", "D3"],
    },
    "GasAbsorptionHeatPump": {
        "sheet": "Gas Absorption Heat Pump",
        "module": "gas_absorption_heat_pump",
        "prefix": "GasAbsorptionHeatPump",
        "modules": _BASELINE,
    },
    "GasEngineHeatPump": {
        "sheet": "Gas Engine Heat Pump",
        "module": "gas_engine_heat_pump",
        "prefix": "GasEngineHeatPump",
        "modules": ["A13", "A4", "A5", "B1", "B2", "B6", "C2", "C3", "C4", "D1", "D3"],
    },
    # --- thermal storage -----------------------------------------------------
    "ConcreteThermalStorage": {
        "sheet": "Concrete thermal storage",
        "module": "concrete_thermal_storage",
        "prefix": "ConcreteThermalStorage",
        # passive store: B6 and D3 activities exist but have no exchanges (zero)
        "modules": _BASELINE,
    },
    "SteelThermalStorage": {
        "sheet": "Steel thermal storage",
        "module": "steel_thermal_storage",
        "prefix": "SteelThermalStorage",
        # passive store: B6 and D3 activities exist but have no exchanges (zero)
        "modules": _BASELINE,
    },
    # --- geothermal ----------------------------------------------------------
    # Two physical parts plus a shared operating stage; see COMPOSITE_SYSTEMS.
    "Geothermal": {
        "sheet": "Geothermal plant",
        "module": "geothermal",
        "prefix": "Geothermal",
        # only the shared operating modules are calculated directly; the rest
        # are summed from the two parts
        "modules": ["B2", "B6"],
    },
    "Geothermal_DeepWell": {
        "sheet": "Geothermal plant",
        "module": "geothermal",
        "prefix": "Geothermal_DeepWell",
        "modules": ["A13", "A4", "A5", "C2", "C3", "C4", "D1", "D3"],
    },
    "Geothermal_HeatExchanger": {
        "sheet": "Geothermal plant",
        "module": "geothermal",
        "prefix": "Geothermal_HeatExchanger",
        "modules": ["A13", "A4", "A5", "C2", "C3", "C4", "D1", "D3"],
    },
    # --- cooling -------------------------------------------------------------
    "AbsorptionChiller": {
        "sheet": "Cooling - Absorption chiller",
        "module": "absorption_chiller",
        "prefix": "AbsorptionChiller",
        "modules": _BASELINE,
    },
    "CompressionChiller": {
        "sheet": "Cooling - Compression chiller",
        "module": "compression_chiller",
        "prefix": "CompressionChiller",
        # D3 activity exists but has no exchanges (nothing incinerated) -> zero
        "modules": _BASELINE,
    },
    "DryCooler": {
        "sheet": "Cooling - Dry cooler",
        "module": "dry_cooler",
        "prefix": "DryCooler",
        # D3 activity exists but has no exchanges (nothing incinerated) -> zero
        "modules": _BASELINE,
    },
    "CoolingTower": {
        "sheet": "Cooling - Cooling tower",
        "module": "cooling_tower",
        "prefix": "CoolingTower",
        "modules": _BASELINE,
    },
    # --- appliances ----------------------------------------------------------
    "Appliances": {
        "sheet": "Appliances demand",
        "module": "appliances",
        "prefix": "Appliances",
        # only plug loads: operational electricity, nothing manufactured here
        "modules": ["B6"],
    },
}

# Present but switched off: the district network (pipes, valves, substation
# heat exchanger) has no input worksheet yet. See energy_systems/auxiliaries.py.
DISABLED_SYSTEMS = {
    "Auxiliaries": {
        "sheet": None,
        "module": "auxiliaries",
        "prefix": None,
        "modules": ["A13", "A4", "A5", "B2", "B6", "C2", "C3", "C4", "D1", "D3"],
    },
}

# ---------------------------------------------------------------------------
# Composite systems
# ---------------------------------------------------------------------------
# Geothermal results are assembled from parts: the deep well and the heat
# exchanger have their own lifespans and replacement counts, so they are
# calculated separately and summed. B2 and B6 belong to the plant as a whole
# and are calculated directly against 'Geothermal'.
COMPOSITE_SYSTEMS = {
    "Geothermal": {
        "parts": ["Geothermal_DeepWell", "Geothermal_HeatExchanger"],
        "modules": ["A13", "A4", "A5", "B4", "C2", "C3", "C4", "D1", "D3"],
    },
}

# ---------------------------------------------------------------------------
# Result categories
# ---------------------------------------------------------------------------
# Which systems roll up into each output workbook. A building's heating result
# is the sum over its heating systems, and likewise for cooling. The frames
# are added in list order (floating-point addition is order-sensitive in the
# last bit), so keep the order stable for reproducible results.
HEATING_SYSTEMS = [
    "Boiler", "BiomassBoiler", "FuelOilBoiler",
    "CHP_RICE", "CHP_ORC", "CHP_WasteToEnergy", "CHP_CombinedCycle", "CHP_Turbogas",
    "HeatRecovery", "SolarThermal",
    "ElectricHeatPump", "GasAbsorptionHeatPump", "GasEngineHeatPump",
    "ConcreteThermalStorage", "SteelThermalStorage",
    "Geothermal",
]

COOLING_SYSTEMS = [
    "AbsorptionChiller", "CompressionChiller", "CoolingTower", "DryCooler",
]

APPLIANCE_SYSTEMS = ["Appliances"]

# Whole-life-cycle totals. WLC sums every module; WLC_noD excludes the module D
# credits, which EN 15804 reports separately from the life cycle proper.
WLC_MODULES = ["A13", "A4", "A5", "B1", "B2", "B6", "C2", "C3", "C4", "B4", "D1", "D3"]
WLC_NO_D_MODULES = [m for m in WLC_MODULES if m not in ("D1", "D3")]


def unit_for(module):
    """Brightway unit string for a module's activities."""
    return MODULE_UNITS.get(module, DEFAULT_UNIT)


def activity_code(module, system, building):
    """Activity code in the scenario database, e.g. 'A13_Boiler_Bd2432709'.

    Parameters
    ----------
    module : str
        EN 15804 module code.
    system : str
        The SYSTEMS entry's 'prefix'.
    building : str
        Building name.

    Returns
    -------
    str
    """
    return f"{module}_{system}_{building}"
