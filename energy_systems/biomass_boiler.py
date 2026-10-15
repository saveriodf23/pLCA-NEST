# Derived from LCA4DHC (Energy_systems/BiomassBoiler.ipynb) - Copyright 2026
# Kevin Autelitano and Jacopo Famiglietti, licensed under the Apache License
# 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
biomass_boiler.py - life-cycle inventory of a wood-chip biomass boiler.

Size brackets are applied per building. Units worth noting: the concrete is in
cubic metres at A1-3 (kilograms at end of life), and the fuel is in kilograms
of wood chips. See energy_systems/__init__.py for the conventions shared by all
modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the boilers.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Biomass boiler' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Biomass boiler")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    LandfillClaybrick = eol["LandfillClaybrick"]
    LandfillConcrete = eol["LandfillConcrete"]
    LandfillElectronics = eol["LandfillElectronics"]
    LandfillGlass = eol["LandfillGlass"]
    LandfillMineralWool = eol["LandfillMineralWool"]
    LandfillPEHD = eol["LandfillPEHD"]
    IncinerationElectronics = eol["IncinerationElectronics"]
    IncinerationEPS = eol["IncinerationEPS"]
    IncinerationPEHD = eol["IncinerationPEHD"]
    IncinerationLubricatingOil = eol["IncinerationLubricatingOil"]
    RecyclingMetals = eol["RecyclingMetals"]
    RecyclingMetals2 = eol["RecyclingMetals2"]
    RecyclingClaybrick = eol["RecyclingClaybrick"]
    RecyclingConcrete = eol["RecyclingConcrete"]
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyClaybrick = eol["RecyclingEfficiencyClaybrick"]
    RecyclingEfficiencyConcrete = eol["RecyclingEfficiencyConcrete"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentClaybrick = eol["RecycledContentClaybrick"]
    RecycledContentConcrete = eol["RecycledContentConcrete"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    SRmetals = eol["SRmetals"]                      # substitution ratios, secondary vs primary
    SRclaybrick = eol["SRclaybrick"]
    SRinert = eol["SRinert"]
    LHVElastomer = eol["LHVElastomer"]              # lower heating values [MJ/kg], for D3
    LHVElectronics = eol["LHVElectronics"]
    LHVEPS = eol["LHVEPS"]
    LHVHDPE = eol["LHVHDPE"]
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency

    # DASHBORD - VALUE INPUTS
    BiomassBoiler_BdName = energysystem['Building Name']
    BiomassBoiler_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Thermal capacity [kW]']
    Energy_produced = energysystem['Energy produced [kWh /year]']
    Efficiency = energysystem['Efficiency (between 0 and 1)']

    # DASHBOARD - INPUT PARAMETERS
    Efficiency_LHV = Efficiency

    # DEFAULT PARAMETERS
    LHV = 18                              # wood chips [MJ/kg], as delivered
    HHV = 20                              # [MJ/kg]
    Lifespan = np.where(Power <= 100, 15, 20)      # [years], by capacity class
    RSP = np.array([RSP])
    Efficiency_HHV = Efficiency_LHV*(LHV/HHV)  # Efficiency based on HHV
    TotEnergyNeeds = np.array([Energy_produced])  # Energy need for 1 year [kWh per year]

    # -- Module A1-3 - per-building material quantities -----------------------
    # A reference unit mass [kg] per capacity class (Milestone-3 Table 3, p.29:
    # 9 kW / 176 kg, 25 kW / 613 kg, 300 kW / 4,138 kg), and a mass fraction per
    # material within each class. Above 500 kW the unit is modelled as j
    # machines of the 100-500 kW class (Milestone-3 Eq. 7's rule).
    # Note: the 500 kW divisor is inferred rather than documented; open
    # question to the inventory authors.
    P = Power.to_numpy(dtype=float)      # thermal capacity per building [kW]
    j = np.ceil(P / 500)                 # how many 100-500 kW machines it takes
    # The source data starts at 5 kW; smaller units are clamped to the smallest
    # documented class.
    _too_small = P < 5
    if _too_small.any():
        print(f"WARNING: {int(_too_small.sum())} biomass boiler(s) below 5 kW "
              f"({np.round(P[_too_small], 2).tolist()} kW) - clamped to the 5-20 kW "
              f"class (176 kg), the smallest documented unit.")
    brackets = [P <= 20,                 # small  (includes the clamped <5 kW units)
                (P > 20) & (P <= 100),   # medium
                (P > 100) & (P <= 500)]  # large
    # reference unit mass [kg]; above 500 kW, j of the 100-500 kW machine
    Mass = np.select(brackets, [176.0, 613.0, 4138.0], default=4138.0 * j)

    def _frac(small, medium, large, other):
        """Mass fraction for each size bracket -> one value per building."""
        return np.select(brackets, [small, medium, large], default=other)

    # mass fractions [-] of the reference unit mass       5-20    20-100   100-500  else
    BiomassBoiler_HDPE              = _frac(0.0011, 0.009,  0.001,  0.001 ) * Mass
    BiomassBoiler_AlkydPaint        = _frac(0.0,    0.001,  0.001,  0.001 ) * Mass
    BiomassBoiler_Aluminium         = _frac(0.0110, 0.0,    0.002,  0.002 ) * Mass
    BiomassBoiler_ChromiumSteel     = _frac(0.0,    0.0049, 0.007,  0.007 ) * Mass
    BiomassBoiler_ClayBrick         = _frac(0.0,    0.0,    0.166,  0.166 ) * Mass
    BiomassBoiler_CastIron          = _frac(0.1766, 0.0,    0.0,    0.0   ) * Mass
    BiomassBoiler_Ceramictile       = _frac(0.1821, 0.0,    0.0,    0.0   ) * Mass
    BiomassBoiler_Copper            = _frac(0.0017, 0.0003, 0.001,  0.001 ) * Mass
    BiomassBoiler_Electronics       = _frac(0.01,   0.007,  0.001,  0.001 ) * Mass
    BiomassBoiler_FlatGlassCoated   = _frac(0.0248, 0.0,    0.0,    0.0   ) * Mass
    BiomassBoiler_LowAlloyedSteel   = _frac(0.698,  0.754,  0.698,  0.698 ) * Mass
    BiomassBoiler_LubricatingOil    = _frac(0.0022, 0.001,  0.001,  0.001 ) * Mass
    BiomassBoiler_Polystyrene       = _frac(0.0,    0.029,  0.013,  0.013 ) * Mass
    BiomassBoiler_SheetRollingSteel = _frac(0.0635, 0.0062, 0.044,  0.044 ) * Mass
    BiomassBoiler_StoneWool         = _frac(0.064,  0.0086, 0.064,  0.064 ) * Mass
    # identical in all four brackets - functions of capacity only
    BiomassBoiler_Concrete       = 4.9171 * np.log(P) - 10.058   # [m3]
    BiomassBoiler_ElectricityA13 = 320.61 * np.log(P) - 561.92   # [kWh]
    BiomassBoiler_Heat           = 569.68 * np.log(P) - 521.23   # [MJ]

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    BiomassBoiler_Truck1632 = ((500 + 200)*(Mass)/1000)
    BiomassBoiler_Light_Truck = (50*(Mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    BiomassBoiler_Light_Truck_B2 = 50 * (Lifespan/2) * 0.01 * (Mass/1000)

    # --- Module B4: replacement within the study period -------------------------
    BiomassboilerNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFBiomassboiler = (RSP / Lifespan)  # Scaling factor

    # --- Module B6: operational energy over the study period --------------------
    # Grid / PV split of the auxiliary electricity. Placeholder values: all
    # auxiliary electricity is currently charged to the grid; the PV row is
    # kept wired for a future split.
    Grid = 1   # temporary
    PV = 0     # temporary
    TotEnergyNeeds = TotEnergyNeeds.flatten()
    # Heat delivered over the study period [MJ].
    y = (TotEnergyNeeds * 3.6 * RSP).flatten()
    # Scaling term for the emission factors below; the 0.06 factor is not
    # explained in the source inventory.
    x = (1/Efficiency_LHV)/(0.06*LHV)
    # Wood chips burned over the study period [kg].
    BiomassBoiler_EnergyVector = (1 / (Efficiency_LHV * LHV)) * y
    BiomassBoiler_ElectricityB6 = 0.0136 * x * y * Grid
    BiomassBoiler_ElectricityB6PV = 0.0136 * x * y * PV
    # BiomassBoiler_electricityB6RECSPV = BiomassBoiler_ElectricityB6 * 0.0056 * RECSPV
    # BiomassBoiler_electricityB6RECSHydro = BiomassBoiler_ElectricityB6 * 0.0056 * RECSHydro
    # BiomassBoiler_electricityB6RECSEolic = BiomassBoiler_ElectricityB6 * 0.0056 * RECSEolic

    # Combustion emissions, one line per substance. The biogenic carbon lines
    # are set to zero (original factors in the trailing comments): biogenic CO2
    # is reported as zero under EN 15804 unless biogenic carbon is tracked.
    BiomassBoiler_Acetaldehyde = 0.000000061126 * x * y
    BiomassBoiler_Ammonia = 0.0000017335 * x * y
    BiomassBoiler_Benzene = 0.00000091189 * x * y
    BiomassBoiler_Benzoapyrene = 0.000000000501039 * x * y
    BiomassBoiler_Bromine = 0.0000000006012472 * x * y
    BiomassBoiler_Cadmium = 0.000000000701455 * x * y
    BiomassBoiler_Calcium = 0.000005862161 * x * y
    BiomassBoiler_CarbonDioxide_Biogenic = 0.0 * x * y #0.096700605405914
    BiomassBoiler_CarbonMonoxide_Biogenic = 0.000 * x * y #0.000250519703124131
    BiomassBoiler_chlorine = 0.0000001803741 * x * y
    BiomassBoiler_chromium = 0.00000000396823 * x * y
    BiomassBoiler_ChromiumVI = 0.00000000004008315 * x * y
    BiomassBoiler_CopperB6 = 0.00000002204573 * x * y
    BiomassBoiler_DinitrogenMonoxide = 0.000003006236 * x * y
    BiomassBoiler_Dioxins = 0.0000000000000310644 * x * y
    BiomassBoiler_Fluorine = 0.00000000501039 * x * y
    BiomassBoiler_Formaldehyde = 0.0000001302702 * x * y
    BiomassBoiler_Hydrocarbons_Aliphatic_Unsaturated = 0.00000000911917 * x * y
    BiomassBoiler_Lead = 0.00000310644 * x * y
    BiomassBoiler_Magnesium = 0.000000002505109 * x * y
    BiomassBoiler_Manganese = 0.00000036074 * x * y
    BiomassBoiler_Mercury = 0.00000017035 * x * y
    BiomassBoiler_methanebiogenic = 0.000000000300623 * x * y
    BiomassBoiler_Mxylene = 0.0000114236984624604 * x * y
    BiomassBoiler_Nickel = 0.000000120249 * x * y
    BiomassBoiler_NitrogenOxides = 0.0000601247287497914 * x * y
    BiomassBoiler_NMVOC = 0.0000266552964124075 * x * y
    BiomassBoiler_PAH = 0.0000000120249 * x * y
    BiomassBoiler_Particulates_25 = 0.0000360748372498748 * x * y
    BiomassBoiler_Particulates_10 = 0.0000020041576 * x * y
    BiomassBoiler_pentachlorophenol = 0.0000000000081168 * x * y
    BiomassBoiler_Phosphorus = 0.0000003006 * x * y
    BiomassBoiler_Potassium = 0.0000234486442124186 * x * y
    BiomassBoiler_Sodium = 0.0000013027 * x * y
    BiomassBoiler_SulfurDioxide = 0.00000250519 * x * y
    BiomassBoiler_Toluene = 0.0000003006 * x * y
    BiomassBoiler_Water = 0.0000535110085873145 * x * y
    BiomassBoiler_Zinc = 0.0000003006 * x * y

    # --- Module C2: transport to treatment --------------------------------------
    BiomassBoiler_Transport_To_Treatment_Plant = (50 * (Mass/1000))

    # --- Module C3: waste processing --------------------------------------------
    # BiomassBoiler_EOL_electricity and _EOL_heat are computed but not wired to
    # any exchange.
    BiomassBoiler_EOL_HDPE = BiomassBoiler_HDPE
    BiomassBoiler_EOL_AlkydPaint = BiomassBoiler_AlkydPaint
    BiomassBoiler_EOL_Aluminium = BiomassBoiler_Aluminium
    BiomassBoiler_EOL_ChromiumSteel = BiomassBoiler_ChromiumSteel
    BiomassBoiler_EOL_ClayBrick = BiomassBoiler_ClayBrick
    BiomassBoiler_EOL_CastIron = BiomassBoiler_CastIron
    BiomassBoiler_EOL_Ceramictile = BiomassBoiler_Ceramictile
    # Concrete volume [m3] converted to the [kg] the end-of-life datasets use.
    BiomassBoiler_EOL_Concrete = BiomassBoiler_Concrete * config.CONCRETE_DENSITY
    BiomassBoiler_EOL_Copper = BiomassBoiler_Copper
    BiomassBoiler_EOL_electricity = BiomassBoiler_ElectricityA13
    BiomassBoiler_EOL_Electronics = BiomassBoiler_Electronics
    BiomassBoiler_EOL_FlatGlassCoated = BiomassBoiler_FlatGlassCoated
    BiomassBoiler_EOL_heat = BiomassBoiler_Heat
    BiomassBoiler_EOL_LowAlloyedSteel = BiomassBoiler_LowAlloyedSteel
    BiomassBoiler_EOL_lubricatingoil = BiomassBoiler_LubricatingOil
    BiomassBoiler_EOL_Polystyrene = BiomassBoiler_Polystyrene
    BiomassBoiler_EOL_SheetRollingSteel = BiomassBoiler_SheetRollingSteel
    BiomassBoiler_EOL_StoneWool = BiomassBoiler_StoneWool

    # --- Module C4: final disposal ----------------------------------------------
    # Each material times the share of it landfilled or incinerated. Alkyd
    # paint has no end-of-life share parameter and is 100% incinerated.
    BiomassBoiler_EOL_Inc_PEHD = BiomassBoiler_EOL_HDPE * IncinerationPEHD
    BiomassBoiler_EOL_Landfill_PEHD = BiomassBoiler_EOL_HDPE * LandfillPEHD
    BiomassBoiler_EOL_Inc_AlkydPaint = BiomassBoiler_EOL_AlkydPaint
    BiomassBoiler_EOL_Landfill_Aluminium = BiomassBoiler_EOL_Aluminium * LandfillMetals
    BiomassBoiler_EOL_Landfill_ChromiumSteel = BiomassBoiler_EOL_ChromiumSteel * LandfillMetals2
    BiomassBoiler_EOL_Landfill_ClayBrick = BiomassBoiler_EOL_ClayBrick * LandfillClaybrick
    BiomassBoiler_EOL_Landfill_CastIron = BiomassBoiler_EOL_CastIron * LandfillMetals2
    BiomassBoiler_EOL_Landfill_Ceramictile = BiomassBoiler_EOL_Ceramictile * LandfillClaybrick
    BiomassBoiler_EOL_Landfill_Concrete = BiomassBoiler_EOL_Concrete * LandfillConcrete
    BiomassBoiler_EOL_Landfill_Copper = BiomassBoiler_EOL_Copper * LandfillMetals
    BiomassBoiler_EOL_Inc_Electronics = BiomassBoiler_EOL_Electronics * IncinerationElectronics #kg
    BiomassBoiler_EOL_Landfill_Electronics = BiomassBoiler_EOL_Electronics * LandfillElectronics #kg
    BiomassBoiler_EOL_Landfill_FlatGlassCoated = BiomassBoiler_EOL_FlatGlassCoated * LandfillGlass #kg
    BiomassBoiler_EOL_Landfill_LowAlloyedSteel = BiomassBoiler_EOL_LowAlloyedSteel * LandfillMetals
    BiomassBoiler_EOL_Inc_LubricatingOil = BiomassBoiler_EOL_lubricatingoil * IncinerationLubricatingOil
    BiomassBoiler_EOL_Inc_Polystyrene = BiomassBoiler_EOL_Polystyrene * IncinerationEPS
    BiomassBoiler_EOL_Landfill_SheetRollingSteel = BiomassBoiler_EOL_SheetRollingSteel * LandfillMetals
    BiomassBoiler_EOL_Landfill_StoneWool = BiomassBoiler_EOL_StoneWool * LandfillMineralWool

    # --- Module D1: credit for exported secondary materials ---------------------
    # The primary concrete dataset is sold in [m3], so its credit is divided by
    # the density. The chromium-steel pair is written twice; the second
    # assignment overwrites the first with the same value.
    BiomassBoiler_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * BiomassBoiler_EOL_Aluminium) - (RecycledContentMetals * BiomassBoiler_EOL_Aluminium)
    BiomassBoiler_EOL_Primary_Aluminium = ((RecycledContentMetals * BiomassBoiler_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * BiomassBoiler_EOL_Aluminium)) * SRmetals
    # Cast iron is treated as a special metal (LandfillMetals2 /
    # RecyclingMetals2). Note: whether it should count as a common metal is an
    # open question to the inventory authors.
    BiomassBoiler_EOL_Recycling_CastIron = (RecyclingMetals2 * RecyclingEfficiencyMetals * BiomassBoiler_EOL_CastIron) - (RecycledContentMetals * BiomassBoiler_EOL_CastIron)
    BiomassBoiler_EOL_Primary_CastIron = ((RecycledContentMetals * BiomassBoiler_EOL_CastIron) - (RecyclingMetals2 * RecyclingEfficiencyMetals * BiomassBoiler_EOL_CastIron)) * SRmetals
    BiomassBoiler_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * BiomassBoiler_EOL_Copper) - (RecycledContentMetals * BiomassBoiler_EOL_Copper)
    BiomassBoiler_EOL_Primary_Copper = ((RecycledContentMetals * BiomassBoiler_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * BiomassBoiler_EOL_Copper)) * SRmetals
    BiomassBoiler_EOL_Recycling_HDPE = (RecyclingPEHD * RecyclingEfficiencyPlastics * BiomassBoiler_EOL_HDPE) - (RecycledContentPlastic * BiomassBoiler_EOL_HDPE)
    BiomassBoiler_EOL_Primary_HDPE = ((RecycledContentPlastic * BiomassBoiler_EOL_HDPE) - (RecyclingPEHD * RecyclingEfficiencyPlastics * BiomassBoiler_EOL_HDPE)) * SRinert
    BiomassBoiler_EOL_Recycling_SheetRollingSteel = (RecyclingMetals * RecyclingEfficiencyMetals * BiomassBoiler_EOL_SheetRollingSteel) - (RecycledContentMetals * BiomassBoiler_EOL_SheetRollingSteel)
    BiomassBoiler_EOL_Primary_SheetRollingSteel = ((RecycledContentMetals * BiomassBoiler_EOL_SheetRollingSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * BiomassBoiler_EOL_SheetRollingSteel)) * SRmetals
    BiomassBoiler_EOL_Recycling_ChromiumSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * BiomassBoiler_EOL_ChromiumSteel) - (RecycledContentMetals * BiomassBoiler_EOL_ChromiumSteel)
    BiomassBoiler_EOL_Primary_ChromiumSteel = ((RecycledContentMetals * BiomassBoiler_EOL_ChromiumSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * BiomassBoiler_EOL_ChromiumSteel)) * SRmetals
    BiomassBoiler_EOL_Recycling_ChromiumSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * BiomassBoiler_EOL_ChromiumSteel) - (RecycledContentMetals * BiomassBoiler_EOL_ChromiumSteel)
    BiomassBoiler_EOL_Primary_ChromiumSteel = ((RecycledContentMetals * BiomassBoiler_EOL_ChromiumSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * BiomassBoiler_EOL_ChromiumSteel)) * SRmetals
    BiomassBoiler_EOL_Recycling_ClayBrick = (RecyclingClaybrick * RecyclingEfficiencyClaybrick * BiomassBoiler_EOL_ClayBrick) - (RecycledContentClaybrick * BiomassBoiler_EOL_ClayBrick)
    BiomassBoiler_EOL_Primary_ClayBrick = ((RecycledContentClaybrick * BiomassBoiler_EOL_ClayBrick) - (RecyclingClaybrick * RecyclingEfficiencyClaybrick * BiomassBoiler_EOL_ClayBrick)) * SRclaybrick
    BiomassBoiler_EOL_Recycling_LowAlloyedSteel = (RecyclingMetals * RecyclingEfficiencyMetals * BiomassBoiler_EOL_LowAlloyedSteel) - (RecycledContentMetals * BiomassBoiler_EOL_LowAlloyedSteel)
    BiomassBoiler_EOL_Primary_LowAlloyedSteel = ((RecycledContentMetals * BiomassBoiler_EOL_LowAlloyedSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * BiomassBoiler_EOL_LowAlloyedSteel)) * SRmetals
    BiomassBoiler_EOL_Recycling_Concrete = (RecyclingConcrete * RecyclingEfficiencyConcrete * BiomassBoiler_EOL_Concrete) - (RecycledContentConcrete * BiomassBoiler_EOL_Concrete)
    BiomassBoiler_EOL_Primary_Concrete = (((RecycledContentConcrete * BiomassBoiler_EOL_Concrete) - (RecyclingConcrete * RecyclingEfficiencyConcrete * BiomassBoiler_EOL_Concrete)) * SRinert) / config.CONCRETE_DENSITY

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    BiomassBoiler_EOL_EnergyRecoveryHeat_AlkydPaint = - BiomassBoiler_EOL_Inc_AlkydPaint * LHVElastomer * Xincheat
    BiomassBoiler_EOL_EnergyRecoveryEle_AlkydPaint = - BiomassBoiler_EOL_Inc_AlkydPaint * LHVElastomer * Xincele / config.MJ_PER_KWH
    BiomassBoiler_EOL_EnergyRecoveryHeat_Electronics = - BiomassBoiler_EOL_Inc_Electronics * LHVElectronics * Xincheat
    BiomassBoiler_EOL_EnergyRecoveryEle_Electronics = - BiomassBoiler_EOL_Inc_Electronics * LHVElectronics * Xincele / config.MJ_PER_KWH
    BiomassBoiler_EOL_EnergyRecoveryHeat_PEHD = - BiomassBoiler_EOL_Inc_PEHD * LHVHDPE * Xincheat
    BiomassBoiler_EOL_EnergyRecoveryEle_PEHD = - BiomassBoiler_EOL_Inc_PEHD * LHVHDPE * Xincele / config.MJ_PER_KWH
    BiomassBoiler_EOL_EnergyRecoveryHeat_Polystyrene = - BiomassBoiler_EOL_Inc_Polystyrene * LHVEPS * Xincheat
    BiomassBoiler_EOL_EnergyRecoveryEle_Polystyrene = - BiomassBoiler_EOL_Inc_Polystyrene * LHVEPS * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, annual here; see energy_systems/__init__.py).
    ThermalEnergyProduced_Biomassboiler = TotEnergyNeeds

    # Collect every 'BiomassBoiler_' quantity for the exchange rows.
    loc = locals()
    return {
        "activity_data": {name: value for name, value in loc.items()
                          if name.startswith("BiomassBoiler_")},
        "sf": SFBiomassboiler,
        "replacements": BiomassboilerNumberReplacements,
        "bd_names": BiomassBoiler_BdName,
        "bd_areas": BiomassBoiler_BdArea,
        "thermal_energy": ThermalEnergyProduced_Biomassboiler,
    }
