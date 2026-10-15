# Derived from LCA4DHC (Energy_systems/CoolingAbsorptionChiller.ipynb) -
# Copyright 2026 Kevin Autelitano and Jacopo Famiglietti, licensed under the
# Apache License 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
absorption_chiller.py - life-cycle inventory of an absorption chiller.

A heat-driven chiller using an ammonia-water absorption cycle instead of a
compressor, so its electricity demand is small. Module A1-3 carries its own
heat and electricity rows, and the ammonia charge appears as a hazardous-waste
stream at end of life. See energy_systems/__init__.py for the conventions
shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Cooling - Absorption chiller'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Cooling - Absorption chiller")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]      # share of low-alloyed metals landfilled
    LandfillMineralWool = eol["LandfillMineralWool"]
    LandfillElastomer = eol["LandfillElastomer"]
    LandfillElectronics = eol["LandfillElectronics"]
    LandfillPEHD = eol["LandfillPEHD"]
    IncinerationElastomer = eol["IncinerationElastomer"]
    IncinerationElectronics = eol["IncinerationElectronics"]
    IncinerationHazardous = eol["IncinerationHazardous"]
    IncinerationPEHD = eol["IncinerationPEHD"]
    RecyclingMetals = eol["RecyclingMetals"]    # share of low-alloyed metals recycled
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    SRmetals = eol["SRmetals"]                  # substitution ratios, secondary vs primary
    SRinert = eol["SRinert"]
    LHVElastomer = eol["LHVElastomer"]          # lower heating values [MJ/kg], for the
    LHVElectronics = eol["LHVElectronics"]      # energy recovered by incineration (D3)
    LHVHDPE = eol["LHVHDPE"]
    LHVHazardous = eol["LHVHazardous"]
    Xincheat = eol["Xincheat"]                  # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                    # electricity recovery efficiency

    # DASHBORD - VALUE INPUTS
    # The only cooling system with no electricity-source columns: it uses the
    # fixed Grid / PV switch in module B6 instead.
    AbsorptionChiller_BdName = energysystem['Building Name']
    AbsorptionChiller_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Cooling capacity [kW]']
    EnergyCooling = energysystem['Energy absorbed [kWh/year]']
    SCOP = energysystem['COP']    # read but currently unused

    # DASHBOARD - INPUT PARAMETERS
    # Unit mass [kg] scaled linearly from the ecoinvent reference machine
    # (3,912 kg for 100 + 250 kW).
    massRef = 3912 #kg
    PowerRef = 100 + 250 # kW (Source: Ecoinvent database)
    mass = massRef * (Power / PowerRef)
    Lifespan = 20 #years

    # --- Module A1-3: manufacture -----------------------------------------------
    # Quantities of the reference machine [kg], scaled by mass / massRef; the
    # factory energy rows (electricity [kWh], heat [MJ]) scale on Power /
    # PowerRef. The sheet-rolling and wire-drawing rows are processes applied
    # to material counted above, so they have no end-of-life counterpart.
    AbsorptionChiller_Aluminium = 420 * (mass / massRef)
    AbsorptionChiller_Ammonia = 72 * (mass / massRef)
    AbsorptionChiller_Copper = 480 * (mass / massRef)
    AbsorptionChiller_Electricitylowvoltage = 800 * (Power / PowerRef)
    AbsorptionChiller_Electricitymediumvoltage = 133 * (Power / PowerRef)
    AbsorptionChiller_Electronics = 60 * (mass / massRef)
    AbsorptionChiller_GlycolEthylene = 150 * (mass / massRef)
    AbsorptionChiller_HeatOther = 5640 * (Power / PowerRef) #MJ
    AbsorptionChiller_HeatfromGas = 903 * (Power / PowerRef) #MJ
    AbsorptionChiller_PEHD = 40 * (mass / massRef)
    AbsorptionChiller_ReinforcingSteel = 3220 * (mass / massRef)
    AbsorptionChiller_SheetRollingSteel = 3220 * (mass / massRef)
    AbsorptionChiller_SheetRollingAluminium = 420 * (mass / massRef)
    AbsorptionChiller_SheetrollingStainlessSteel = 480 * (mass / massRef)
    AbsorptionChiller_StoneWool = 70 * (mass / massRef)
    AbsorptionChiller_Elastomer = 90 * (mass / massRef)
    AbsorptionChiller_WireDrawingCopper = 480 * (mass / massRef)
    AbsorptionChiller_Water = 630 * (mass / massRef)
    AbsorptionChiller_WaterWater = 0.99 * (mass / massRef) #cubic meter
    AbsorptionChiller_WaterUnspec = 5.98 * (mass / massRef) #cubic meter

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    AbsorptionChiller_Truck1632 = ((500 + 200)*(mass)/1000)
    AbsorptionChiller_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the unit mass
    # (first Lifespan, see the B4 note), plus injection moulding of the PEHD
    # parts.
    AbsorptionChiller_Light_Truck_B2 = 50 * (Lifespan/2) * 0.01 * (mass/1000)
    AbsorptionChiller_InjectionMoulding = 40 * (mass / massRef)

    # --- Module B4: replacement within the study period -------------------------
    # Note: Lifespan is reassigned here, so B2 uses 20 years while B4 and the
    # scaling factor use 25. Open question to the inventory authors.
    Lifespan = 25 #year
    AbsChillerNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFAbsChiller = (RSP / Lifespan)  # Scaling factor

    # --- Module B6: operating electricity ---------------------------------------
    # Auxiliary electricity over the study period [kWh]: 1% of the cooling
    # delivered (pumps and controls of a heat-driven machine). Placeholder
    # Grid / PV split: all charged to the grid; the PV row is kept wired for a
    # future split.
    Grid = 1 #temporary
    PV = 0   #temporary

    AbsorptionChiller_UsePhaseElectricity = 0.01 * EnergyCooling * RSP * Grid
    AbsorptionChiller_UsephaseelectricityPV = 0.01 * EnergyCooling * RSP * PV

    # AbsorptionChiller_usephaseelectricityRECSPV = AbsorptionChiller_UsePhaseElectricity * 0.0056 * RECSPV
    # AbsorptionChiller_usephaseelectricityRECSHydro = AbsorptionChiller_UsePhaseElectricity * 0.0056 * RECSHydro
    # AbsorptionChiller_usephaseelectricityRECSEolic = AbsorptionChiller_UsePhaseElectricity * 0.0056 * RECSEolic

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km].
    AbsorptionChiller_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    AbsorptionChiller_EOL_Aluminium = AbsorptionChiller_Aluminium
    AbsorptionChiller_EOL_ammonia = AbsorptionChiller_Ammonia
    AbsorptionChiller_EOL_Copper = AbsorptionChiller_Copper
    AbsorptionChiller_EOL_Electronics = AbsorptionChiller_Electronics
    AbsorptionChiller_EOL_PEHD = AbsorptionChiller_PEHD
    AbsorptionChiller_EOL_ReinforcingSteel = AbsorptionChiller_ReinforcingSteel
    AbsorptionChiller_EOL_Stonelwool = AbsorptionChiller_StoneWool
    AbsorptionChiller_EOL_Elastomer = AbsorptionChiller_Elastomer

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled and incinerated shares of each material [kg]. The ammonia
    # line reads the A1-3 quantity, which equals the C3 one.
    AbsorptionChiller_EOL_Landfill_Aluminium = AbsorptionChiller_EOL_Aluminium * LandfillMetals
    AbsorptionChiller_EOL_Inc_Ammonia = AbsorptionChiller_Ammonia * IncinerationHazardous #kg
    AbsorptionChiller_EOL_Landfill_Copper = AbsorptionChiller_EOL_Copper * LandfillMetals
    AbsorptionChiller_EOL_Inc_Electronics = AbsorptionChiller_EOL_Electronics * IncinerationElectronics #kg
    AbsorptionChiller_EOL_Landfill_Electronics = AbsorptionChiller_EOL_Electronics * LandfillElectronics #kg
    AbsorptionChiller_EOL_Inc_PEHD = AbsorptionChiller_EOL_PEHD * IncinerationPEHD
    AbsorptionChiller_EOL_Landfill_PEHD = AbsorptionChiller_EOL_PEHD * LandfillPEHD
    AbsorptionChiller_EOL_Landfill_ReinforcingSteel = AbsorptionChiller_EOL_ReinforcingSteel * LandfillMetals
    AbsorptionChiller_EOL_Landfill_Stonelwool = AbsorptionChiller_EOL_Stonelwool * LandfillMineralWool
    AbsorptionChiller_EOL_Inc_Elastomer = AbsorptionChiller_EOL_Elastomer * IncinerationElastomer
    AbsorptionChiller_EOL_Landfill_Elastomer = AbsorptionChiller_EOL_Elastomer * LandfillElastomer

    # --- Module D1: credit for exported secondary materials ---------------------
    # Only aluminium, copper, PEHD and the reinforcing steel are credited.
    AbsorptionChiller_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * AbsorptionChiller_EOL_Aluminium) - (RecycledContentMetals * AbsorptionChiller_EOL_Aluminium)
    AbsorptionChiller_EOL_Primary_Aluminium = ((RecycledContentMetals * AbsorptionChiller_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * AbsorptionChiller_EOL_Aluminium)) * SRmetals

    AbsorptionChiller_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * AbsorptionChiller_EOL_Copper) - (RecycledContentMetals * AbsorptionChiller_EOL_Copper)
    AbsorptionChiller_EOL_Primary_Copper = ((RecycledContentMetals * AbsorptionChiller_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * AbsorptionChiller_EOL_Copper)) * SRmetals

    AbsorptionChiller_EOL_Recycling_PEHD = (RecyclingPEHD * RecyclingEfficiencyPlastics * AbsorptionChiller_EOL_PEHD) - (RecycledContentPlastic * AbsorptionChiller_EOL_PEHD)
    AbsorptionChiller_EOL_Primary_PEHD = ((RecycledContentPlastic * AbsorptionChiller_EOL_PEHD) - (RecyclingPEHD * RecyclingEfficiencyPlastics * AbsorptionChiller_EOL_PEHD)) * SRinert

    AbsorptionChiller_EOL_Recycling_Steel = (RecyclingMetals * RecyclingEfficiencyMetals * AbsorptionChiller_EOL_ReinforcingSteel) - (RecycledContentMetals * AbsorptionChiller_EOL_ReinforcingSteel)
    AbsorptionChiller_EOL_Primary_Steel = ((RecycledContentMetals * AbsorptionChiller_EOL_ReinforcingSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * AbsorptionChiller_EOL_ReinforcingSteel)) * SRmetals

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    AbsorptionChiller_EOL_EnergyRecoveryHeat_Ammonia = - AbsorptionChiller_EOL_Inc_Ammonia * LHVHazardous * Xincheat
    AbsorptionChiller_EOL_EnergyRecoveryEle_Ammonia = - AbsorptionChiller_EOL_Inc_Ammonia * LHVHazardous * Xincele / config.MJ_PER_KWH

    AbsorptionChiller_EOL_EnergyRecoveryHeat_Electronics = - AbsorptionChiller_EOL_Inc_Electronics * LHVElectronics * Xincheat
    AbsorptionChiller_EOL_EnergyRecoveryEle_Electronics = - AbsorptionChiller_EOL_Inc_Electronics * LHVElectronics * Xincele / config.MJ_PER_KWH

    AbsorptionChiller_EOL_EnergyRecoveryHeat_PEHD = - AbsorptionChiller_EOL_Inc_PEHD * LHVHDPE * Xincheat
    AbsorptionChiller_EOL_EnergyRecoveryEle_PEHD = - AbsorptionChiller_EOL_Inc_PEHD * LHVHDPE * Xincele / config.MJ_PER_KWH

    AbsorptionChiller_EOL_EnergyRecoveryHeat_Elastomer = - AbsorptionChiller_EOL_Inc_Elastomer * LHVElastomer * Xincheat
    AbsorptionChiller_EOL_EnergyRecoveryEle_Elastomer = - AbsorptionChiller_EOL_Inc_Elastomer * LHVElastomer * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyAbsorbed_AbsChiller = EnergyCooling * RSP

    # Collect every 'AbsorptionChiller_' quantity for the exchange rows.
    # locals() is bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("AbsorptionChiller_")}

    return {
        "activity_data": activity_data,
        "sf": SFAbsChiller,
        "replacements": AbsChillerNumberReplacements,
        "bd_names": AbsorptionChiller_BdName,
        "bd_areas": AbsorptionChiller_BdArea,
        "thermal_energy": ThermalEnergyAbsorbed_AbsChiller,
    }
