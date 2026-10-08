"""
electric_heat_pump.py - life-cycle inventory of an electric heat pump.

Two things make this one bigger than the boilers:

  * the cold source. Groundwater and surface-water machines need a borehole
    field, so the ground loop - casing steel, PE pipe, bentonite, cement,
    glycol, drilling water and iron - is inventoried alongside the unit, with
    a module A5 (drilling diesel and site transport). Air and industrial-waste-
    water machines have none of it.
  * the refrigerant. Its mass is computed separately and subtracted from the
    overall mass, then charged again as leakage in B1 and B6.

The electricity consumed is split across up to seven sources by dividing each
by their total; Scenario.validate() rejects a building where all are zero.
See energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the heat pumps.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Electric Heat Pump' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Electric Heat Pump")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]
    LandfillElastomer = eol["LandfillElastomer"]
    LandfillPVC = eol["LandfillPVC"]
    LandfillElectronics = eol["LandfillElectronics"]
    LandfillRefrigerant = eol["LandfillRefrigerant"]
    LandfillPEHD = eol["LandfillPEHD"]
    LandfillConcrete = eol["LandfillConcrete"]
    IncinerationElastomer = eol["IncinerationElastomer"]
    IncinerationPVC = eol["IncinerationPVC"]
    IncinerationElectronics = eol["IncinerationElectronics"]
    IncinerationLubricatingOil = eol["IncinerationLubricatingOil"]
    IncinerationPEHD = eol["IncinerationPEHD"]
    IncinerationHazardous = eol["IncinerationHazardous"]
    RecyclingMetals = eol["RecyclingMetals"]
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingConcrete = eol["RecyclingConcrete"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecyclingEfficiencyConcrete = eol["RecyclingEfficiencyConcrete"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    RecycledContentConcrete = eol["RecycledContentConcrete"]
    SRmetals = eol["SRmetals"]                      # substitution ratios
    SRinert = eol["SRinert"]
    LHVElastomer = eol["LHVElastomer"]              # lower heating values [MJ/kg], for D3
    LHVPVC = eol["LHVPVC"]
    LHVElectronics = eol["LHVElectronics"]
    LHVHazardous = eol["LHVHazardous"]
    LHVHDPE = eol["LHVHDPE"]
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency

    ElectricHeatPump_BdName = energysystem['Building Name']
    ElectricHeatPump_BdArea = energysystem['Zone net floor area [m2]']
    Typology = energysystem['Cold source (Groundwater, Surface water, Industrial waste water, Air)']
    RefrigerantGas = energysystem['Refrigerant gas']
    Power = energysystem['Thermal capacity [kW]']
    EnergyProduced = energysystem['Energy produced [kWh /year]']
    SCOP = energysystem['SCOP']
    ElectricityGrid = energysystem['Energy input from national grid [kWh/year]']
    ElectricityPV = energysystem['Energy input from Photovoltaic system [kWh/year]']
    ElectricityRICE = energysystem['Energy input from CHP-Internal Combustion Engine [kWh/year]']
    ElectricityCombinedCycle = energysystem['Energy input from CHP-Combined cycle [kWh/year]']
    ElectricityGasTurbine = energysystem['Energy input from CHP-Gas Turbine [kWh/year]']
    ElectricityWtE = energysystem['Energy input from CHP-Waste-to-Energy [kWh/year]']
    ElectricityORC = energysystem['Energy input from CHP-Organic Rankine Cycle [kWh/year]']

    # Unit mass [kg] from thermal capacity [kW]: exponential below 40 kW, linear
    # to 1 MW, then a cascade of i units of up to 1 MW above.
    i = np.ceil(Power / 1000)
    conditions = [
        Power < 40,
        (Power >= 40) & (Power <= 1000),
        Power > 1000
    ]
    choices = [
        33.771 * np.exp(0.0758 * Power),
        8.330 * Power + 336.570,
        (8.330 * (Power / i) + 336.570) * i
    ]
    overallmass = np.select(conditions, choices)
    Lifespan = 20        # [years], the machine
    GPLifespan = 80      # [years], the ground loop (currently unused)

    # default parameters
    # The commented-out block is a year-dependent refrigerant choice (R410a/R32
    # giving way to R290); with it disabled the gas comes from the workbook.
    # refrigerantgas = np.where(
    #     Typology.eq('Groundwater') | Typology.eq('Air'),
    #     np.where((Year >= 2020) & (Year <= 2029), 'R410a', 'R290'),
    #     np.where(
    #         Typology.eq('Surface water'),
    #         np.where((Year >= 2020) & (Year <= 2039), 'R32', 'R290'),
    #         np.where((Year >= 2020) & (Year <= 2029), 'R410a', 'R290')
    #     )
    # )
    refrigerantgas = np.array(RefrigerantGas)
    # Whether the cold source needs boreholes ('yes'/'no').
    well = np.where(Typology.eq('Industrial waste water') | Typology.eq('Air'), 'no', 'yes')
    # Number of boreholes (currently unused).
    NW = np.where(
        Typology.eq('Groundwater'), 9 * (35/150),
        np.where(Typology.eq('Surface water'), 2, 0)
    )

    # Refrigerant charge [kg], modular above 1 MW. Subtracted from the overall
    # mass so the material split below covers the machine only.
    i = np.ceil(Power / 1000)
    conditions = [
        Power < 1000,
        Power >= 1000
    ]
    choices = [
        0.322 * Power**0.932,
        0.322 * (Power / i)**0.932 * i
    ]
    M_R = np.select(conditions, choices)
    massrefrigerant = M_R
    mass = overallmass - massrefrigerant

    # --- Module A1-3: product stage --------------------------------------------
    # Material split as a fraction of the machine mass [kg].
    ElectricHeatPump_ReinforcingSteel = 0.58462492250465 * mass
    ElectricHeatPump_LowAlloyedSteel = 0.155920644761314 * mass
    ElectricHeatPump_Copper = 0.173796238892333 * mass
    ElectricHeatPump_Elastomer = 0.0779086588138045 * mass
    ElectricHeatPump_PVC = 0.00774953502789833 * mass
    ElectricHeatPump_Airfun = np.full(len(Power), 1.9)
    ElectricHeatPump_Electronics = np.full(len(Power), 1)
    # Process water [m3] and the shares of it emitted to air and water.
    ElectricHeatPump_WaterConsumption = (5.4 * mass) / 1000
    ElectricHeatPump_EmissionWaterAir = 0.15 * ElectricHeatPump_WaterConsumption
    ElectricHeatPump_EmissionWaterWater = 0.02 * ElectricHeatPump_WaterConsumption
    # Wastewater treatment [m3]. Note: taken as a fraction of the unit mass
    # rather than of the water consumed; open question.
    ElectricHeatPump_WasteWaterTreatment = (0.83 * mass) / 1000
    ElectricHeatPump_LubricatingOil = 0.27 * Power
    ElectricHeatPump_Electricity = 14 * Power                   # [kWh] to manufacture
    ElectricHeatPump_Heat = 136.5 * Power                       # [MJ] to manufacture
    ElectricHeatPump_refrigerantgas = massrefrigerant
    ElectricHeatPump_EthanePentafluoro_MethaneDifluoro = np.zeros(len(Power)) #0.03 * massrefrigerant
    # The ground loop, only for cold sources with boreholes.
    ElectricHeatPump_SteelWell = np.where(well == 'yes', np.full(len(Power), 33), np.zeros(len(Power)))
    ElectricHeatPump_PEwell = np.where(well == 'yes', 4 * Power * 15 * 0.3, np.zeros(len(Power)))
    ElectricHeatPump_BentoniteWell = np.where(well == 'yes', np.full(len(Power), 8), np.zeros(len(Power)))
    ElectricHeatPump_CementWell = np.where(well == 'yes', np.full(len(Power), 33), np.zeros(len(Power)))
    ElectricHeatPump_GlycolEthyleneWell = np.where(well == 'yes', 30 * Power * 0.3 * 1.140, np.zeros(len(Power)))
    ElectricHeatPump_Resourcewaterwell = np.where(well == 'yes', 1.02 * Power * 1000, np.zeros(len(Power)))
    ElectricHeatPump_EmissionWaterAirWell = np.where(well == 'yes', (ElectricHeatPump_Resourcewaterwell - (30 * Power / 1000)) * 0.15, np.zeros(len(Power)))
    ElectricHeatPump_EmissionWaterWaterWell = np.where(well == 'yes', (ElectricHeatPump_Resourcewaterwell - (30 * Power / 1000)) * 0.85, np.zeros(len(Power)))
    ElectricHeatPump_IronWell = np.where(well == 'yes', np.full(len(Power), 43), np.zeros(len(Power)))

    # --- Module A4: transport to site -------------------------------------------
    ElectricHeatPump_Truck1632 = ((500 + 200)*(overallmass)/1000)
    ElectricHeatPump_Light_Truck = (50*(overallmass)/1000)

    # --- Module A5: installation on site ----------------------------------------
    # Drilling diesel [MJ] and site transport of the ground-loop materials
    # [t.km], only for cold sources with boreholes.
    ElectricHeatPump_DieselA5 = np.where(well == 'yes', np.full(len(Power), 5900), np.zeros(len(Power)))
    ElectricHeatPump_Light_TruckA5 = np.where(well == 'yes', (160 * (ElectricHeatPump_SteelWell + ElectricHeatPump_PEwell + ElectricHeatPump_BentoniteWell + ElectricHeatPump_CementWell + ElectricHeatPump_GlycolEthyleneWell) / 1000), np.zeros(len(Power)))
    ElectricHeatPump_Truck1632A5 = np.where(well == 'yes', (180 * (ElectricHeatPump_SteelWell + ElectricHeatPump_PEwell + ElectricHeatPump_BentoniteWell + ElectricHeatPump_CementWell + ElectricHeatPump_GlycolEthyleneWell) / 1000), np.zeros(len(Power)))

    # --- Module B1: use-stage refrigerant leakage -------------------------------
    # 2% of the charge per year over the machine's life; R290 (propane) is
    # exempt as its impact is negligible.
    # Note: the R290 exemption is applied to these two rows and to one of the
    # two B6 rows, but not to ElectricHeatPump_UsePhaseRefrigerantGas. Open
    # question to the inventory authors.
    massrefrigerantB2 = np.array(massrefrigerant)
    ElectricHeatPump_MaintenanceRefrigerantGas = np.where(refrigerantgas == 'R290', np.zeros(len(Power)), 0.02 * massrefrigerant * Lifespan)
    ElectricHeatPump_MaintenanceEthanePentafluoro_MethaneDifluoro = np.where(refrigerantgas == 'R290', np.zeros(len(Power)), 0.02 * massrefrigerant * Lifespan)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the machine mass.
    ElectricHeatPump_Light_Truck_B2 = np.array(50 * (Lifespan / 2) * 0.01 * (mass / 1000))  # Light_Truk_B2 come array

    # --- Module B4: replacement within the study period -------------------------
    EHPNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFEHP = (RSP / Lifespan)  # Scaling factor

    # --- Module B6: operational energy over the study period --------------------
    # Each source's share of the electricity the pump draws.
    TotalElectricityInput = (ElectricityGrid + ElectricityPV + ElectricityRICE + ElectricityCombinedCycle +
        ElectricityGasTurbine + ElectricityWtE + ElectricityORC)
    ElectricHeatPump_EleGrid = ElectricityGrid / TotalElectricityInput
    ElectricHeatPump_ElePV = ElectricityPV / TotalElectricityInput
    ElectricHeatPump_EleRICE = ElectricityRICE / TotalElectricityInput
    ElectricHeatPump_EleCombinedCycle = ElectricityCombinedCycle / TotalElectricityInput
    ElectricHeatPump_EleGasTurbine = ElectricityGasTurbine / TotalElectricityInput
    ElectricHeatPump_EleWtE = ElectricityWtE / TotalElectricityInput
    ElectricHeatPump_EleORC = ElectricityORC / TotalElectricityInput

    # Electricity drawn over the study period [kWh]: heat delivered / SCOP x RSP,
    # times each source's share.
    ElectricHeatPump_UsePhaseElectricity = (1 / SCOP) * EnergyProduced * RSP * ElectricHeatPump_EleGrid
    ElectricHeatPump_UsephaseelectricityPV = (1 / SCOP) * EnergyProduced * RSP * ElectricHeatPump_ElePV
    # ElectricHeatPump_usephaseelectricityRECSPV = ElectricHeatPump_UsePhaseElectricity * 0.0056 * RECSPV
    # ElectricHeatPump_usephaseelectricityRECSHydro = ElectricHeatPump_UsePhaseElectricity * 0.0056 * RECSHydro
    # ElectricHeatPump_usephaseelectricityRECSEolic = ElectricHeatPump_UsePhaseElectricity * 0.0056 * RECSEolic
    # Operating leakage, 4% of the charge per year (see the B1 note on R290).
    ElectricHeatPump_UsePhaseRefrigerantGas = 0.04 * massrefrigerant * RSP
    ElectricHeatPump_UsePhaseEthanePentafluoro_MethaneDifluoro = np.where(refrigerantgas == 'R290', np.zeros(len(Power)), 0.04 * massrefrigerant * RSP)

    # --- Module C2: transport to treatment --------------------------------------
    ElectricHeatPump_Transport_To_Treatment_Plant = 50 * (overallmass/1000)

    # --- Module C3: waste processing --------------------------------------------
    ElectricHeatPump_EOL_ReinforcingSteel = ElectricHeatPump_ReinforcingSteel
    ElectricHeatPump_EOL_LowAlloyedSteel = ElectricHeatPump_LowAlloyedSteel
    ElectricHeatPump_EOL_Copper = ElectricHeatPump_Copper
    ElectricHeatPump_EOL_Elastomer = ElectricHeatPump_Elastomer
    ElectricHeatPump_EOL_PVC = ElectricHeatPump_PVC
    ElectricHeatPump_EOL_Airfun = ElectricHeatPump_Airfun
    ElectricHeatPump_EOL_Electronics = ElectricHeatPump_Electronics
    ElectricHeatPump_EOL_lubricatingoil = ElectricHeatPump_LubricatingOil
    ElectricHeatPump_EOL_RefrigerantGas = massrefrigerant
    ElectricHeatPump_EOL_SteelWell =  ElectricHeatPump_SteelWell
    ElectricHeatPump_EOL_PEwell = ElectricHeatPump_PEwell
    ElectricHeatPump_EOL_BentoniteWell = ElectricHeatPump_BentoniteWell
    ElectricHeatPump_EOL_CementWell = ElectricHeatPump_CementWell
    ElectricHeatPump_EOL_glycolethylenewell = ElectricHeatPump_GlycolEthyleneWell
    ElectricHeatPump_EOL_IronWell = ElectricHeatPump_IronWell

    # --- Module C4: final disposal ----------------------------------------------
    ElectricHeatPump_EOL_Landfill_ReinforcingSteel = ElectricHeatPump_EOL_ReinforcingSteel * LandfillMetals
    ElectricHeatPump_EOL_Landfill_LowAlloyedSteel = ElectricHeatPump_EOL_LowAlloyedSteel * LandfillMetals
    ElectricHeatPump_EOL_Landfill_Copper = ElectricHeatPump_EOL_Copper * LandfillMetals
    ElectricHeatPump_EOL_Inc_Elastomer = ElectricHeatPump_EOL_Elastomer * IncinerationElastomer
    ElectricHeatPump_EOL_Landfill_Elastomer = ElectricHeatPump_EOL_Elastomer * LandfillElastomer
    ElectricHeatPump_EOL_Inc_PVC = ElectricHeatPump_EOL_PVC * IncinerationPVC
    ElectricHeatPump_EOL_Landfill_PVC = ElectricHeatPump_EOL_PVC * LandfillPVC
    ElectricHeatPump_EOL_Landfill_Airfun = ElectricHeatPump_EOL_Airfun * LandfillMetals
    ElectricHeatPump_EOL_Inc_Electronics = ElectricHeatPump_EOL_Electronics * IncinerationElectronics #kg
    ElectricHeatPump_EOL_Landfill_Electronics = ElectricHeatPump_EOL_Electronics * LandfillElectronics #kg
    ElectricHeatPump_EOL_Inc_LubricatingOil = ElectricHeatPump_EOL_lubricatingoil * IncinerationLubricatingOil #kg
    ElectricHeatPump_EOL_Landfill_RefrigerantGas = ElectricHeatPump_EOL_RefrigerantGas * LandfillRefrigerant
    ElectricHeatPump_EOL_Landfill_SteelWell = ElectricHeatPump_EOL_SteelWell * LandfillMetals
    ElectricHeatPump_EOL_Inc_PEwell = ElectricHeatPump_EOL_PEwell * IncinerationPEHD
    ElectricHeatPump_EOL_Landfill_PEwell = ElectricHeatPump_EOL_PEwell * LandfillPEHD
    ElectricHeatPump_EOL_Inc_BentoniteWell = ElectricHeatPump_EOL_BentoniteWell * IncinerationHazardous #kg
    ElectricHeatPump_EOL_Landfill_CementWell = ElectricHeatPump_EOL_CementWell * LandfillConcrete
    ElectricHeatPump_EOL_Inc_GlycolEthyleneWell = ElectricHeatPump_EOL_glycolethylenewell * IncinerationHazardous #kg
    ElectricHeatPump_EOL_Landfill_IronWell = ElectricHeatPump_EOL_IronWell * LandfillMetals

    # --- Module D1: credit for exported secondary materials ---------------------
    ElectricHeatPump_EOL_Recycling_ReinforcingSteel = (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_ReinforcingSteel) - (RecycledContentMetals * ElectricHeatPump_EOL_ReinforcingSteel)
    ElectricHeatPump_EOL_Primary_ReinforcingSteel = ((RecycledContentMetals * ElectricHeatPump_EOL_ReinforcingSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_ReinforcingSteel)) * SRmetals
    ElectricHeatPump_EOL_Recycling_LowAlloyedSteel = (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_LowAlloyedSteel) - (RecycledContentMetals * ElectricHeatPump_EOL_LowAlloyedSteel)
    ElectricHeatPump_EOL_Primary_LowAlloyedSteel = ((RecycledContentMetals * ElectricHeatPump_EOL_LowAlloyedSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_LowAlloyedSteel)) * SRmetals
    ElectricHeatPump_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_Copper) - (RecycledContentMetals * ElectricHeatPump_EOL_Copper)
    ElectricHeatPump_EOL_Primary_Copper = ((RecycledContentMetals * ElectricHeatPump_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_Copper)) * SRmetals
    ElectricHeatPump_EOL_Recycling_Airfun = (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_Airfun) - (RecycledContentMetals * ElectricHeatPump_EOL_Airfun)
    ElectricHeatPump_EOL_Primary_Airfun = ((RecycledContentMetals * ElectricHeatPump_EOL_Airfun) - (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_Airfun)) * SRmetals
    ElectricHeatPump_EOL_Recycling_SteelWell = (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_SteelWell) - (RecycledContentMetals * ElectricHeatPump_EOL_SteelWell)
    ElectricHeatPump_EOL_Primary_SteelWell = ((RecycledContentMetals * ElectricHeatPump_EOL_SteelWell) - (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_SteelWell)) * SRmetals
    ElectricHeatPump_EOL_Recycling_PEwell = (RecyclingPEHD * RecyclingEfficiencyPlastics * ElectricHeatPump_EOL_PEwell) - (RecycledContentPlastic * ElectricHeatPump_EOL_PEwell)
    ElectricHeatPump_EOL_Primary_PEwell = ((RecycledContentPlastic * ElectricHeatPump_EOL_PEwell) - (RecyclingPEHD * RecyclingEfficiencyPlastics * ElectricHeatPump_EOL_PEwell)) * SRinert
    ElectricHeatPump_EOL_Recycling_CementWell = (RecyclingConcrete * RecyclingEfficiencyConcrete * ElectricHeatPump_EOL_CementWell) - (RecycledContentConcrete * ElectricHeatPump_EOL_CementWell)
    # The well cement is in [kg]; the primary concrete dataset is sold in [m3].
    ElectricHeatPump_EOL_Primary_CementWell = (((RecycledContentConcrete * ElectricHeatPump_EOL_CementWell) - (RecyclingConcrete * RecyclingEfficiencyConcrete * ElectricHeatPump_EOL_CementWell)) * SRinert) / config.CONCRETE_DENSITY
    ElectricHeatPump_EOL_Recycling_IronWell = (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_IronWell) - (RecycledContentMetals * ElectricHeatPump_EOL_IronWell)
    ElectricHeatPump_EOL_Primary_IronWell = ((RecycledContentMetals * ElectricHeatPump_EOL_IronWell) - (RecyclingMetals * RecyclingEfficiencyMetals * ElectricHeatPump_EOL_IronWell)) * SRmetals

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    ElectricHeatPump_EOL_EnergyRecoveryHeat_Elastomer = - ElectricHeatPump_EOL_Inc_Elastomer * LHVElastomer * Xincheat
    ElectricHeatPump_EOL_EnergyRecoveryEle_Elastomer = - ElectricHeatPump_EOL_Inc_Elastomer * LHVElastomer * Xincele / config.MJ_PER_KWH
    ElectricHeatPump_EOL_EnergyRecoveryHeat_PVC = - ElectricHeatPump_EOL_Inc_PVC * LHVPVC * Xincheat
    ElectricHeatPump_EOL_EnergyRecoveryEle_PVC = - ElectricHeatPump_EOL_Inc_PVC * LHVPVC * Xincele / config.MJ_PER_KWH
    ElectricHeatPump_EOL_EnergyRecoveryHeat_Electronics = - ElectricHeatPump_EOL_Inc_Electronics * LHVElectronics * Xincheat
    ElectricHeatPump_EOL_EnergyRecoveryEle_Electronics = - ElectricHeatPump_EOL_Inc_Electronics * LHVElectronics * Xincele / config.MJ_PER_KWH
    ElectricHeatPump_EOL_EnergyRecoveryHeat_LubricatingOil = - ElectricHeatPump_EOL_Inc_LubricatingOil * LHVHazardous * Xincheat
    ElectricHeatPump_EOL_EnergyRecoveryEle_LubricatingOil = - ElectricHeatPump_EOL_Inc_LubricatingOil * LHVHazardous * Xincele / config.MJ_PER_KWH
    ElectricHeatPump_EOL_EnergyRecoveryHeat_PEwell = - ElectricHeatPump_EOL_Inc_PEwell * LHVHDPE * Xincheat
    ElectricHeatPump_EOL_EnergyRecoveryEle_PEwell = - ElectricHeatPump_EOL_Inc_PEwell * LHVHDPE * Xincele / config.MJ_PER_KWH
    ElectricHeatPump_EOL_EnergyRecoveryHeat_BentoniteWell = - ElectricHeatPump_EOL_Inc_BentoniteWell * LHVHazardous * Xincheat
    ElectricHeatPump_EOL_EnergyRecoveryEle_BentoniteWell = - ElectricHeatPump_EOL_Inc_BentoniteWell * LHVHazardous * Xincele / config.MJ_PER_KWH
    ElectricHeatPump_EOL_EnergyRecoveryHeat_GlycolEthyleneWell = - ElectricHeatPump_EOL_Inc_GlycolEthyleneWell * LHVHazardous * Xincheat
    ElectricHeatPump_EOL_EnergyRecoveryEle_GlycolEthyleneWell = - ElectricHeatPump_EOL_Inc_GlycolEthyleneWell * LHVHazardous * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_EHP = np.array([EnergyProduced * RSP])

    # Collect every 'ElectricHeatPump_' quantity for the exchange rows.
    loc = locals()
    return {
        "activity_data": {name: value for name, value in loc.items()
                          if name.startswith("ElectricHeatPump_")},
        "sf": SFEHP,
        "replacements": EHPNumberReplacements,
        "bd_names": ElectricHeatPump_BdName,
        "bd_areas": ElectricHeatPump_BdArea,
        "thermal_energy": ThermalEnergyProduced_EHP,
    }
