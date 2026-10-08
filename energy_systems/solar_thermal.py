"""
solar_thermal.py - life-cycle inventory of a solar thermal system.

Collectors plus a hot-water store, sized from the building's thermal capacity
and the solar resource at its location (North-, Centre- or South-Italy, checked
by Scenario.validate()). See energy_systems/__init__.py for the conventions
shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Solar thermal system'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Solar thermal system")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillCardboard = eol["LandfillCardboard"]
    LandfillElastomer = eol["LandfillElastomer"]
    LandfillGlass = eol["LandfillGlass"]
    LandfillMetals = eol["LandfillMetals"]      # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]    # share of special metals landfilled
    LandfillMineralWool = eol["LandfillMineralWool"]
    LandfillPEHD = eol["LandfillPEHD"]
    IncinerationCardboard = eol["IncinerationCardboard"]
    IncinerationElastomer = eol["IncinerationElastomer"]
    IncinerationPEHD = eol["IncinerationPEHD"]
    RecyclingCardboard = eol["RecyclingCardboard"]
    RecyclingMetals = eol["RecyclingMetals"]    # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]  # share of special metals recycled
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingEfficiencyCardboard = eol["RecyclingEfficiencyCardboard"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecycledContentCardboard = eol["RecycledContentCardboard"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    SRmetals = eol["SRmetals"]                  # substitution ratios, secondary vs primary
    SRinert = eol["SRinert"]
    LHVCardboard = eol["LHVCardboard"]          # lower heating values [MJ/kg], for the
    LHVElastomer = eol["LHVElastomer"]          # energy recovered by incineration (D3)
    LHVHDPE = eol["LHVHDPE"]
    Xincheat = eol["Xincheat"]                  # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                    # electricity recovery efficiency

    # DASHBOARD - VALUE INPUTS and sizing.
    # Solar irradiance [kW/m2] by location: 0.8 north, 1.0 centre, 1.2 south.
    # surface [m2] is the collector area for the requested capacity; storage is
    # 50 l per m2 of collector, in units of the 2000 l ecoinvent store;
    # scalingfactor is the area in units of the 12.3 m2 ecoinvent collector.
    # Two lifetimes: 21 years for the collectors, 40 for the store.
    SolarThermal_BdName = energysystem['Building Name']
    SolarThermal_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Thermal capacity [kW]']
    location = energysystem['Location']

    solarirradiance = np.where(
        location == 'North-Italy', 0.8,
        np.where(location == 'Centre-Italy', 1.0,
        np.where(location == 'South-Italy', 1.2, np.nan))
    ) #kW/m2

    solarefficiency = 0.6
    lifespanST = 21 #years
    lifespanStorage = 40 #years
    TotEnergyNeeds = energysystem["Producibility [Insert the value in kWh/ year]"]
    surface = (Power) / (solarefficiency * solarirradiance)
    storage = (50 * surface) / 2000 #Rule of thumb 50 l /m2
    scalingfactor = surface / 12.3 #ecoinvent data

    # --- Module A1-3: manufacture -----------------------------------------------
    # Counts of whole ecoinvent units: 12.3 m2 collectors and 2000 l stores.
    SolarThermal_SolarCollector = scalingfactor
    SolarThermal_Storage = storage #2000 l storage capacity from ecoinvent dataset

    # --- Module A4: transport to site -------------------------------------------
    # Collector array mass [kg] (primary data). Freight [t.km]: 700 km by heavy
    # lorry, 50 km by light lorry.
    mass = 532.8 * scalingfactor #kg primary data

    SolarThermal_Truck1632 = ((500 + 200)*(mass)/1000)
    SolarThermal_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years of the collectors' life,
    # carrying 1% of the mass.
    mass = np.array(mass)
    lifespanST = np.array(lifespanST)
    SolarThermal_Light_Truck_B2 = 50 * (lifespanST/2) * 0.01 * (mass/1000)

    # --- Module B4: replacement within the study period -------------------------
    # Note: both the replacement count and the scaling factor use the store's
    # 40-year life; the collectors' 21-year life is used only in B2. Open
    # question to the inventory authors.
    SolarThermalNumberReplacements = (np.maximum(np.divide(RSP, lifespanStorage) - 1, 0))
    SFSolarThermal = (RSP / lifespanStorage)  # Scaling factor

    # --- Module B6: operating electricity ---------------------------------------
    # Pump and controller electricity [kWh] per collector unit, all charged to
    # the grid (placeholder; no PV row).
    Grid = 1 #temporary
    SolarThermal_Electricity = 0.00015579 * scalingfactor * Grid

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km].
    SolarThermal_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    # The collector's bill of materials [kg] per 12.3 m2 unit, written directly
    # as end-of-life quantities because A1-3 buys whole units.
    SolarThermal_EOL_Copper = 16 * scalingfactor
    SolarThermal_EOL_Steel = (16 + 1.5) * scalingfactor
    SolarThermal_EOL_StainlessSteel = (5 + 261) * scalingfactor
    SolarThermal_EOL_Glass = 9.12 * scalingfactor
    SolarThermal_EOL_MineralWool = 2.43 * scalingfactor
    SolarThermal_EOL_PaperBoard = 3.68 * scalingfactor
    SolarThermal_EOL_Plastic = 0.790 * scalingfactor
    SolarThermal_EOL_Elastomer = 5.2 * scalingfactor

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled and incinerated shares of each material [kg].
    SolarThermal_EOL_Landfill_Copper = SolarThermal_EOL_Copper * LandfillMetals
    SolarThermal_EOL_Landfill_Steel = SolarThermal_EOL_Steel * LandfillMetals
    SolarThermal_EOL_Landfill_StainlessSteel = SolarThermal_EOL_StainlessSteel * LandfillMetals2
    SolarThermal_EOL_Landfill_Glass = SolarThermal_EOL_Glass * LandfillGlass #kg
    SolarThermal_EOL_Landfill_MineralWool = SolarThermal_EOL_MineralWool * LandfillMineralWool
    SolarThermal_EOL_Inc_PaperBoard = SolarThermal_EOL_PaperBoard * IncinerationCardboard
    SolarThermal_EOL_Landfill_PaperBoard = SolarThermal_EOL_PaperBoard * LandfillCardboard
    SolarThermal_EOL_Inc_Plastic = SolarThermal_EOL_Plastic * IncinerationPEHD
    SolarThermal_EOL_Landfill_Plastic = SolarThermal_EOL_Plastic * LandfillPEHD
    SolarThermal_EOL_Inc_Elastomer = SolarThermal_EOL_Elastomer * IncinerationElastomer
    SolarThermal_EOL_Landfill_Elastomer = SolarThermal_EOL_Elastomer * LandfillElastomer

    # --- Module D1: credit for exported secondary materials ---------------------
    # Glass, mineral wool and elastomer earn no credit.
    SolarThermal_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * SolarThermal_EOL_Copper) - (RecycledContentMetals * SolarThermal_EOL_Copper)
    SolarThermal_EOL_Primary_Copper = ((RecycledContentMetals * SolarThermal_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * SolarThermal_EOL_Copper))* SRmetals

    SolarThermal_EOL_Recycling_Steel = (RecyclingMetals * RecyclingEfficiencyMetals * SolarThermal_EOL_Steel) - (RecycledContentMetals * SolarThermal_EOL_Steel)
    SolarThermal_EOL_Primary_Steel = ((RecycledContentMetals * SolarThermal_EOL_Steel) - (RecyclingMetals * RecyclingEfficiencyMetals * SolarThermal_EOL_Steel))* SRmetals

    SolarThermal_EOL_Recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * SolarThermal_EOL_StainlessSteel) - (RecycledContentMetals * SolarThermal_EOL_StainlessSteel)
    SolarThermal_EOL_Primary_StainlessSteel = ((RecycledContentMetals * SolarThermal_EOL_StainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * SolarThermal_EOL_StainlessSteel))* SRmetals

    SolarThermal_EOL_Recycling_PaperBoard = (RecyclingCardboard * RecyclingEfficiencyCardboard * SolarThermal_EOL_PaperBoard) - (RecycledContentCardboard * SolarThermal_EOL_PaperBoard)
    SolarThermal_EOL_Primary_PaperBoard = ((RecycledContentCardboard * SolarThermal_EOL_PaperBoard) - (RecyclingCardboard * RecyclingEfficiencyCardboard * SolarThermal_EOL_PaperBoard)) * SRinert

    SolarThermal_EOL_Recycling_Plastic = (RecyclingPEHD * RecyclingEfficiencyPlastics * SolarThermal_EOL_Plastic) - (RecycledContentPlastic * SolarThermal_EOL_Plastic)
    SolarThermal_EOL_Primary_Plastic = ((RecycledContentPlastic * SolarThermal_EOL_Plastic) - (RecyclingPEHD * RecyclingEfficiencyPlastics * SolarThermal_EOL_Plastic)) * SRinert

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    SolarThermal_EOL_EnergyRecoveryHeat_PaperBoard =  - SolarThermal_EOL_Inc_PaperBoard * LHVCardboard * Xincheat
    SolarThermal_EOL_EnergyRecoveryEle_PaperBoard =  - SolarThermal_EOL_Inc_PaperBoard * LHVCardboard * Xincele / config.MJ_PER_KWH
    SolarThermal_EOL_EnergyRecoveryHeat_Plastic =  - SolarThermal_EOL_Inc_Plastic * LHVHDPE * Xincheat
    SolarThermal_EOL_EnergyRecoveryEle_Plastic =  - SolarThermal_EOL_Inc_Plastic * LHVHDPE * Xincele / config.MJ_PER_KWH
    SolarThermal_EOL_EnergyRecoveryHeat_Elastomer = - SolarThermal_EOL_Inc_Elastomer * LHVElastomer * Xincheat
    SolarThermal_EOL_EnergyRecoveryEle_Elastomer = - SolarThermal_EOL_Inc_Elastomer * LHVElastomer * Xincele / config.MJ_PER_KWH

    # Data for export (informative only: the workbook's Producibility column).
    ThermalEnergyProduced_SolarThermal = TotEnergyNeeds

    # Collect every 'SolarThermal_' quantity for the exchange rows. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("SolarThermal_")}

    return {
        "activity_data": activity_data,
        "sf": SFSolarThermal,
        "replacements": SolarThermalNumberReplacements,
        "bd_names": SolarThermal_BdName,
        "bd_areas": SolarThermal_BdArea,
        "thermal_energy": ThermalEnergyProduced_SolarThermal,
    }
