"""
chp_rice.py - life-cycle inventory of a reciprocating internal combustion
engine CHP unit.

A gas piston engine driving a generator, recovering the engine and exhaust
heat, and burning a gas blend, biogas or hydrogen. Every quantity is multiplied
by AFQ_RICE, the share of the burden allocated to HEAT (the electricity leaves
the system boundary); the two allocation methods are the same as
chp_turbogas.py's.

The engine is inventoried component by component: module A1-3 buys whole
ecoinvent units of a 160 kW electrical reference machine (air input/output
unit, control cabinet, gas motor, catalytic converter, ...), so CHP_RICE_Air,
CHP_RICE_Control, CHP_RICE_Motor etc. are counts of those units, not masses.
Modules C3 onwards resolve the same components into materials, so every
end-of-life name carries its component as a suffix.

Note: above 1400 kW the C3 inventory is incomplete and compute() raises
NotImplementedError (see the C3 block).

See energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the engines.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the
        'CHP-Internal Combustion Engine' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).

    Raises
    ------
    NotImplementedError
        For engines of 1400 kW or more (incomplete C3 inventory).
    """
    energysystem = sc.sheet("CHP-Internal Combustion Engine")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]          # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    LandfillMineralWool = eol["LandfillMineralWool"]
    LandfillCardboard = eol["LandfillCardboard"]
    LandfillPEHD = eol["LandfillPEHD"]
    LandfillPVC = eol["LandfillPVC"]
    IncinerationCardboard = eol["IncinerationCardboard"]
    IncinerationPEHD = eol["IncinerationPEHD"]
    IncinerationPVC = eol["IncinerationPVC"]
    RecyclingCardboard = eol["RecyclingCardboard"]
    RecyclingMetals = eol["RecyclingMetals"]        # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]      # share of special metals recycled
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingEfficiencyCardboard = eol["RecyclingEfficiencyCardboard"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecycledContentCardboard = eol["RecycledContentCardboard"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    SRmetals = eol["SRmetals"]                      # substitution ratio, secondary vs primary
    SRinert = eol["SRinert"]                        # same, for inert materials
    LHVCardboard = eol["LHVCardboard"]              # lower heating values [MJ/kg], for the
    LHVHDPE = eol["LHVHDPE"]                        # energy recovered by incineration (D3)
    LHVPVC = eol["LHVPVC"]
    LHVHazardous = eol["LHVHazardous"]
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency


    # DASHBOARD - VALUE INPUTS
    # 'Multifunctionality Approach' selects the allocation method; the three
    # temperatures drive the Carnot factor of the default method; the three
    # EnergyInputSource columns [kWh/year] are used only as fuel shares.
    # EquivalentHours [h/year] is the full-load running time.
    CHP_RICE_BdName = energysystem['Building Name']
    CHP_RICE_BdArea = energysystem['Zone net floor area [m2]']
    Multifunctionality = energysystem['Multifunctionality Approach']
    Power = energysystem['Thermal capacity [kW]']
    EfficiencyW = energysystem['Electrical efficiency based on LHV (between 0 and 1)']
    EfficiencyQ = energysystem['Heat efficiency based on LHV (between 0 and 1)']
    ElectricEnergyproduced = energysystem['Electric energy produced in a year (exported and consumed) [kWh /year]']
    ThermalEnergyproduced_primary = energysystem['Thermal energy produced used [kWh /year]']
    ExternalTemperature = energysystem['External temperature [°C]']
    SupplyTemperature = energysystem['Supply temperature [°C]']
    ReturnTemperature = energysystem['Return temperature [°C]']
    EnergyInputSourceGasBlend = energysystem['Energy input from gas-blend [kWh/year]']
    EnergyInputSourceBiogas = energysystem['Energy input from biogas [kWh/year]']
    EnergyInputSourceHydrogen = energysystem['Energy input from hydrogen [kWh/year]']

    EquivalentHours = ThermalEnergyproduced_primary / Power

    # DEFAULT PARAMETERS and energy balance.
    # Lifespan [years]: rated operating hours (40,000 below 25 kW electrical,
    # 100,000 above) divided by the full-load hours per year. EnergyProducedLHV
    # is the fuel input over the study period (Power x EquivalentHours x RSP /
    # efficiency), restated on the HHV basis of the fuel datasets; TotalW /
    # TotalQ are the electricity and heat delivered.
    # DEFAULT PARAMETERS
    LHV = 36.8  # In MJ per Nm3 - Table 3.6 06_V_Natural Gas 3_3 Fuel Data
    HHV = 40.4  # In MJ per Nm3 - Table 3.6 06_V_Natural Gas 3_3 Fuel Data

    Lifespan = np.where(
        Power * (EfficiencyW / EfficiencyQ)  < 25,
        40000 / EquivalentHours,
        100000 / EquivalentHours
    )

    # ADDITIONAL CALCULATIONS
    Qused = 1
    EfficiencyTot = EfficiencyW + EfficiencyQ
    EnergyProducedLHV = (Power * EquivalentHours * RSP) / EfficiencyW
    EnergyProducedHHV = EnergyProducedLHV * (HHV / LHV)
    TotalW = EnergyProducedLHV * EfficiencyW
    TotalQ = EnergyProducedLHV * EfficiencyQ * Qused

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
    #     AFQ = (ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature))) / (ElectricEnergyproduced + (ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature))))

    #     AFQ_RICE = np.array(AFQ)
    #     # AFW calculation
    #     AFW_RICE = (1 - AFQ_RICE)

    # else:
    #     fwecr = 0.7
    #     fweexp = fwecr

    #     # Calculation
    #     InletEnergyCogenmode = EnergyProducedHHV * EfficiencyTot
    #     AFW = (InletEnergyCogenmode * fwecr - (ElectricEnergyproduced * fweexp)) / EnergyProducedHHV
    #     AFW_RICE = np.array([AFW]).T
    #     AFQ_RICE = 1 - AFW_RICE

    # if SupplyTemperature.eq(0).all() and ReturnTemperature.eq(0).all():
    #     AFQ_RICE = np.zeros_like(AFQ_RICE)
    #     AFW_RICE = np.zeros_like(AFW_RICE)

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
    AFW_RICE_else = (InletEnergyCogenmode * fwecr - (ElectricEnergyproduced * fweexp)) / EnergyProducedHHV
    AFQ_RICE_else = 1 - AFW_RICE_else

    # Calculations for 'Default' condition
    ExternalTemperature = ExternalTemperature + 273.15 #K
    SupplyTemperature = SupplyTemperature + 273.15 #K
    ReturnTemperature = ReturnTemperature + 273.15 #K
    CarnotTemperature = (SupplyTemperature - ReturnTemperature) / np.log(SupplyTemperature / ReturnTemperature)
    ThermalEnergyproduced = EnergyProducedHHV
    ElectricEnergyproduced = (EnergyProducedHHV / EfficiencyQ) * EfficiencyW

    # AFQ calculation
    AFQ_RICE_default = (ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature))) / (ElectricEnergyproduced + ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature)))
    AFQ_RICE_default = np.array(AFQ_RICE_default)

    # AFW calculation
    AFW_RICE_default = (1 - AFQ_RICE_default)

    # Apply conditions row by row
    AFQ_RICE = np.where(Multifunctionality == 'Default', AFQ_RICE_default, AFQ_RICE_else)
    AFW_RICE = np.where(Multifunctionality == 'Default', AFW_RICE_default, AFW_RICE_else)

    # Handle zero temperatures row by row
    zero_mask = (SupplyTemperature == 273.15) & (ReturnTemperature == 273.15)
    AFQ_RICE = np.where(zero_mask, 0, AFQ_RICE)
    AFW_RICE = np.where(zero_mask, 0, AFW_RICE)

    # --- Module A1-3: manufacture ---------------------------------------------
    # Component counts [unit] of the 160 kW electrical reference machine (air
    # input/output unit, control cabinet, gas motor 206 kW, sound insulation,
    # three-way catalytic converter 19.1 l, electric parts, generator 200 kW,
    # heating and sanitary equipment, heat storage 2000 l), allocated to heat.
    # `mass` [kg] is the whole-machine mass of the bracket, used by A4 and C2.
    # Six size brackets [kW], applied per building.
    brackets = [
        Power < 25,
        (Power >= 25) & (Power < 100),
        (Power >= 100) & (Power < 300),
        (Power >= 300) & (Power < 700),
        (Power >= 700) & (Power < 1400),
        Power >= 1400,
    ]
    # Number of 1400 kW modules for an engine above that size.
    i = np.ceil(Power / 1400)

    mass = np.select(brackets, [
        12783.67,
        5133.22,
        14070.56,
        25247.44,
        40903.44,
        40903.44,
    ])
    CHP_RICE_Air = np.select(brackets, [
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0.4) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.6) * AFQ_RICE,
        np.full(len(Power),2.6) * i * AFQ_RICE,
    ])
    CHP_RICE_Control = np.select(brackets, [
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0.4) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.6) * AFQ_RICE,
        np.full(len(Power),2.6) * i * AFQ_RICE,
    ])
    CHP_RICE_Motor = np.select(brackets, [
        np.full(len(Power),2.5) * AFQ_RICE,
        np.full(len(Power),0.3) * AFQ_RICE,
        np.full(len(Power),1.3) * AFQ_RICE,
        np.full(len(Power), 2.8) * AFQ_RICE,
        np.full(len(Power),5.3) * AFQ_RICE,
        np.full(len(Power),5.3) * i * AFQ_RICE,
    ])
    CHP_RICE_Insulation = np.select(brackets, [
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0.4) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.6) * AFQ_RICE,
        np.full(len(Power),2.6) * i * AFQ_RICE,
    ])
    CHP_RICE_Catalytic = np.select(brackets, [
        np.full(len(Power),5) * AFQ_RICE,
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0) * i * AFQ_RICE,
    ])
    CHP_RICE_Electric = np.select(brackets, [
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),0.4) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.6) * AFQ_RICE,
        np.full(len(Power),2.6) * i * AFQ_RICE,
    ])
    CHP_RICE_Generator = np.select(brackets, [
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),0.3) * AFQ_RICE,
        np.full(len(Power),1.3) * AFQ_RICE,
        np.full(len(Power),2.8) * AFQ_RICE,
        np.full(len(Power),5.3) * AFQ_RICE,
        np.full(len(Power),5.3) * i * AFQ_RICE,
    ])
    CHP_RICE_Sanitary = np.select(brackets, [
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),0.4) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.6) * AFQ_RICE,
        np.full(len(Power),2.6) * i * AFQ_RICE,
    ])
    CHP_RICE_Storage = np.select(brackets, [
        np.full(len(Power),2) * AFQ_RICE,
        np.full(len(Power),0.8) * AFQ_RICE,
        np.full(len(Power),2) * AFQ_RICE,
        np.full(len(Power),3.4) * AFQ_RICE,
        np.full(len(Power),5.2) * AFQ_RICE,
        np.full(len(Power),5.2) * i * AFQ_RICE,
    ])
    # --- Module A4: transport to site -----------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    mass = np.full(len(Power), mass)
    CHP_RICE_Truck1632 = ((500 + 200)*(mass)/1000) * AFQ_RICE
    CHP_RICE_Light_Truck = (50*(mass)/1000) * AFQ_RICE

    # --- Module A5: installation ----------------------------------------------
    # Counts [unit] of the reference machine's assembly energy, construction
    # work, planning and start-up datasets.
    CHP_RICE_Energy = np.select(brackets, [
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0.414) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.61 * i) * AFQ_RICE,
    ])
    CHP_RICE_Construction = np.select(brackets, [
        np.full(len(Power),0) * AFQ_RICE,
        np.full(len(Power),0.4) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.61 * i) * AFQ_RICE,
    ])
    CHP_RICE_Planning = np.select(brackets, [
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),0.414) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.61 * i) * AFQ_RICE,
    ])
    CHP_RICE_Startup = np.select(brackets, [
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),0.414) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.7) * AFQ_RICE,
        np.full(len(Power),2.61 * i) * AFQ_RICE,
    ])
    # --- Module B2: maintenance ------------------------------------------------
    # CHP_RICE_Maintenance is a count [unit] of the reference maintenance
    # dataset; CHP_RICE_LubricatingOil is 0.03 g of oil per MJ of fuel [kg].
    CHP_RICE_Maintenance = np.select(brackets, [
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),0.377) * AFQ_RICE,
        np.full(len(Power),1) * AFQ_RICE,
        np.full(len(Power),1.8) * AFQ_RICE,
        np.full(len(Power),2.89) * AFQ_RICE,
        np.full(len(Power), 2.89 * i) * AFQ_RICE,
    ])
    CHP_RICE_LubricatingOil = np.select(brackets, [
        ((0.03/1000) * EnergyProducedHHV  *3.6) * AFQ_RICE,
        ((0.03/1000) * EnergyProducedHHV  *3.6) * AFQ_RICE,
        ((0.03/1000) * EnergyProducedHHV  *3.6) * AFQ_RICE,
        ((0.03/1000) * EnergyProducedHHV  *3.6) * AFQ_RICE,
        ((0.03/1000) * EnergyProducedHHV  *3.6) * AFQ_RICE,
        ((0.03/1000) * EnergyProducedHHV  *3.6) * AFQ_RICE,
    ])
    # --- Module B4: replacement within the study period ------------------------
    RICENumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFRICE = (RSP / Lifespan)  # Scaling factor

    # Shares of the fuel input, from the three [kWh/year] columns.
    #Parameters for repartition of the energy input
    GasBlend = EnergyInputSourceGasBlend / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)
    Biogas = EnergyInputSourceBiogas / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)
    Hydrogen = EnergyInputSourceHydrogen / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)

    # --- Module B6: fuel and combustion emissions over the lifetime ------------
    # y is the fuel input over the study period [MJ], allocated to heat; x = 1
    # (no year-by-year blend split). Natural gas, biomethane and biogas in [m3]
    # (1 / HHV), hydrogen in [kWh] of photovoltaic electrolysis electricity
    # (120 MJ/kg / 3.6 / 0.9); emissions are biosphere flows.
    x = 1
    TotEnergyNeeds = np.array([EnergyProducedHHV])
    TotEnergyNeeds = TotEnergyNeeds.flatten()
    y = (TotEnergyNeeds * 3.6).flatten() * AFQ_RICE

    CHP_RICE_EnergyvectorNG = (((1 / (HHV)) * 0.95)) * x * y * GasBlend
    CHP_RICE_EnergyvectorBiomethane = (((1 / (HHV)) * 0.042)) * x * y * GasBlend
    CHP_RICE_EnergyvectorHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * GasBlend #120 MJ/kg
    CHP_RICE_EnergyvectorInputBiogas = ((1 / (HHV))) * x * y * Biogas
    CHP_RICE_EnergyVectorInputHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * Hydrogen #120 MJ/kg
    CHP_RICE_Acetaldehyde = (0.0000000008 * x * y).flatten()
    CHP_RICE_AceticAcid = (0.000000121 * x * y).flatten()
    CHP_RICE_Benzene = (0.000000000926 * x * y).flatten()
    CHP_RICE_Benzoapyrene = (0.000000000000529 * x * y).flatten()
    CHP_RICE_Butane = (0.000000926 * x * y).flatten()
    CHP_RICE_CarbonDioxideFossil = (0.0561 * x * y).flatten()
    CHP_RICE_CarbonMonoxideFossil = (0.000003 * x * y).flatten()
    CHP_RICE_DinitrogenMonoxide = (0.000001 * x * y).flatten()
    CHP_RICE_Ethane = (0.00000137 * x * y).flatten()
    CHP_RICE_Formaldehyde = (0.0000000331 * x * y).flatten()
    CHP_RICE_Hexane = (0.000000793 * x * y).flatten()
    CHP_RICE_Mercury = (0.00000000003 * x * y).flatten()
    CHP_RICE_MethaneFossil = (0.000001 * x * y).flatten()
    CHP_RICE_NitrogenOxides = (0.000064 * x * y).flatten()
    CHP_RICE_PAH = (0.000000008 * x * y).flatten()
    CHP_RICE_Particulates = (0.0000005 * x * y).flatten()
    CHP_RICE_Pentane = (0.00000115 * x * y).flatten()
    CHP_RICE_Propane = (0.000000705 * x * y).flatten()
    CHP_RICE_PropionicAcid = (0.000000016 * x * y).flatten()
    CHP_RICE_SulfurDioxide = (0.0000005 * x * y).flatten()
    CHP_RICE_Toluene = (0.0000000015 * x * y).flatten()
    CHP_RICE_Dioxins = (0.000000000029 * x * y).flatten()

    # --- Module C2: transport to the treatment plant ---------------------------
    # 50 km [t.km]. Note: unlike every other quantity here, not multiplied by
    # AFQ_RICE.
    CHP_RICE_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing ------------------------------------------
    # The A1-3 component counts resolved into materials [kg]: mass of each
    # material in one reference component x the same count (e.g. 288 kg of
    # reinforcing steel per air input unit, 1000 kg of cast iron per gas motor).
    #
    # Note: the top bracket (1400 kW and above) defines only 24 of the 45
    # quantities; the missing 21 (AlkydpaintStorage, AluminiumEle,
    # AluminiumStorage, CastironGen, ChromiumsteelStorage, CopperEle, CopperGen,
    # HDPEEle, LeadEle, NickelEle, PVCpolimerizedEle, PlatinumEle,
    # ReinforcingsteelEle, ReinforcingsteelSan, ReinforcingsteelStorage,
    # SheetrollingaluminiumStorage, SheetrollingsteelStorage, StonewoolSan,
    # StonewoolStorage, TinEle, ZincEle) default to NaN, and the guard below
    # refuses such engines. Open question to the inventory authors.
    CHP_RICE_ReinforcingsteelAirinput = np.select(brackets, [
        np.full(len(Power), 288 * 0) * AFQ_RICE,
        np.full(len(Power), 288 * 0.4) * AFQ_RICE,
        np.full(len(Power), 288 * 1) * AFQ_RICE,
        np.full(len(Power), 288 * 1.7) * AFQ_RICE,
        np.full(len(Power), 288 * 2.6) * AFQ_RICE,
        np.full(len(Power), 288 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_AluminiumControlcabinet = np.select(brackets, [
        np.full(len(Power), 0.15 * 0) * AFQ_RICE,
        np.full(len(Power), 0.15 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.15 * 1) * AFQ_RICE,
        np.full(len(Power), 0.15 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.15 * 2.6) * AFQ_RICE,
        np.full(len(Power), 0.15 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_CopperControlcabinet = np.select(brackets, [
        np.full(len(Power), 10.8 * 0) * AFQ_RICE,
        np.full(len(Power), 10.8 * 0.4) * AFQ_RICE,
        np.full(len(Power), 10.8 * 1) * AFQ_RICE,
        np.full(len(Power), 10.8 * 1.7) * AFQ_RICE,
        np.full(len(Power), 10.8 * 2.6) * AFQ_RICE,
        np.full(len(Power), 10.8 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_LeadControlcabinet = np.select(brackets, [
        np.full(len(Power), 0.76 * 0) * AFQ_RICE,
        np.full(len(Power), 0.76 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.76 * 1) * AFQ_RICE,
        np.full(len(Power), 0.76 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.76 * 2.6) * AFQ_RICE,
        np.full(len(Power), 0.76 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_NickelControlcabinet = np.select(brackets, [
        np.full(len(Power), 0.34 * 0) * AFQ_RICE,
        np.full(len(Power), 0.34 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.34 * 1) * AFQ_RICE,
        np.full(len(Power), 0.34 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.34 * 2.6) * AFQ_RICE,
        np.full(len(Power), 0.34 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_PlatinumControlcabinet = np.select(brackets, [
        np.full(len(Power), 0.0021 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0021 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.0021 * 1) * AFQ_RICE,
        np.full(len(Power), 0.0021 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.0021 * 2.6) * AFQ_RICE,
        np.full(len(Power), 0.0021 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_HDPEControlcabinet = np.select(brackets, [
        np.full(len(Power), 78.5 * 0) * AFQ_RICE,
        np.full(len(Power), 78.5 * 0.4) * AFQ_RICE,
        np.full(len(Power), 78.5 * 1) * AFQ_RICE,
        np.full(len(Power), 78.5 * 1.7) * AFQ_RICE,
        np.full(len(Power), 78.5 * 2.6) * AFQ_RICE,
        np.full(len(Power), 78.5 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_PVCemulsionatedControlcabinet = np.select(brackets, [
        np.full(len(Power), 0.95745 * 0) * AFQ_RICE,
        np.full(len(Power), 0.95745 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.95745 * 1) * AFQ_RICE,
        np.full(len(Power), 0.95745 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.95745 * 2.6) * AFQ_RICE,
        np.full(len(Power), 0.95745 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_PVCpolimerizedControlcabinet = np.select(brackets, [
        np.full(len(Power), 6.54255 * 0) * AFQ_RICE,
        np.full(len(Power), 6.54255 * 0.4) * AFQ_RICE,
        np.full(len(Power), 6.54255 * 1) * AFQ_RICE,
        np.full(len(Power), 6.54255 * 1.7) * AFQ_RICE,
        np.full(len(Power), 6.54255 * 2.6) * AFQ_RICE,
        np.full(len(Power), 6.54255 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_ReinforcingsteelControlcabinet = np.select(brackets, [
        np.full(len(Power), 276 * 0) * AFQ_RICE,
        np.full(len(Power), 276 * 0.4) * AFQ_RICE,
        np.full(len(Power), 276 * 1) * AFQ_RICE,
        np.full(len(Power), 276 * 1.7) * AFQ_RICE,
        np.full(len(Power), 276 * 2.6) * AFQ_RICE,
        np.full(len(Power), 276 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_TinControlcabinet = np.select(brackets, [
        np.full(len(Power), 1.62 * 0) * AFQ_RICE,
        np.full(len(Power), 1.62 * 0.4) * AFQ_RICE,
        np.full(len(Power), 1.62 * 1) * AFQ_RICE,
        np.full(len(Power), 1.62 * 1.7) * AFQ_RICE,
        np.full(len(Power), 1.62 * 2.6) * AFQ_RICE,
        np.full(len(Power), 1.62 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_ZincControlcabinet = np.select(brackets, [
        np.full(len(Power), 0.25 * 0) * AFQ_RICE,
        np.full(len(Power), 0.25 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.25 * 1) * AFQ_RICE,
        np.full(len(Power), 0.25 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.25 * 2.6) * AFQ_RICE,
        np.full(len(Power), 0.25 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_CastironGasmotor = np.select(brackets, [
        np.full(len(Power), 1000 * 2.5) * AFQ_RICE,
        np.full(len(Power), 1000 * 0.3) * AFQ_RICE,
        np.full(len(Power), 1000 * 1.3) * AFQ_RICE,
        np.full(len(Power), 1000 * 2.8) * AFQ_RICE,
        np.full(len(Power), 1000 * 5.3) * AFQ_RICE,
        np.full(len(Power), 1000 * 5.3 * i) * AFQ_RICE,
    ])
    CHP_RICE_ReinforcingsteelGasmotor = np.select(brackets, [
        np.full(len(Power), 100 * 2.5) * AFQ_RICE,
        np.full(len(Power), 100 * 0.3) * AFQ_RICE,
        np.full(len(Power), 100 * 1.3) * AFQ_RICE,
        np.full(len(Power), 100 * 2.8) * AFQ_RICE,
        np.full(len(Power), 100 * 5.3) * AFQ_RICE,
        np.full(len(Power), 100 * 5.3 * i) * AFQ_RICE,
    ])
    CHP_RICE_ChromiumsteelGasmotor = np.select(brackets, [
        np.full(len(Power), 100 * 2.5) * AFQ_RICE,
        np.full(len(Power), 100 * 0.3) * AFQ_RICE,
        np.full(len(Power), 100 * 1.3) * AFQ_RICE,
        np.full(len(Power), 100 * 2.8) * AFQ_RICE,
        np.full(len(Power), 100 * 5.3) * AFQ_RICE,
        np.full(len(Power), 100 * 5.3 * i) * AFQ_RICE,
    ])
    CHP_RICE_LowalloyedsteelGasmotor = np.select(brackets, [
        np.full(len(Power), 200 * 2.5) * AFQ_RICE,
        np.full(len(Power), 200 * 0.3) * AFQ_RICE,
        np.full(len(Power), 200 * 1.3) * AFQ_RICE,
        np.full(len(Power), 200 * 2.8) * AFQ_RICE,
        np.full(len(Power), 200 * 5.3) * AFQ_RICE,
        np.full(len(Power), 200 * 5.3 * i) * AFQ_RICE,
    ])
    CHP_RICE_ReinforcingsteelSoundinsulation = np.select(brackets, [
        np.full(len(Power), 1920 * 0) * AFQ_RICE,
        np.full(len(Power), 1920 * 0.4) * AFQ_RICE,
        np.full(len(Power), 1920 * 1) * AFQ_RICE,
        np.full(len(Power), 1920 * 1.7) * AFQ_RICE,
        np.full(len(Power), 1920 * 2.6) * AFQ_RICE,
        np.full(len(Power), 1920 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_StonewoolSoundinsulation = np.select(brackets, [
        np.full(len(Power), 480 * 0) * AFQ_RICE,
        np.full(len(Power), 480 * 0.4) * AFQ_RICE,
        np.full(len(Power), 480 * 1) * AFQ_RICE,
        np.full(len(Power), 480 * 1.7) * AFQ_RICE,
        np.full(len(Power), 480 * 2.6) * AFQ_RICE,
        np.full(len(Power), 480 * 2.6 * i) * AFQ_RICE,
    ])
    CHP_RICE_CorrugatedboxboardConverter = np.select(brackets, [
        np.full(len(Power), 0.55 * 5) * AFQ_RICE,
        np.full(len(Power), 0.55 * 0) * AFQ_RICE,
        np.full(len(Power), 0.55 * 0) * AFQ_RICE,
        np.full(len(Power), 0.55 * 0) * AFQ_RICE,
        np.full(len(Power), 0.55 * 0) * AFQ_RICE,
        np.full(len(Power), 0.55 * 0 * i) * AFQ_RICE,
    ])
    CHP_RICE_PalladiumConverter = np.select(brackets, [
        np.full(len(Power), 0.0082 * 5) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0 * i) * AFQ_RICE,
    ])
    CHP_RICE_PlatinumConverter = np.select(brackets, [
        np.full(len(Power), 0.0409 * 5) * AFQ_RICE,
        np.full(len(Power), 0.0409 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0409 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0409 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0409 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0409 * 0 * i) * AFQ_RICE,
    ])
    CHP_RICE_RhodiumConverter = np.select(brackets, [
        np.full(len(Power), 0.0082 * 5) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0) * AFQ_RICE,
        np.full(len(Power), 0.0082 * 0 * i) * AFQ_RICE,
    ])
    CHP_RICE_ChromiumsteelConverter = np.select(brackets, [
        np.full(len(Power), 66 * 5) * AFQ_RICE,
        np.full(len(Power), 66 * 0) * AFQ_RICE,
        np.full(len(Power), 66 * 0) * AFQ_RICE,
        np.full(len(Power), 66 * 0) * AFQ_RICE,
        np.full(len(Power), 66 * 0) * AFQ_RICE,
        np.full(len(Power), 66 * 0 * i) * AFQ_RICE,
    ])
    CHP_RICE_ZeoliteConverter = np.select(brackets, [
        np.full(len(Power), 3.8 * 5) * AFQ_RICE,
        np.full(len(Power), 3.8 * 0) * AFQ_RICE,
        np.full(len(Power), 3.8 * 0) * AFQ_RICE,
        np.full(len(Power), 3.8 * 0) * AFQ_RICE,
        np.full(len(Power), 3.8 * 0) * AFQ_RICE,
        np.full(len(Power), 3.8 * 0 * i) * AFQ_RICE,
    ])
    CHP_RICE_AluminiumEle = np.select(brackets[:5], [
        np.full(len(Power), 0.1 * 1) * AFQ_RICE,
        np.full(len(Power), 0.1 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.1 * 1) * AFQ_RICE,
        np.full(len(Power), 0.1 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.1 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_CopperEle = np.select(brackets[:5], [
        np.full(len(Power), 6.5 * 1) * AFQ_RICE,
        np.full(len(Power), 6.5 * 0.4) * AFQ_RICE,
        np.full(len(Power), 6.5 * 1) * AFQ_RICE,
        np.full(len(Power), 6.5 * 1.7) * AFQ_RICE,
        np.full(len(Power), 6.5 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_LeadEle = np.select(brackets[:5], [
        np.full(len(Power), 0.47 * 1) * AFQ_RICE,
        np.full(len(Power), 0.47 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.47 * 1) * AFQ_RICE,
        np.full(len(Power), 0.47 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.47 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_NickelEle = np.select(brackets[:5], [
        np.full(len(Power), 0.21 * 1) * AFQ_RICE,
        np.full(len(Power), 0.21 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.21 * 1) * AFQ_RICE,
        np.full(len(Power), 0.21 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.21 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_PlatinumEle = np.select(brackets[:5], [
        np.full(len(Power), 0.0013 * 1) * AFQ_RICE,
        np.full(len(Power), 0.0013 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.0013 * 1) * AFQ_RICE,
        np.full(len(Power), 0.0013 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.0013 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_HDPEEle = np.select(brackets[:5], [
        np.full(len(Power), 47.4 * 1) * AFQ_RICE,
        np.full(len(Power), 47.4 * 0.4) * AFQ_RICE,
        np.full(len(Power), 47.4 * 1) * AFQ_RICE,
        np.full(len(Power), 47.4 * 1.7) * AFQ_RICE,
        np.full(len(Power), 47.4 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_PVCpolimerizedEle = np.select(brackets[:5], [
        np.full(len(Power), 0.501133 * 1) * AFQ_RICE,
        np.full(len(Power), 0.501133 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.501133 * 1) * AFQ_RICE,
        np.full(len(Power), 0.501133 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.501133 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_ReinforcingsteelEle = np.select(brackets[:5], [
        np.full(len(Power), 52.7 * 1) * AFQ_RICE,
        np.full(len(Power), 52.7 * 0.4) * AFQ_RICE,
        np.full(len(Power), 52.7 * 1) * AFQ_RICE,
        np.full(len(Power), 52.7 * 1.7) * AFQ_RICE,
        np.full(len(Power), 52.7 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_TinEle = np.select(brackets[:5], [
        np.full(len(Power), 0.997 * 1) * AFQ_RICE,
        np.full(len(Power), 0.997 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.997 * 1) * AFQ_RICE,
        np.full(len(Power), 0.997 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.997 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_ZincEle = np.select(brackets[:5], [
        np.full(len(Power), 0.154 * 1) * AFQ_RICE,
        np.full(len(Power), 0.154 * 0.4) * AFQ_RICE,
        np.full(len(Power), 0.154 * 1) * AFQ_RICE,
        np.full(len(Power), 0.154 * 1.7) * AFQ_RICE,
        np.full(len(Power), 0.154 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_CastironGen = np.select(brackets[:5], [
        np.full(len(Power), 595 * 1) * AFQ_RICE,
        np.full(len(Power), 595 * 0.3) * AFQ_RICE,
        np.full(len(Power), 595 * 1.3) * AFQ_RICE,
        np.full(len(Power), 595 * 2.8) * AFQ_RICE,
        np.full(len(Power), 595 * 5.3) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_CopperGen = np.select(brackets[:5], [
        np.full(len(Power), 255 * 1) * AFQ_RICE,
        np.full(len(Power), 255 * 0.3) * AFQ_RICE,
        np.full(len(Power), 255 * 1.3) * AFQ_RICE,
        np.full(len(Power), 255 * 2.8) * AFQ_RICE,
        np.full(len(Power), 255 * 5.3) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_ReinforcingsteelSan = np.select(brackets[:5], [
        np.full(len(Power), 353 * 1) * AFQ_RICE,
        np.full(len(Power), 353 * 0.4) * AFQ_RICE,
        np.full(len(Power), 353 * 1) * AFQ_RICE,
        np.full(len(Power), 353 * 1.7) * AFQ_RICE,
        np.full(len(Power), 353 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_StonewoolSan = np.select(brackets[:5], [
        np.full(len(Power), 7 * 1) * AFQ_RICE,
        np.full(len(Power), 7 * 0.4) * AFQ_RICE,
        np.full(len(Power), 7 * 1) * AFQ_RICE,
        np.full(len(Power), 7 * 1.7) * AFQ_RICE,
        np.full(len(Power), 7 * 2.6) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_AlkydpaintStorage = np.select(brackets[:5], [
        np.full(len(Power), 4.2 * 2) * AFQ_RICE,
        np.full(len(Power), 4.2 * 0.8) * AFQ_RICE,
        np.full(len(Power), 4.2 * 2) * AFQ_RICE,
        np.full(len(Power), 4.2 * 3.4) * AFQ_RICE,
        np.full(len(Power), 4.2 * 5.2) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_AluminiumStorage = np.select(brackets[:5], [
        np.full(len(Power), 87.2 * 2) * AFQ_RICE,
        np.full(len(Power), 87.2 * 0.8) * AFQ_RICE,
        np.full(len(Power), 87.2 * 2) * AFQ_RICE,
        np.full(len(Power), 87.2 * 3.4) * AFQ_RICE,
        np.full(len(Power), 87.2 * 5.2) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_ReinforcingsteelStorage = np.select(brackets[:5], [
        np.full(len(Power), 1770 * 2) * AFQ_RICE,
        np.full(len(Power), 1770 * 0.8) * AFQ_RICE,
        np.full(len(Power), 1770 * 2) * AFQ_RICE,
        np.full(len(Power), 1770 * 3.4) * AFQ_RICE,
        np.full(len(Power), 1770 * 5.2) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_SheetrollingaluminiumStorage = np.select(brackets[:5], [
        np.full(len(Power), 87.2 * 2) * AFQ_RICE,
        np.full(len(Power), 87.2 * 0.8) * AFQ_RICE,
        np.full(len(Power), 87.2 * 2) * AFQ_RICE,
        np.full(len(Power), 87.2 * 3.4) * AFQ_RICE,
        np.full(len(Power), 87.2 * 5.2) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_SheetrollingsteelStorage = np.select(brackets[:5], [
        np.full(len(Power), 1770 * 2) * AFQ_RICE,
        np.full(len(Power), 1770 * 0.8) * AFQ_RICE,
        np.full(len(Power), 1770 * 2) * AFQ_RICE,
        np.full(len(Power), 1770 * 3.4) * AFQ_RICE,
        np.full(len(Power), 1770 * 5.2) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_ChromiumsteelStorage = np.select(brackets[:5], [
        np.full(len(Power), 3.7 * 2) * AFQ_RICE,
        np.full(len(Power), 3.7 * 0.8) * AFQ_RICE,
        np.full(len(Power), 3.7 * 2) * AFQ_RICE,
        np.full(len(Power), 3.7 * 3.4) * AFQ_RICE,
        np.full(len(Power), 3.7 * 5.2) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    CHP_RICE_StonewoolStorage = np.select(brackets[:5], [
        np.full(len(Power), 84 * 2) * AFQ_RICE,
        np.full(len(Power), 84 * 0.8) * AFQ_RICE,
        np.full(len(Power), 84 * 2) * AFQ_RICE,
        np.full(len(Power), 84 * 3.4) * AFQ_RICE,
        np.full(len(Power), 84 * 5.2) * AFQ_RICE,
    ], default=np.nan)   # NOT DEFINED above 1400 kW - see the C3 note
    # Refuse engines of 1400 kW or more (see the C3 note).
    if np.asarray(Power >= 1400).any():
        raise NotImplementedError(
            "chp_rice.py: the module C3 inventory above 1400 kW is incomplete - "
            "21 of its 45 material quantities were never given a value in the "
            "original top bracket, and supplying them is a modelling decision. "
            "Engines at or above 1400 kW "
            "cannot be inventoried until those 21 figures are decided."
        )

    # --- Module C4: disposal ---------------------------------------------------
    # The landfilled and incinerated shares of each material [kg].
    #
    # Zeolite and alkyd paint have no end-of-life share parameters and are 100%
    # incinerated.
    CHP_RICE_EOL_Landfill_ReinforcingsteelAirinput = CHP_RICE_ReinforcingsteelAirinput * LandfillMetals
    CHP_RICE_EOL_Landfill_AluminiumControlcabinet = CHP_RICE_AluminiumControlcabinet * LandfillMetals
    CHP_RICE_EOL_Landfill_CopperControlcabinet = CHP_RICE_CopperControlcabinet * LandfillMetals
    CHP_RICE_EOL_Landfill_LeadControlcabinet = CHP_RICE_LeadControlcabinet * LandfillMetals2
    CHP_RICE_EOL_Landfill_NickelControlcabinet = CHP_RICE_NickelControlcabinet * LandfillMetals2
    CHP_RICE_EOL_Landfill_PlatinumControlcabinet = CHP_RICE_PlatinumControlcabinet * LandfillMetals2
    CHP_RICE_EOL_Inc_HDPEControlcabinet = CHP_RICE_HDPEControlcabinet * IncinerationPEHD
    CHP_RICE_EOL_Landfill_HDPEControlcabinet = CHP_RICE_HDPEControlcabinet * LandfillPEHD
    CHP_RICE_EOL_Inc_PVCemulsionatedControlcabinet = CHP_RICE_PVCemulsionatedControlcabinet * IncinerationPVC
    CHP_RICE_EOL_Landfill_PVCemulsionatedControlcabinet = CHP_RICE_PVCemulsionatedControlcabinet * LandfillPVC
    CHP_RICE_EOL_Inc_PVCpolimerizedControlcabinet = CHP_RICE_PVCpolimerizedControlcabinet * IncinerationPVC
    CHP_RICE_EOL_Landfill_PVCpolimerizedControlcabinet = CHP_RICE_PVCpolimerizedControlcabinet * LandfillPVC
    CHP_RICE_EOL_Landfill_ReinforcingsteelControlcabinet = CHP_RICE_ReinforcingsteelControlcabinet * LandfillMetals
    CHP_RICE_EOL_Landfill_TinControlcabinet = CHP_RICE_TinControlcabinet * LandfillMetals
    CHP_RICE_EOL_Landfill_ZincControlcabinet = CHP_RICE_ZincControlcabinet * LandfillMetals2
    CHP_RICE_EOL_Landfill_CastironGasmotor = CHP_RICE_CastironGasmotor * LandfillMetals2
    CHP_RICE_EOL_Landfill_ReinforcingsteelGasmotor = CHP_RICE_ReinforcingsteelGasmotor * LandfillMetals
    CHP_RICE_EOL_Landfill_ChromiumsteelGasmotor = CHP_RICE_ChromiumsteelGasmotor * LandfillMetals2
    CHP_RICE_EOL_Landfill_LowalloyedsteelGasmotor = CHP_RICE_LowalloyedsteelGasmotor * LandfillMetals
    CHP_RICE_EOL_Landfill_ReinforcingsteelSoundinsulation = CHP_RICE_ReinforcingsteelSoundinsulation * LandfillMetals
    CHP_RICE_EOL_Landfill_StonewoolSoundinsulation = CHP_RICE_StonewoolSoundinsulation * LandfillMineralWool
    CHP_RICE_EOL_Inc_CorrugatedboxboardConverter = CHP_RICE_CorrugatedboxboardConverter * IncinerationCardboard
    CHP_RICE_EOL_Landfill_CorrugatedboxboardConverter = CHP_RICE_CorrugatedboxboardConverter * LandfillCardboard
    CHP_RICE_EOL_Landfill_PalladiumConverter = CHP_RICE_PalladiumConverter * LandfillMetals2
    CHP_RICE_EOL_Landfill_PlatinumConverter = CHP_RICE_PlatinumConverter * LandfillMetals2
    CHP_RICE_EOL_Landfill_RhodiumConverter = CHP_RICE_RhodiumConverter * LandfillMetals2
    CHP_RICE_EOL_Landfill_ChromiumsteelConverter = CHP_RICE_ChromiumsteelConverter * LandfillMetals2
    CHP_RICE_EOL_Inc_ZeoliteConverter = CHP_RICE_ZeoliteConverter
    CHP_RICE_EOL_Landfill_AluminiumEle = CHP_RICE_AluminiumEle * LandfillMetals
    CHP_RICE_EOL_Landfill_CopperEle = CHP_RICE_CopperEle * LandfillMetals
    CHP_RICE_EOL_Landfill_LeadEle = CHP_RICE_LeadEle * LandfillMetals2
    CHP_RICE_EOL_Landfill_NickelEle = CHP_RICE_NickelEle * LandfillMetals2
    CHP_RICE_EOL_Landfill_PlatinumEle = CHP_RICE_PlatinumEle * LandfillMetals2
    CHP_RICE_EOL_Inc_HDPEEle = CHP_RICE_HDPEEle * IncinerationPEHD
    CHP_RICE_EOL_Landfill_HDPEEle = CHP_RICE_HDPEEle * LandfillPEHD
    CHP_RICE_EOL_Inc_PVCpolimerizedEle = CHP_RICE_PVCpolimerizedEle * IncinerationPVC
    CHP_RICE_EOL_Landfill_PVCpolimerizedEle = CHP_RICE_PVCpolimerizedEle * LandfillPVC
    CHP_RICE_EOL_Landfill_ReinforcingsteelEle = CHP_RICE_ReinforcingsteelEle * LandfillMetals
    CHP_RICE_EOL_Landfill_TinEle = CHP_RICE_TinEle * LandfillMetals
    CHP_RICE_EOL_Landfill_ZincEle = CHP_RICE_ZincEle * LandfillMetals2
    CHP_RICE_EOL_Landfill_CastironGen = CHP_RICE_CastironGen * LandfillMetals2
    CHP_RICE_EOL_Landfill_CopperGen = CHP_RICE_CopperGen * LandfillMetals
    CHP_RICE_EOL_Landfill_ReinforcingsteelSan = CHP_RICE_ReinforcingsteelSan * LandfillMetals
    CHP_RICE_EOL_Landfill_StonewoolSan = CHP_RICE_StonewoolSan * LandfillMineralWool
    CHP_RICE_EOL_Inc_AlkydpaintStorage = CHP_RICE_AlkydpaintStorage
    CHP_RICE_EOL_Landfill_AluminiumStorage = CHP_RICE_AluminiumStorage * LandfillMetals
    CHP_RICE_EOL_Landfill_ReinforcingsteelStorage = CHP_RICE_ReinforcingsteelStorage * LandfillMetals
    CHP_RICE_EOL_Landfill_SheetrollingaluminiumStorage = CHP_RICE_SheetrollingaluminiumStorage * LandfillMetals
    CHP_RICE_EOL_Landfill_SheetrollingsteelStorage = CHP_RICE_SheetrollingsteelStorage * LandfillMetals
    CHP_RICE_EOL_Landfill_ChromiumsteelStorage = CHP_RICE_ChromiumsteelStorage * LandfillMetals2
    CHP_RICE_EOL_Landfill_StonewoolStorage = CHP_RICE_StonewoolStorage * LandfillMineralWool

    # --- Module D1: recycling credits and primary-production burdens ------------
    # Special metals use RecyclingMetals2 on both lines of each pair.
    CHP_RICE_Recycling_ReinforcingsteelAirinput = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelAirinput) - (RecycledContentMetals * CHP_RICE_ReinforcingsteelAirinput)
    CHP_RICE_Primary_ReinforcingsteelAirinput = ((RecycledContentMetals * CHP_RICE_ReinforcingsteelAirinput) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelAirinput))* SRmetals

    CHP_RICE_Recycling_AluminiumControlcabinet = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_AluminiumControlcabinet) - (RecycledContentMetals * CHP_RICE_AluminiumControlcabinet)
    CHP_RICE_Primary_AluminiumControlcabinet = ((RecycledContentMetals * CHP_RICE_AluminiumControlcabinet) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_AluminiumControlcabinet))* SRmetals

    CHP_RICE_Recycling_CopperControlcabinet = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_CopperControlcabinet) - (RecycledContentMetals * CHP_RICE_CopperControlcabinet)
    CHP_RICE_Primary_CopperControlcabinet = ((RecycledContentMetals * CHP_RICE_CopperControlcabinet) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_CopperControlcabinet))* SRmetals

    CHP_RICE_Recycling_LeadControlcabinet = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_LeadControlcabinet) - (RecycledContentMetals * CHP_RICE_LeadControlcabinet)
    CHP_RICE_Primary_LeadControlcabinet = ((RecycledContentMetals * CHP_RICE_LeadControlcabinet) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_LeadControlcabinet))* SRmetals

    CHP_RICE_Recycling_NickelControlcabinet = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_NickelControlcabinet) - (RecycledContentMetals * CHP_RICE_NickelControlcabinet)
    CHP_RICE_Primary_NickelControlcabinet = ((RecycledContentMetals * CHP_RICE_NickelControlcabinet) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_NickelControlcabinet))* SRmetals

    CHP_RICE_Recycling_PlatinumControlcabinet = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_PlatinumControlcabinet) - (RecycledContentMetals * CHP_RICE_PlatinumControlcabinet)
    CHP_RICE_Primary_PlatinumControlcabinet = ((RecycledContentMetals * CHP_RICE_PlatinumControlcabinet) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_PlatinumControlcabinet)) * SRmetals

    CHP_RICE_Recycling_HDPEControlcabinet = (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_RICE_HDPEControlcabinet) - (RecycledContentPlastic * CHP_RICE_HDPEControlcabinet)
    CHP_RICE_Primary_HDPEControlcabinet = ((RecycledContentPlastic * CHP_RICE_HDPEControlcabinet) - (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_RICE_HDPEControlcabinet)) * SRinert

    CHP_RICE_Recycling_ReinforcingsteelControlcabinet = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelControlcabinet) - (RecycledContentMetals * CHP_RICE_ReinforcingsteelControlcabinet)
    CHP_RICE_Primary_ReinforcingsteelControlcabinet = ((RecycledContentMetals * CHP_RICE_ReinforcingsteelControlcabinet) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelControlcabinet)) * SRmetals

    CHP_RICE_Recycling_TinControlcabinet = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_TinControlcabinet) - (RecycledContentMetals * CHP_RICE_TinControlcabinet)
    CHP_RICE_Primary_TinControlcabinet = ((RecycledContentMetals * CHP_RICE_TinControlcabinet) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_TinControlcabinet))* SRmetals

    CHP_RICE_Recycling_ZincControlcabinet = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ZincControlcabinet) - (RecycledContentMetals * CHP_RICE_ZincControlcabinet)
    CHP_RICE_Primary_ZincControlcabinet = ((RecycledContentMetals * CHP_RICE_ZincControlcabinet) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ZincControlcabinet))* SRmetals

    # Cast iron is treated as a special metal (LandfillMetals2 /
    # RecyclingMetals2). Note: which family it belongs to is an open question.
    CHP_RICE_Recycling_CastironGasmotor = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_CastironGasmotor) - (RecycledContentMetals * CHP_RICE_CastironGasmotor)
    CHP_RICE_Primary_CastironGasmotor = ((RecycledContentMetals * CHP_RICE_CastironGasmotor) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_CastironGasmotor))* SRmetals

    CHP_RICE_Recycling_ReinforcingsteelGasmotor = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelGasmotor) - (RecycledContentMetals * CHP_RICE_ReinforcingsteelGasmotor)
    CHP_RICE_Primary_ReinforcingsteelGasmotor = ((RecycledContentMetals * CHP_RICE_ReinforcingsteelGasmotor) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelGasmotor))* SRmetals

    CHP_RICE_Recycling_ChromiumsteelGasmotor = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ChromiumsteelGasmotor) - (RecycledContentMetals * CHP_RICE_ChromiumsteelGasmotor)
    CHP_RICE_Primary_ChromiumsteelGasmotor = ((RecycledContentMetals * CHP_RICE_ChromiumsteelGasmotor) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ChromiumsteelGasmotor))* SRmetals

    CHP_RICE_Recycling_LowalloyedsteelGasmotor = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_LowalloyedsteelGasmotor) - (RecycledContentMetals * CHP_RICE_LowalloyedsteelGasmotor)
    CHP_RICE_Primary_LowalloyedsteelGasmotor = ((RecycledContentMetals * CHP_RICE_LowalloyedsteelGasmotor) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_LowalloyedsteelGasmotor))* SRmetals

    CHP_RICE_Recycling_ReinforcingsteelSoundinsulation = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelSoundinsulation) - (RecycledContentMetals * CHP_RICE_ReinforcingsteelSoundinsulation)
    CHP_RICE_Primary_ReinforcingsteelSoundinsulation = ((RecycledContentMetals * CHP_RICE_ReinforcingsteelSoundinsulation) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelSoundinsulation))* SRmetals

    CHP_RICE_Recycling_CorrugatedboxboardConverter = (RecyclingCardboard * RecyclingEfficiencyCardboard * CHP_RICE_CorrugatedboxboardConverter) - (RecycledContentCardboard * CHP_RICE_CorrugatedboxboardConverter)
    CHP_RICE_Primary_CorrugatedboxboardConverter = ((RecycledContentCardboard * CHP_RICE_CorrugatedboxboardConverter) - (RecyclingCardboard * RecyclingEfficiencyCardboard * CHP_RICE_CorrugatedboxboardConverter))* SRinert

    CHP_RICE_Recycling_PalladiumConverter = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_PalladiumConverter) - (RecycledContentMetals * CHP_RICE_PalladiumConverter)
    CHP_RICE_Primary_PalladiumConverter = ((RecycledContentMetals * CHP_RICE_PalladiumConverter) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_PalladiumConverter))* SRmetals

    CHP_RICE_Recycling_PlatinumConverter = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_PlatinumConverter) - (RecycledContentMetals * CHP_RICE_PlatinumConverter)
    CHP_RICE_Primary_PlatinumConverter = ((RecycledContentMetals * CHP_RICE_PlatinumConverter) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_PlatinumConverter))* SRmetals

    CHP_RICE_Recycling_RhodiumConverter = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_RhodiumConverter) - (RecycledContentMetals * CHP_RICE_RhodiumConverter)
    CHP_RICE_Primary_RhodiumConverter = ((RecycledContentMetals * CHP_RICE_RhodiumConverter) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_RhodiumConverter))* SRmetals

    CHP_RICE_Recycling_ChromiumsteelConverter = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ChromiumsteelConverter) - (RecycledContentMetals * CHP_RICE_ChromiumsteelConverter)
    CHP_RICE_Primary_ChromiumsteelConverter = ((RecycledContentMetals * CHP_RICE_ChromiumsteelConverter) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ChromiumsteelConverter))* SRmetals

    CHP_RICE_Recycling_AluminiumEle = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_AluminiumEle) - (RecycledContentMetals * CHP_RICE_AluminiumEle)
    CHP_RICE_Primary_AluminiumEle = ((RecycledContentMetals * CHP_RICE_AluminiumEle) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_AluminiumEle))* SRmetals

    CHP_RICE_Recycling_CopperEle = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_CopperEle) - (RecycledContentMetals * CHP_RICE_CopperEle)
    CHP_RICE_Primary_CopperEle = ((RecycledContentMetals * CHP_RICE_CopperEle) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_CopperEle))* SRmetals

    CHP_RICE_Recycling_LeadEle = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_LeadEle) - (RecycledContentMetals * CHP_RICE_LeadEle)
    CHP_RICE_Primary_LeadEle = ((RecycledContentMetals * CHP_RICE_LeadEle) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_LeadEle))* SRmetals

    CHP_RICE_Recycling_NickelEle = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_NickelEle) - (RecycledContentMetals * CHP_RICE_NickelEle)
    CHP_RICE_Primary_NickelEle = ((RecycledContentMetals * CHP_RICE_NickelEle) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_NickelEle))* SRmetals

    CHP_RICE_Recycling_PlatinumEle = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_PlatinumEle) - (RecycledContentMetals * CHP_RICE_PlatinumEle)
    CHP_RICE_Primary_PlatinumEle = ((RecycledContentMetals * CHP_RICE_PlatinumEle) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_PlatinumEle))* SRmetals

    CHP_RICE_Recycling_HDPEEle = (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_RICE_HDPEEle) - (RecycledContentPlastic * CHP_RICE_HDPEEle)
    CHP_RICE_Primary_HDPEEle = ((RecycledContentPlastic * CHP_RICE_HDPEEle) - (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_RICE_HDPEEle)) * SRinert

    CHP_RICE_Recycling_ReinforcingsteelEle = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelEle) - (RecycledContentMetals * CHP_RICE_ReinforcingsteelEle)
    CHP_RICE_Primary_ReinforcingsteelEle = ((RecycledContentMetals * CHP_RICE_ReinforcingsteelEle) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelEle))* SRmetals
    # Note: tin in the electric parts has a C4 landfill line but no D1 credit.

    CHP_RICE_Recycling_ZincEle = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ZincEle) - (RecycledContentMetals * CHP_RICE_ZincEle)
    CHP_RICE_Primary_ZincEle = ((RecycledContentMetals * CHP_RICE_ZincEle) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ZincEle))* SRmetals

    # Cast iron is treated as a special metal (LandfillMetals2 /
    # RecyclingMetals2). Note: which family it belongs to is an open question.
    CHP_RICE_Recycling_CastironGen = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_CastironGen) - (RecycledContentMetals * CHP_RICE_CastironGen)
    CHP_RICE_Primary_CastironGen = ((RecycledContentMetals * CHP_RICE_CastironGen) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_CastironGen))* SRmetals

    CHP_RICE_Recycling_CopperGen = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_CopperGen) - (RecycledContentMetals * CHP_RICE_CopperGen)
    CHP_RICE_Primary_CopperGen = ((RecycledContentMetals * CHP_RICE_CopperGen) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_CopperGen))* SRmetals

    CHP_RICE_Recycling_ReinforcingsteelSan = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelSan) - (RecycledContentMetals * CHP_RICE_ReinforcingsteelSan)
    CHP_RICE_Primary_ReinforcingsteelSan = ((RecycledContentMetals * CHP_RICE_ReinforcingsteelSan) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelSan))* SRmetals

    CHP_RICE_Recycling_AluminiumStorage = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_AluminiumStorage) - (RecycledContentMetals * CHP_RICE_AluminiumStorage)
    CHP_RICE_Primary_AluminiumStorage = ((RecycledContentMetals * CHP_RICE_AluminiumStorage) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_AluminiumStorage))* SRmetals

    CHP_RICE_Recycling_ReinforcingsteelStorage = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelStorage) - (RecycledContentMetals * CHP_RICE_ReinforcingsteelStorage)
    CHP_RICE_Primary_ReinforcingsteelStorage = ((RecycledContentMetals * CHP_RICE_ReinforcingsteelStorage) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_ReinforcingsteelStorage))* SRmetals

    CHP_RICE_Recycling_SheetrollingaluminiumStorage = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_SheetrollingaluminiumStorage) - (RecycledContentMetals * CHP_RICE_SheetrollingaluminiumStorage)
    CHP_RICE_Primary_SheetrollingaluminiumStorage = ((RecycledContentMetals * CHP_RICE_SheetrollingaluminiumStorage) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_SheetrollingaluminiumStorage))* SRmetals

    CHP_RICE_Recycling_SheetrollingsteelStorage = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_SheetrollingsteelStorage) - (RecycledContentMetals * CHP_RICE_SheetrollingsteelStorage)
    CHP_RICE_Primary_SheetrollingsteelStorage = ((RecycledContentMetals * CHP_RICE_SheetrollingsteelStorage) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_RICE_SheetrollingsteelStorage))* SRmetals

    CHP_RICE_Recycling_ChromiumsteelStorage = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ChromiumsteelStorage) - (RecycledContentMetals * CHP_RICE_ChromiumsteelStorage)
    CHP_RICE_Primary_ChromiumsteelStorage = ((RecycledContentMetals * CHP_RICE_ChromiumsteelStorage) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_RICE_ChromiumsteelStorage))* SRmetals

    # --- Module D3: energy recovered from incineration -------------------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    CHP_RICE_EnergyRecoveryHeat_HDPEControlcabinet =  - CHP_RICE_EOL_Inc_HDPEControlcabinet * LHVHDPE * Xincheat
    CHP_RICE_EnergyRecoveryEle_HDPEControlcabinet =  - CHP_RICE_EOL_Inc_HDPEControlcabinet * LHVHDPE * Xincele / config.MJ_PER_KWH

    CHP_RICE_EnergyRecoveryHeat_PVCemulsionatedControlcabinet =  - CHP_RICE_EOL_Inc_PVCemulsionatedControlcabinet * LHVPVC * Xincheat
    CHP_RICE_EnergyRecoveryEle_PVCemulsionatedControlcabinet =  - CHP_RICE_EOL_Inc_PVCemulsionatedControlcabinet * LHVPVC * Xincele / config.MJ_PER_KWH

    CHP_RICE_EnergyRecoveryHeat_PVCpolimerizedControlcabinet =  - CHP_RICE_EOL_Inc_PVCpolimerizedControlcabinet * LHVPVC * Xincheat
    CHP_RICE_EnergyRecoveryEle_PVCpolimerizedControlcabinet =  - CHP_RICE_EOL_Inc_PVCpolimerizedControlcabinet * LHVPVC * Xincele / config.MJ_PER_KWH

    CHP_RICE_EnergyRecoveryHeat_CorrugatedboxboardConverter =  - CHP_RICE_EOL_Inc_CorrugatedboxboardConverter * LHVCardboard * Xincheat
    CHP_RICE_EnergyRecoveryEle_CorrugatedboxboardConverter =  - CHP_RICE_EOL_Inc_CorrugatedboxboardConverter * LHVCardboard * Xincele / config.MJ_PER_KWH

    CHP_RICE_EnergyRecoveryHeat_HDPEEle =  - CHP_RICE_EOL_Inc_HDPEEle * LHVHDPE * Xincheat
    CHP_RICE_EnergyRecoveryEle_HDPEEle =  - CHP_RICE_EOL_Inc_HDPEEle * LHVHDPE * Xincele / config.MJ_PER_KWH

    CHP_RICE_EnergyRecoveryHeat_PVCpolimerizedEle =  - CHP_RICE_EOL_Inc_PVCpolimerizedEle * LHVPVC * Xincheat
    CHP_RICE_EnergyRecoveryEle_PVCpolimerizedEle =  - CHP_RICE_EOL_Inc_PVCpolimerizedEle * LHVPVC * Xincele / config.MJ_PER_KWH

    CHP_RICE_EnergyRecoveryHeat_AlkydpaintStorage = - CHP_RICE_EOL_Inc_AlkydpaintStorage * LHVHazardous * Xincheat
    CHP_RICE_EnergyRecoveryEle_AlkydpaintStorage = - CHP_RICE_EOL_Inc_AlkydpaintStorage * LHVHazardous * Xincele / config.MJ_PER_KWH

    CHP_RICE_EnergyRecoveryHeat_ZeoliteConverter = - CHP_RICE_EOL_Inc_ZeoliteConverter * LHVHazardous * Xincheat
    CHP_RICE_EnergyRecoveryEle_ZeoliteConverter = - CHP_RICE_EOL_Inc_ZeoliteConverter * LHVHazardous * Xincele / config.MJ_PER_KWH

    # Data for export (informative only: the fuel input; see energy_systems/__init__.py).
    ThermalEnergyProduced_RICE = TotEnergyNeeds

    # Collect every 'CHP_RICE_' quantity for the exchange rows. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("CHP_RICE_")}

    return {
        "activity_data": activity_data,
        "sf": SFRICE,
        "replacements": RICENumberReplacements,
        "bd_names": CHP_RICE_BdName,
        "bd_areas": CHP_RICE_BdArea,
        "thermal_energy": ThermalEnergyProduced_RICE,
    }
