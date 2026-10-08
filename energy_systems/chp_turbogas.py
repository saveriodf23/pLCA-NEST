"""
chp_turbogas.py - life-cycle inventory of a gas-turbine CHP unit.

An open-cycle gas turbine producing heat and power, burning a gas blend,
biogas or hydrogen. Every quantity is multiplied by AFQ_GasTurbine, the share
of the burden allocated to HEAT: this tool inventories the heat service only,
and the electricity leaves the system boundary. Two allocation methods are
available per building through the 'Multifunctionality Approach' column. See
energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the turbines.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'CHP-Turbogas' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("CHP-Turbogas")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillConcrete = eol["LandfillConcrete"]      # share of concrete landfilled
    LandfillMetals = eol["LandfillMetals"]          # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    LandfillPEHD = eol["LandfillPEHD"]
    IncinerationPEHD = eol["IncinerationPEHD"]
    RecyclingConcrete = eol["RecyclingConcrete"]
    RecyclingMetals = eol["RecyclingMetals"]        # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]      # share of special metals recycled
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingEfficiencyConcrete = eol["RecyclingEfficiencyConcrete"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecycledContentConcrete = eol["RecycledContentConcrete"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    SRmetals = eol["SRmetals"]                      # substitution ratio, secondary vs primary
    SRinert = eol["SRinert"]                        # same, for inert materials
    LHVHDPE = eol["LHVHDPE"]                        # lower heating value [MJ/kg], for the
                                                    # energy recovered by incineration (D3)
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency

    # DASHBOARD - VALUE INPUTS
    # 'Multifunctionality Approach' selects the allocation method; the three
    # temperatures drive the Carnot factor of the default method; the three
    # EnergyInputSource columns [kWh/year] are used only as fuel shares.
    CHP_Turbogas_BdName = energysystem['Building Name']
    CHP_Turbogas_BdArea = energysystem['Zone net floor area [m2]']
    Multifunctionality = energysystem['Multifunctionality Approach']
    Power = energysystem['Thermal capacity [kW]']; #Da file Excel
    EfficiencyW = energysystem['Electrical efficiency based on LHV (between 0 and 1)']
    EfficiencyQ = energysystem['Heat efficiency based on LHV (between 0 and 1)']
    ElectricEnergyproduced = energysystem['Electric energy produced in a year (exported and consumed) [kWh /year]']
    ThermalEnergyproduced_primary = energysystem['Thermal energy produced used [kWh /year]']
    Qused = 1
    ExternalTemperature = energysystem['External temperature [°C]']
    SupplyTemperature = energysystem['Supply temperature [°C]']
    ReturnTemperature = energysystem['Return temperature [°C]']
    EnergyInputSourceGasBlend = energysystem['Energy input from gas-blend [kWh/year]']
    EnergyInputSourceBiogas = energysystem['Energy input from biogas [kWh/year]']
    EnergyInputSourceHydrogen = energysystem['Energy input from hydrogen [kWh/year]']

    EquivalentHours = ThermalEnergyproduced_primary / Power

    # DEFAULT PARAMETERS
    LHV = 36.8  # In MJ per Nm3 - Table 3.6 06_V_Natural Gas 3_3 Fuel Data
    HHV = 40.4  # In MJ per Nm3 - Table 3.6 06_V_Natural Gas 3_3 Fuel Data

    # Lifespan [years]: rated operating hours (40,000 below 25 kW electrical,
    # 100,000 above) divided by the full-load hours per year.
    Lifespan = np.where(
        Power * (EfficiencyW / EfficiencyQ)  < 25,
        40000 / EquivalentHours,
        100000 / EquivalentHours
    )

    # ADDITIONAL CALCULATIONS
    # Fuel input over the study period (from the electrical output and
    # efficiency), restated on the HHV basis of the fuel datasets; TotW / TotQ
    # are the electricity and heat delivered.
    # Note: this CHP divides by the electrical efficiency, the ORC and
    # waste-to-energy plants by the thermal one; which is intended is an open
    # question to the inventory authors.
    EfficiencyTot = EfficiencyW + EfficiencyQ
    EnergyProducedLHV = (Power * EquivalentHours * RSP) / EfficiencyW
    EnergyProducedHHV = EnergyProducedLHV * (HHV/LHV)
    TotW = EnergyProducedLHV * EfficiencyW
    TotQ = EnergyProducedLHV * EfficiencyQ * Qused

    # Earlier whole-column if/else version of the allocation below, kept for
    # reference; the live version applies the same arithmetic per building.
    # # MULTIFUNCTIONALITY AND ALLOCATION OF output
    # if Multifunctionality == 'Default':
    #     ExternalTemperature = ExternalTemperature + 273.15 #K
    #     SupplyTemperature = SupplyTemperature + 273.15 #K
    #     ReturnTemperature = ReturnTemperature + 273.15 #K
    #     CarnotTemperature = (SupplyTemperature - ReturnTemperature) / np.log(SupplyTemperature / ReturnTemperature)
    #     ThermalEnergyproduced = EnergyProducedHHV
    #     ElectricEnergyproduced = (EnergyProducedHHV / EfficiencyQ) * EfficiencyW
    #     # AFQ calculation
    #     AFQ_GasTurbine = (ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature))) / (ElectricEnergyproduced + ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature)))
    #     AFQ_GasTurbine = np.array(AFQ_GasTurbine)

    #     # AFW calculation
    #     AFW_GasTurbine = (1 - AFQ_GasTurbine)

    # else:
    #     fwecr = 0.7
    #     fweexp = fwecr

    #     # Calculations
    #     InletEnergyCogenmode = EnergyProducedHHV * EfficiencyTot
    #     AFW_GasTurbine = (InletEnergyCogenmode * fwecr - (ElectricEnergyproduced * fweexp)) / EnergyProducedHHV
    #     AFQ_GasTurbine = 1 - AFW_GasTurbine

    # if SupplyTemperature.eq(0).all() and ReturnTemperature.eq(0).all():
    #     AFQ_GasTurbine = np.zeros_like(AFQ_GasTurbine)
    #     AFW_GasTurbine = np.zeros_like(AFW_GasTurbine)

    # --- Multifunctionality: splitting the burden between heat and power -------
    # AFQ is the share charged to HEAT, AFW to POWER. Two methods, per building:
    #
    #   'Default' - exergy allocation: heat is weighted by its Carnot factor
    #               (1 - T_ext / T_carnot).
    #   otherwise - EN 15316:2017 primary-energy weighting, fwecr = 0.7 for the
    #               electricity carrier (table B2, p. 24).
    #
    # The 'else' arithmetic runs first, while ElectricEnergyproduced still
    # holds the workbook value. Rows with no temperatures get no allocation.
    # MULTIFUNCTIONALITY AND ALLOCATION OF output
    # Calculations for 'Else' condition (computed first to preserve original ElectricEnergyproduced)
    fwecr = 0.7
    fweexp = fwecr
    InletEnergyCogenmode = EnergyProducedHHV * EfficiencyTot
    AFW_GasTurbine_else = (InletEnergyCogenmode * fwecr - (ElectricEnergyproduced * fweexp)) / EnergyProducedHHV
    AFQ_GasTurbine_else = 1 - AFW_GasTurbine_else

    # Calculations for 'Default' condition
    ExternalTemperature = ExternalTemperature + 273.15 #K
    SupplyTemperature = SupplyTemperature + 273.15 #K
    ReturnTemperature = ReturnTemperature + 273.15 #K
    CarnotTemperature = (SupplyTemperature - ReturnTemperature) / np.log(SupplyTemperature / ReturnTemperature)
    ThermalEnergyproduced = EnergyProducedHHV
    ElectricEnergyproduced = (EnergyProducedHHV / EfficiencyQ) * EfficiencyW

    # AFQ calculation
    AFQ_GasTurbine_default = (ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature))) / (ElectricEnergyproduced + ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature)))
    AFQ_GasTurbine_default = np.array(AFQ_GasTurbine_default)

    # AFW calculation
    AFW_GasTurbine_default = (1 - AFQ_GasTurbine_default)

    # Apply conditions row by row
    AFQ_GasTurbine = np.where(Multifunctionality == 'Default', AFQ_GasTurbine_default, AFQ_GasTurbine_else)
    AFW_GasTurbine = np.where(Multifunctionality == 'Default', AFW_GasTurbine_default, AFW_GasTurbine_else)

    # Handle zero temperatures row by row
    zero_mask = zero_mask = (SupplyTemperature == 273.15) & (ReturnTemperature == 273.15)
    AFQ_GasTurbine = np.where(zero_mask, 0, AFQ_GasTurbine)
    AFW_GasTurbine = np.where(zero_mask, 0, AFW_GasTurbine)

    # Unit mass [kg], scaled linearly from a 10 MW electrical reference machine
    # of 114,998.5 kg.
    PowerEle = (Power / EfficiencyQ) * EfficiencyW
    RefPowerEle = 10000 #kW
    RefMass = 114998.5 #kg
    mass = PowerEle * (RefMass / RefPowerEle)

    # --- Module A1-3: manufacture ---------------------------------------------
    # Material and construction demand, allocated to heat. Concretes in [m3]
    # (/ 2400 kg/m3), copper, PEHD and steels in [kg], diesel and heat in [MJ],
    # electricity in [kWh]. The three flat figures are the reference plant's
    # construction energy.
    CHP_Turbogas_ConcreteAT = ((0.22 * mass) / 2400) * AFQ_GasTurbine
    CHP_Turbogas_ConcreteCH = ((0.41 * mass) / 2400) * AFQ_GasTurbine
    CHP_Turbogas_Copper = (0.03 * mass) * AFQ_GasTurbine
    CHP_Turbogas_Diesel = (np.full(Power.shape, 759000)) * AFQ_GasTurbine
    CHP_Turbogas_Electricity = (np.full(Power.shape, 46900)) * AFQ_GasTurbine
    CHP_Turbogas_Heat = (np.full(Power.shape, 721050)) * AFQ_GasTurbine
    CHP_Turbogas_PEHD = (0.08 * mass) * AFQ_GasTurbine
    CHP_Turbogas_ReinforcingSteel = (0.25 * mass) * AFQ_GasTurbine
    CHP_Turbogas_ChromiumSteel = (0.01 * mass) * AFQ_GasTurbine

    # --- Module A4: transport to site -----------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    CHP_Turbogas_Truck1632 = ((500 + 200)*(mass)/1000) * AFQ_GasTurbine
    CHP_Turbogas_Light_Truck = (50*(mass)/1000) * AFQ_GasTurbine

    # --- Module B2: maintenance transport -------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the unit mass.
    #y_Lifespan =  (EquivalentHours * RSP) / Lifespan
    CHP_Turbogas_LightTruck_B2 = (50 * (Lifespan/2) * 0.01 * (mass/1000))* AFQ_GasTurbine

    # --- Module B4: replacement within the study period ------------------------
    GasTurbineNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFGasTurbine = (RSP / Lifespan)  # Scaling factor

    # Shares of the fuel input, from the three [kWh/year] columns.
    #Parameters for energy input source repartition
    GasBlend = EnergyInputSourceGasBlend / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)
    Biogas = EnergyInputSourceBiogas / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)
    Hydrogen = EnergyInputSourceHydrogen / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)

    # --- Module B6: fuel and combustion emissions over the lifetime ------------
    # y is the fuel input over the study period [MJ], allocated to heat; x = 1
    # (no year-by-year blend split). Natural gas, biomethane and biogas in [m3]
    # (1 / HHV), hydrogen in [kWh] of photovoltaic electrolysis electricity
    # (120 MJ/kg / 3.6 / 0.9), cooling water in [kg]; emissions are biosphere
    # flows.
    x = 1
    TotEnergyNeeds = np.array([EnergyProducedHHV])
    TotEnergyNeeds = TotEnergyNeeds.flatten()
    y = (TotEnergyNeeds * 3.6).flatten() * AFQ_GasTurbine

    # Gas-blend composition: A natural gas, B biomethane, C hydrogen
    # (config.GAS_BLEND).
    A, B, C = config.GAS_BLEND

    # The 0.95 and 0.042 are factors from the reference inventory, separate
    # from the blend shares A and B.
    CHP_Turbogas_EnergyVectorNG = (((1 / (HHV)) * 0.95) * A) * x * y * GasBlend
    CHP_Turbogas_EnergyVectorBiomethane = (((1 / (HHV)) * 0.042) * B) * x * y * GasBlend
    CHP_Turbogas_EnergyVectorHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * C * GasBlend #120 MJ/kg
    CHP_Turbogas_EnergyVectorInputBiogas = ((1 / (HHV))) * x * y * Biogas
    CHP_Turbogas_EnergyVectorInputHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * Hydrogen #120 MJ/kg
    CHP_Turbogas_WaterCooling = (0.00618146537053705 * x * y).flatten()
    CHP_Turbogas_Acetaldehyde = (0.000000001 * x * y).flatten()
    CHP_Turbogas_AceticAcid = (0.00000015 * x * y).flatten()
    CHP_Turbogas_Benzene = (0.00000039 * x * y).flatten()
    CHP_Turbogas_Benzoapyrene = (0.00000000001 * x * y).flatten()
    CHP_Turbogas_Butane = (0.00000068 * x * y).flatten()
    CHP_Turbogas_CarbonDioxideFossil = (0.05406 * x * y).flatten()
    CHP_Turbogas_CarbonMonoxideFossil = (0.000003 * x * y).flatten()
    CHP_Turbogas_DinitrogenMonoxide = (0.00000048 * x * y).flatten()
    CHP_Turbogas_Formaldehyde = (0.00000010 * x * y).flatten()
    CHP_Turbogas_Mercury = (0.00000000003 * x * y).flatten()
    CHP_Turbogas_MethaneFossil = (0.00000193 * x * y).flatten()
    CHP_Turbogas_NitrogenOxides = (0.00001931 * x * y).flatten()
    CHP_Turbogas_PAH = (0.00000001 * x * y).flatten()
    CHP_Turbogas_Particulates = (0.00000010 * x * y).flatten()
    CHP_Turbogas_Pentane = (0.00000116 * x * y).flatten()
    CHP_Turbogas_Propane = (0.00000019 * x * y).flatten()
    CHP_Turbogas_PropionicAcid = (0.00000002 * x * y).flatten()
    CHP_Turbogas_SulfurDioxide = (0.00000048 * x * y).flatten()
    CHP_Turbogas_Toluene = (0.00000019 * x * y).flatten()
    CHP_Turbogas_WaterAir = (0.0000729530701641572 * x * y).flatten()
    CHP_Turbogas_WaterWater = (0.00610851230037289 * x * y).flatten()

    # --- Module C2: transport to the treatment plant ---------------------------
    # 50 km [t.km]. Note: unlike every other quantity here, not multiplied by
    # AFQ_GasTurbine.
    CHP_Turbogas_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing ------------------------------------------
    # Concrete volumes [m3] converted to the [kg] the end-of-life datasets use.
    CHP_Turbogas_EOL_ConcreteAT = CHP_Turbogas_ConcreteAT * config.CONCRETE_DENSITY
    CHP_Turbogas_EOL_ConcreteCH = CHP_Turbogas_ConcreteCH * config.CONCRETE_DENSITY
    CHP_Turbogas_EOL_Copper = CHP_Turbogas_Copper
    CHP_Turbogas_EOL_PEHD = CHP_Turbogas_PEHD
    CHP_Turbogas_EOL_ReinforcingSteel = CHP_Turbogas_ReinforcingSteel
    CHP_Turbogas_EOL_ChromiumSteel = CHP_Turbogas_ChromiumSteel

    # --- Module C4: disposal ---------------------------------------------------
    # The landfilled and incinerated shares of each material [kg].
    CHP_Turbogas_EOL_Landfill_ConcreteAT = CHP_Turbogas_EOL_ConcreteAT * LandfillConcrete
    CHP_Turbogas_EOL_Landfill_ConcreteCH = CHP_Turbogas_EOL_ConcreteCH * LandfillConcrete
    CHP_Turbogas_EOL_Landfill_Copper = CHP_Turbogas_EOL_Copper * LandfillMetals
    CHP_Turbogas_EOL_Inc_PEHD = CHP_Turbogas_EOL_PEHD * IncinerationPEHD
    CHP_Turbogas_EOL_Landfill_PEHD = CHP_Turbogas_EOL_PEHD * LandfillPEHD
    CHP_Turbogas_EOL_Landfill_ReinforcingSteel = CHP_Turbogas_EOL_ReinforcingSteel * LandfillMetals
    CHP_Turbogas_EOL_Landfill_ChromiumSteel = CHP_Turbogas_EOL_ChromiumSteel * LandfillMetals2

    # --- Module D1: recycling credits and primary-production burdens ------------
    CHP_Turbogas_EOL_Recycling_ConcreteAT = (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_Turbogas_EOL_ConcreteAT) - (RecycledContentConcrete * CHP_Turbogas_EOL_ConcreteAT)
    # The primary concrete dataset is sold in [m3], so the credit is divided by
    # the density.
    CHP_Turbogas_EOL_Primary_ConcreteAT = (((RecycledContentConcrete * CHP_Turbogas_EOL_ConcreteAT) - (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_Turbogas_EOL_ConcreteAT)) * SRinert) / config.CONCRETE_DENSITY

    CHP_Turbogas_EOL_Recycling_ConcreteCH = (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_Turbogas_EOL_ConcreteCH) - (RecycledContentConcrete * CHP_Turbogas_EOL_ConcreteCH)
    CHP_Turbogas_EOL_Primary_ConcreteCH = (((RecycledContentConcrete * CHP_Turbogas_EOL_ConcreteCH) - (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_Turbogas_EOL_ConcreteCH)) * SRinert) / config.CONCRETE_DENSITY

    CHP_Turbogas_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_Turbogas_EOL_Copper) - (RecycledContentMetals * CHP_Turbogas_EOL_Copper)
    CHP_Turbogas_EOL_Primary_Copper = ((RecycledContentMetals * CHP_Turbogas_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_Turbogas_EOL_Copper)) * SRmetals

    CHP_Turbogas_EOL_Recycling_HDPE = (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_Turbogas_EOL_PEHD) - (RecycledContentPlastic * CHP_Turbogas_EOL_PEHD)
    CHP_Turbogas_EOL_Primary_HDPE = ((RecycledContentPlastic * CHP_Turbogas_EOL_PEHD) - (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_Turbogas_EOL_PEHD)) * SRinert

    CHP_Turbogas_EOL_Recycling_ReinforcingSteel = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_Turbogas_EOL_ReinforcingSteel) - (RecycledContentMetals * CHP_Turbogas_EOL_ReinforcingSteel)
    CHP_Turbogas_EOL_Primary_ReinforcingSteel = ((RecycledContentMetals * CHP_Turbogas_EOL_ReinforcingSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_Turbogas_EOL_ReinforcingSteel)) * SRmetals

    CHP_Turbogas_EOL_Recycling_ChromiumSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_Turbogas_EOL_ChromiumSteel) - (RecycledContentMetals * CHP_Turbogas_EOL_ChromiumSteel)
    CHP_Turbogas_EOL_Primary_ChromiumSteel = ((RecycledContentMetals * CHP_Turbogas_EOL_ChromiumSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_Turbogas_EOL_ChromiumSteel)) * SRmetals

    # --- Module D3: energy recovered from incineration -------------------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    CHP_Turbogas_EOL_EnergyRecoveryHeat_PEHD = - CHP_Turbogas_EOL_Inc_PEHD * LHVHDPE * Xincheat
    CHP_Turbogas_EOL_EnergyRecoveryEle_PEHD = - CHP_Turbogas_EOL_Inc_PEHD * LHVHDPE * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_GasTurbine = np.array(TotQ)

    # Collect every 'CHP_Turbogas_' quantity for the exchange rows. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("CHP_Turbogas_")}

    return {
        "activity_data": activity_data,
        "sf": SFGasTurbine,
        "replacements": GasTurbineNumberReplacements,
        "bd_names": CHP_Turbogas_BdName,
        "bd_areas": CHP_Turbogas_BdArea,
        "thermal_energy": ThermalEnergyProduced_GasTurbine,
    }
