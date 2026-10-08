"""
gas_absorption_heat_pump.py - life-cycle inventory of a gas absorption heat pump.

An absorption machine driven by burning gas rather than by a compressor: its
working pair is the ammonia and water inventoried in A1-3, and its use phase is
combustion emissions rather than electricity.

Efficiency is expressed as SGUE, the seasonal gas utilisation efficiency, so
the gas burned over the study period is EnergyProduced / SGUE x RSP, and every
B6 emission factor multiplies that. See energy_systems/__init__.py for the
conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the heat pumps.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Gas Absorption Heat Pump'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Gas Absorption Heat Pump")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]
    LandfillMetals2 = eol["LandfillMetals2"]
    LandfillMineralWool = eol["LandfillMineralWool"]
    LandfillElastomer = eol["LandfillElastomer"]
    LandfillElectronics = eol["LandfillElectronics"]
    LandfillPUfoam = eol["LandfillPUfoam"]
    IncinerationElastomer = eol["IncinerationElastomer"]
    IncinerationElectronics = eol["IncinerationElectronics"]
    IncinerationHazardous = eol["IncinerationHazardous"]
    RecyclingMetals = eol["RecyclingMetals"]
    RecyclingMetals2 = eol["RecyclingMetals2"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                      # substitution ratio, secondary vs primary
    LHVElastomer = eol["LHVElastomer"]              # lower heating values [MJ/kg], for D3
    LHVElectronics = eol["LHVElectronics"]
    LHVHazardous = eol["LHVHazardous"]
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency

    GasAbsorptionHeatPump_BdName = energysystem['Building Name']
    GasAbsorptionHeatPump_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Thermal capacity [kW]']
    EnergyProduced = energysystem['Energy produced [kWh /year]']
    SGUE = energysystem['SGUE']       # seasonal gas utilisation efficiency [-]

    def calculate_mass(Power):
        """Unit mass [kg] from thermal capacity [kW].

        Linear below 40 kW; above it, i units of up to 40 kW each.
        """
        if Power < 40:
            return (8.80 * Power + 16.339)
        else:
            i = np.ceil(Power / 40)
            return (8.80 * (Power / i) + 16.339) * i

    mass = Power.apply(calculate_mass)
    Lifespan = 21        # [years]

    # --- Module A1-3: product stage --------------------------------------------
    # Material split as a fraction of unit mass [kg]. ABS and PTFE are
    # commented out, so those materials are not inventoried.
    GasAbsorptionHeatPump_Copper = 0.00836823451596883 * mass
    GasAbsorptionHeatPump_Aluminium = 0.0223154922991968 * mass
    GasAbsorptionHeatPump_LowAlloyedSteel = 0.0147316866978209 * mass
    GasAbsorptionHeatPump_StainlessSteel = 0.588455354108063 * mass
    GasAbsorptionHeatPump_Ferrite = 0.00367632500737107 * mass
    GasAbsorptionHeatPump_Brass = 0.000428949095362739 * mass
    GasAbsorptionHeatPump_Alumina = 0.00258582093128782 * mass
    #GasAbsorptionHeatPump_ABS = 0.00104095820607209 * mass
    #GasAbsorptionHeatPump_PTFE = 0.000318122042965086 * mass
    GasAbsorptionHeatPump_NBR = 8.57898190725478E-05 * mass
    GasAbsorptionHeatPump_SyntheticRubber = 0.000857898190725478 * mass
    # The working pair: ammonia is the refrigerant, water the absorbent.
    GasAbsorptionHeatPump_Ammonia = 0.0283297913027938 * mass
    GasAbsorptionHeatPump_Water = 0.0495771347798891 * mass
    GasAbsorptionHeatPump_Electronics = 0.0257369457217643 * mass
    GasAbsorptionHeatPump_MineralWool = 0.0127330963856069 * mass
    GasAbsorptionHeatPump_PUfoam =  0.0170228561304905 * mass
    GasAbsorptionHeatPump_EPDM =  0.00476639971653733 * mass
    GasAbsorptionHeatPump_BatterySteel = 0.104731697222516 * mass
    GasAbsorptionHeatPump_BatteryAluminium =  0.0748083551589398 * mass
    GasAbsorptionHeatPump_Airfun = 0.00424925081081468 * mass
    GasAbsorptionHeatPump_Pump =  0.0207611362155566 * mass
    GasAbsorptionHeatPump_LubricatingOil = 0.00171579638145096 * mass
    # Weld length [m] per kg of unit mass (the welding dataset is sold in metres).
    GasAbsorptionHeatPump_Welding = 0.0127029092597341 * mass
    # Process water and the shares of it emitted to air and water.
    GasAbsorptionHeatPump_WaterConsumption = 0.0122 * mass
    GasAbsorptionHeatPump_EmissionsWaterAir = 0.15 * GasAbsorptionHeatPump_WaterConsumption
    GasAbsorptionHeatPump_EmissionsWaterWater = 0.02 * GasAbsorptionHeatPump_WaterConsumption
    # Wastewater treatment [m3]. Note: taken as a fraction of the unit mass
    # rather than of the water consumed; open question.
    GasAbsorptionHeatPump_WastewaterTreatment = (0.83 * mass) / 1000
    GasAbsorptionHeatPump_ElectricityA13 = 0.532 * mass              # [kWh] to manufacture
    GasAbsorptionHeatPump_Heat = 3.8 * mass                          # [MJ] to manufacture
    GasAbsorptionHeatPump_HazardousWaste = 0.0006 * mass

    # --- Module A4: transport to site -------------------------------------------
    GasAbsorptionHeatPump_Truck1632 = ((500 + 200)*(mass)/1000)
    GasAbsorptionHeatPump_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    GasAbsorptionHeatPump_Light_Truck_B2 = np.array(50 * (Lifespan / 2) * 0.01 * (mass / 1000))  # Light_Truk_B2 come array

    # --- Module B4: replacement within the study period -------------------------
    GAHPNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFGAHP = (RSP / Lifespan)  # Scaling factor

    # --- Module B6: operational combustion emissions ----------------------------
    # (1 / SGUE) * EnergyProduced * RSP is the gas burned over the study period;
    # each factor turns it into one emitted substance.
    # Note: the fossil CO2 factor here (0.05406) differs from the gas boiler's
    # (0.056); open question to the inventory authors.
    GasAbsorptionHeatPump_Acetaldehyde = 0.000000001 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_AceticAcid = 0.00000015 * (1 / SGUE)  * EnergyProduced * RSP
    GasAbsorptionHeatPump_Benzene = 0.0000004 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Benzoapyrene = 0.00000000001 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Butane = 0.0000007 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_CarbonDioxideFossil = 0.05406 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_CarbonMonoxideFossil = 0.00003 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_DinitrogenMonoxide = 0.0000005 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Formaldehyde = 0.0000001 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Mercury = 0.00000000003 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_MethaneFossil = 0.000002 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_NitrogenOxides = 0.00002 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_PAH = 0.00000001 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Particulates = 0.0000001 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Pentane = 0.0000012 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Propane = 0.0000002 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_PropionicAcid = 0.00000002 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_SulfurDioxide = 0.0000005 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Toluene = 0.0000002 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Nitrate = 0.00000013 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Nitrite = 0.000000003 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Sulfate = 0.00000005 * (1 / SGUE) * EnergyProduced * RSP
    GasAbsorptionHeatPump_Sulfite = 0.00000005 * (1 / SGUE) * EnergyProduced * RSP

    # --- Module C2: transport to treatment --------------------------------------
    GasAbsorptionHeatPump_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    GasAbsorptionHeatPump_EOL_Copper  = GasAbsorptionHeatPump_Copper
    GasAbsorptionHeatPump_EOL_Aluminium  = GasAbsorptionHeatPump_Aluminium
    GasAbsorptionHeatPump_EOL_LowAlloyedSteel  = GasAbsorptionHeatPump_LowAlloyedSteel
    GasAbsorptionHeatPump_EOL_StainlessSteel  = GasAbsorptionHeatPump_StainlessSteel
    GasAbsorptionHeatPump_EOL_Ferrite  = GasAbsorptionHeatPump_Ferrite
    GasAbsorptionHeatPump_EOL_Brass  = GasAbsorptionHeatPump_Brass
    GasAbsorptionHeatPump_EOL_Alumina  = GasAbsorptionHeatPump_Alumina
    #GasAbsorptionHeatPump_EOL_ABS  = GasAbsorptionHeatPump_ABS
    #GasAbsorptionHeatPump_EOL_PTFE  = GasAbsorptionHeatPump_PTFE
    GasAbsorptionHeatPump_EOL_NBR  = GasAbsorptionHeatPump_NBR
    GasAbsorptionHeatPump_EOL_SyntheticRubber  = GasAbsorptionHeatPump_SyntheticRubber
    GasAbsorptionHeatPump_EOL_ammonia  = GasAbsorptionHeatPump_Ammonia
    GasAbsorptionHeatPump_EOL_Electronics  = GasAbsorptionHeatPump_Electronics
    GasAbsorptionHeatPump_EOL_MineralWool  = GasAbsorptionHeatPump_MineralWool
    GasAbsorptionHeatPump_EOL_PUfoam  = GasAbsorptionHeatPump_PUfoam
    GasAbsorptionHeatPump_EOL_EPDM  = GasAbsorptionHeatPump_EPDM
    GasAbsorptionHeatPump_EOL_BatterySteel  = GasAbsorptionHeatPump_BatterySteel
    GasAbsorptionHeatPump_EOL_BatteryAluminium  = GasAbsorptionHeatPump_BatteryAluminium
    GasAbsorptionHeatPump_EOL_Airfun  = GasAbsorptionHeatPump_Airfun
    GasAbsorptionHeatPump_EOL_Pump  = GasAbsorptionHeatPump_Pump
    GasAbsorptionHeatPump_EOL_hazardouswaste  = GasAbsorptionHeatPump_HazardousWaste

    # --- Module C4: final disposal ----------------------------------------------
    # Despite its name, GasAbsorptionHeatPump_EOL_Landfill_Ammonia is an
    # incineration flow: scaled by IncinerationHazardous and wired to hazardous
    # waste incineration with energy recovery.
    GasAbsorptionHeatPump_EOL_Landfill_Copper  = GasAbsorptionHeatPump_EOL_Copper  * LandfillMetals
    GasAbsorptionHeatPump_EOL_Landfill_Aluminium  = GasAbsorptionHeatPump_EOL_Aluminium  * LandfillMetals
    GasAbsorptionHeatPump_EOL_Landfill_LowAlloyedSteel  = GasAbsorptionHeatPump_EOL_LowAlloyedSteel  * LandfillMetals
    GasAbsorptionHeatPump_EOL_Landfill_StainlessSteel  = GasAbsorptionHeatPump_EOL_StainlessSteel  * LandfillMetals2
    GasAbsorptionHeatPump_EOL_Landfill_Ferrite  = GasAbsorptionHeatPump_EOL_Ferrite  * LandfillMetals
    GasAbsorptionHeatPump_EOL_Landfill_Brass  = GasAbsorptionHeatPump_EOL_Brass  * LandfillMetals
    GasAbsorptionHeatPump_EOL_Landfill_Alumina  = GasAbsorptionHeatPump_EOL_Alumina  * LandfillMetals
    GasAbsorptionHeatPump_EOL_Inc_NBR  = GasAbsorptionHeatPump_EOL_NBR * IncinerationElastomer
    GasAbsorptionHeatPump_EOL_Landfill_NBR  = GasAbsorptionHeatPump_EOL_NBR * LandfillElastomer
    GasAbsorptionHeatPump_EOL_Inc_SyntheticRubber  = GasAbsorptionHeatPump_EOL_SyntheticRubber * IncinerationElastomer
    GasAbsorptionHeatPump_EOL_Landfill_SyntheticRubber  = GasAbsorptionHeatPump_EOL_SyntheticRubber * LandfillElastomer
    GasAbsorptionHeatPump_EOL_Landfill_Ammonia  = GasAbsorptionHeatPump_EOL_ammonia * IncinerationHazardous
    GasAbsorptionHeatPump_EOL_Inc_Electronics  = GasAbsorptionHeatPump_EOL_Electronics * IncinerationElectronics
    GasAbsorptionHeatPump_EOL_Landfill_Electronics  = GasAbsorptionHeatPump_EOL_Electronics * LandfillElectronics
    GasAbsorptionHeatPump_EOL_Landfill_MineralWool  = GasAbsorptionHeatPump_EOL_MineralWool * LandfillMineralWool
    GasAbsorptionHeatPump_EOL_Landfill_PUfoam  = GasAbsorptionHeatPump_EOL_PUfoam * LandfillPUfoam
    GasAbsorptionHeatPump_EOL_Inc_EPDM  = GasAbsorptionHeatPump_EOL_EPDM * IncinerationElastomer
    GasAbsorptionHeatPump_EOL_Landfill_EPDM  = GasAbsorptionHeatPump_EOL_EPDM * LandfillElastomer
    GasAbsorptionHeatPump_EOL_Landfill_BatterySteel  = GasAbsorptionHeatPump_EOL_BatterySteel  * LandfillMetals
    GasAbsorptionHeatPump_EOL_Landfill_BatteryAluminium  = GasAbsorptionHeatPump_EOL_BatteryAluminium  * LandfillMetals
    GasAbsorptionHeatPump_EOL_Landfill_Airfun  = GasAbsorptionHeatPump_EOL_Airfun  * LandfillMetals2
    GasAbsorptionHeatPump_EOL_Landfill_Pump  = GasAbsorptionHeatPump_EOL_Pump   * LandfillMetals2
    GasAbsorptionHeatPump_EOL_Inc_HazardousWaste  = GasAbsorptionHeatPump_EOL_hazardouswaste * IncinerationHazardous

    # --- Module D1: credit for exported secondary materials ---------------------
    GasAbsorptionHeatPump_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_Copper) - (RecycledContentMetals * GasAbsorptionHeatPump_EOL_Copper)
    GasAbsorptionHeatPump_EOL_Primary_Copper = ((RecycledContentMetals * GasAbsorptionHeatPump_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_Copper)) * SRmetals
    GasAbsorptionHeatPump_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_Aluminium) - (RecycledContentMetals * GasAbsorptionHeatPump_EOL_Aluminium)
    GasAbsorptionHeatPump_EOL_Primary_Aluminium = ((RecycledContentMetals * GasAbsorptionHeatPump_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_Aluminium))* SRmetals
    GasAbsorptionHeatPump_EOL_Recycling_LowAlloyedSteel = (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_LowAlloyedSteel) - (RecycledContentMetals * GasAbsorptionHeatPump_EOL_LowAlloyedSteel)
    GasAbsorptionHeatPump_EOL_Primary_LowAlloyedSteel = ((RecycledContentMetals * GasAbsorptionHeatPump_EOL_LowAlloyedSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_LowAlloyedSteel)) * SRmetals
    GasAbsorptionHeatPump_EOL_Recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_StainlessSteel) - (RecycledContentMetals * GasAbsorptionHeatPump_EOL_StainlessSteel)
    GasAbsorptionHeatPump_EOL_Primary_StainlessSteel = ((RecycledContentMetals * GasAbsorptionHeatPump_EOL_StainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_StainlessSteel))* SRmetals
    GasAbsorptionHeatPump_EOL_Recycling_BatterySteel = (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_BatterySteel) - (RecycledContentMetals * GasAbsorptionHeatPump_EOL_BatterySteel)
    GasAbsorptionHeatPump_EOL_Primary_BatterySteel = ((RecycledContentMetals * GasAbsorptionHeatPump_EOL_BatterySteel) - (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_BatterySteel)) * SRmetals
    GasAbsorptionHeatPump_EOL_Recycling_BatteryAluminium = (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_BatteryAluminium) - (RecycledContentMetals * GasAbsorptionHeatPump_EOL_BatteryAluminium)
    GasAbsorptionHeatPump_EOL_Primary_BatteryAluminium = ((RecycledContentMetals * GasAbsorptionHeatPump_EOL_BatteryAluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_BatteryAluminium))* SRmetals
    GasAbsorptionHeatPump_EOL_Recycling_Airfun = (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_Airfun) - (RecycledContentMetals * GasAbsorptionHeatPump_EOL_Airfun)
    GasAbsorptionHeatPump_EOL_Primary_Airfun = ((RecycledContentMetals * GasAbsorptionHeatPump_EOL_Airfun) - (RecyclingMetals * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_Airfun)) * SRmetals
    GasAbsorptionHeatPump_EOL_Recycling_Pump = (RecyclingMetals2 * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_Pump) - (RecycledContentMetals * GasAbsorptionHeatPump_EOL_Pump)
    GasAbsorptionHeatPump_EOL_Primary_Pump = ((RecycledContentMetals * GasAbsorptionHeatPump_EOL_Pump) - (RecyclingMetals2 * RecyclingEfficiencyMetals * GasAbsorptionHeatPump_EOL_Pump))* SRmetals

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    GasAbsorptionHeatPump_EOL_EnergyRecoveryHeat_NBR = - GasAbsorptionHeatPump_EOL_Inc_NBR * LHVElastomer * Xincheat
    GasAbsorptionHeatPump_EOL_EnergyRecoveryEle_NBR = - GasAbsorptionHeatPump_EOL_Inc_NBR * LHVElastomer * Xincele / config.MJ_PER_KWH
    GasAbsorptionHeatPump_EOL_EnergyRecoveryHeat_SyntheticRubber = - GasAbsorptionHeatPump_EOL_Inc_SyntheticRubber * LHVElastomer * Xincheat
    GasAbsorptionHeatPump_EOL_EnergyRecoveryEle_SyntheticRubber = - GasAbsorptionHeatPump_EOL_Inc_SyntheticRubber * LHVElastomer * Xincele / config.MJ_PER_KWH
    GasAbsorptionHeatPump_EOL_EnergyRecoveryHeat_Electronics = - GasAbsorptionHeatPump_EOL_Inc_Electronics * LHVElectronics * Xincheat
    GasAbsorptionHeatPump_EOL_EnergyRecoveryEle_Electronics = - GasAbsorptionHeatPump_EOL_Inc_Electronics * LHVElectronics * Xincele / config.MJ_PER_KWH
    GasAbsorptionHeatPump_EOL_EnergyRecoveryHeat_EPDM = - GasAbsorptionHeatPump_EOL_Inc_EPDM * LHVElastomer * Xincheat
    GasAbsorptionHeatPump_EOL_EnergyRecoveryEle_EPDM = - GasAbsorptionHeatPump_EOL_Inc_EPDM * LHVElastomer * Xincele / config.MJ_PER_KWH
    GasAbsorptionHeatPump_EOL_EnergyRecoveryHeat_HazardousWaste = - GasAbsorptionHeatPump_EOL_Inc_HazardousWaste * LHVHazardous * Xincheat
    GasAbsorptionHeatPump_EOL_EnergyRecoveryEle_HazardousWaste = - GasAbsorptionHeatPump_EOL_Inc_HazardousWaste * LHVHazardous * Xincele / config.MJ_PER_KWH
    # The incinerated ammonia (see the C4 note), as in absorption_chiller.py.
    GasAbsorptionHeatPump_EOL_EnergyRecoveryHeat_Ammonia = - GasAbsorptionHeatPump_EOL_Landfill_Ammonia * LHVHazardous * Xincheat
    GasAbsorptionHeatPump_EOL_EnergyRecoveryEle_Ammonia = - GasAbsorptionHeatPump_EOL_Landfill_Ammonia * LHVHazardous * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_GAHP = np.array([EnergyProduced * RSP])

    # Collect every 'GasAbsorptionHeatPump_' quantity for the exchange rows.
    loc = locals()
    return {
        "activity_data": {name: value for name, value in loc.items()
                          if name.startswith("GasAbsorptionHeatPump_")},
        "sf": SFGAHP,
        "replacements": GAHPNumberReplacements,
        "bd_names": GasAbsorptionHeatPump_BdName,
        "bd_areas": GasAbsorptionHeatPump_BdArea,
        "thermal_energy": ThermalEnergyProduced_GAHP,
    }
