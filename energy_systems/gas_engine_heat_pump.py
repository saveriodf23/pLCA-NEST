"""
gas_engine_heat_pump.py - life-cycle inventory of a gas engine heat pump.

A vapour-compression heat pump whose compressor is driven by a gas engine, so
it has both a refrigerant charge (like electric_heat_pump.py) and combustion
emissions (like gas_absorption_heat_pump.py), and it can burn any of the four
fuels the gas boiler can. See energy_systems/__init__.py for the conventions
shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the heat pumps.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Gas Engine Heat Pump'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Gas Engine Heat Pump")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    LandfillElectronics = eol["LandfillElectronics"]
    LandfillRefrigerant = eol["LandfillRefrigerant"]
    IncinerationElectronics = eol["IncinerationElectronics"]
    IncinerationLubricatingOil = eol["IncinerationLubricatingOil"]
    IncinerationHazardous = eol["IncinerationHazardous"]
    RecyclingMetals = eol["RecyclingMetals"]
    RecyclingMetals2 = eol["RecyclingMetals2"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                      # substitution ratio, secondary vs primary
    LHVElectronics = eol["LHVElectronics"]          # lower heating values [MJ/kg], for D3
    LHVHazardous = eol["LHVHazardous"]
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency

    GasEngineHeatPump_BdName = energysystem['Building Name']
    GasEngineHeatPump_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Thermal capacity [kW]']
    EnergyProduced = energysystem['Energy produced [kWh /year]']
    SGUE = energysystem['SGUE']       # seasonal gas utilisation efficiency [-]
    EnergyInputSource = energysystem['Energy source (Gas-blend, LPG, Biomethane, Hydrogen)']

    # Heating values of the fuel gas [MJ/m3], as in boiler.py.
    LHV = np.where(EnergyInputSource == 'Gas-blend', 36.8,
          np.where(EnergyInputSource == 'LPG', 93,
          np.where(EnergyInputSource == 'Biomethane', 35,
          np.where(EnergyInputSource == 'Hydrogen', 10.8, np.nan))))

    HHV = np.where(EnergyInputSource == 'Gas-blend', 40.4,
          np.where(EnergyInputSource == 'LPG', 102,
          np.where(EnergyInputSource == 'Biomethane', 38,
          np.where(EnergyInputSource == 'Hydrogen', 12.7, np.nan))))

    def calculate_mass(Power):
        """Unit mass [kg] from thermal capacity [kW].

        A power law below 90 kW; above it, i units of up to 90 kW each.
        """
        if Power < 90:
            return (250.490 * Power ** 0.330)
        else:
            i = np.ceil(Power / 90)
            return (250.490 * (Power / i) ** 0.330) * i

    mass = Power.apply(calculate_mass)
    Lifespan = 20        # [years]

    # Refrigerant charge [kg], modular above 90 kW. Subtracted from the unit
    # mass so the material split below covers the machine only.
    i = np.ceil(Power / 90)
    conditions = [
        Power < 90,
        Power >= 90
    ]
    choices = [
        0.322 * Power**0.932,
        0.322 * (Power / i)**0.932 * i
    ]
    M_R = np.select(conditions, choices)
    massrefrigerant = M_R
    mass = mass - massrefrigerant

    # --- Module A1-3: product stage --------------------------------------------
    # Material split as a fraction of the machine mass [kg].
    GasEngineHeatPump_Copper = 0.0192709304876261 * mass
    GasEngineHeatPump_Aluminium = 0.128643214612436 * mass
    GasEngineHeatPump_LowAlloyedSteel = 0.202601386160499 * mass
    GasEngineHeatPump_StainlessSteel = 0.394003982376949 * mass
    GasEngineHeatPump_Ferrite = 0.00275299006966087 * mass
    GasEngineHeatPump_Brass = 0.227202457102359 * mass
    GasEngineHeatPump_Alumina = 0.00254967543377773 * mass
    GasEngineHeatPump_Electronics = 0.002 * mass
    GasEngineHeatPump_LubricatingOil = 0.000017 * mass
    # Weld length [m] per kg of unit mass (the welding dataset is sold in metres).
    GasEngineHeatPump_Welding = 0.00012 * mass
    # Process water and the shares of it emitted to air and water.
    GasEngineHeatPump_WaterConsumption = 0.0122 * mass
    GasEngineHeatPump_EmissionWaterAir = 0.15 * GasEngineHeatPump_WaterConsumption
    GasEngineHeatPump_EmissionWaterWater = 0.02 * GasEngineHeatPump_WaterConsumption
    # Wastewater treatment [m3]. Note: taken as a fraction of the unit mass
    # rather than of the water consumed; open question.
    GasEngineHeatPump_WasteWaterTreatment = (0.83 * mass) / 1000
    GasEngineHeatPump_ElectricityA13 = 0.532 * mass              # [kWh] to manufacture
    GasEngineHeatPump_Heat = 3.8 * mass                          # [MJ] to manufacture
    GasEngineHeatPump_HazardousWaste = 0.0006 * mass
    GasEngineHeatPump_RefrigerantGas = massrefrigerant
    GasEngineHeatPump_ethanepentafluoro_methanedifluoro = np.zeros(len(Power))

    # --- Module A4: transport to site -------------------------------------------
    GasEngineHeatPump_Truck1632 = ((500 + 200)*(mass)/1000)
    GasEngineHeatPump_Light_Truck = (50*(mass)/1000)

    # --- Module B1: use-stage refrigerant leakage -------------------------------
    # 3% of the charge per year over the machine's life.
    # Note: no R290 exemption here, unlike electric_heat_pump.py; open question
    # to the inventory authors.
    massrefrigerantB2 = np.array(massrefrigerant)
    GasEngineHeatPump_MaintenanceRefrigerantGas = 0.03 * massrefrigerant * Lifespan
    GasEngineHeatPump_MaintenanceEthanePentafluoro_MethaneDifluoro = 0.03 * massrefrigerant * Lifespan

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the machine mass.
    GasEngineHeatPump_Light_Truck_B2 = np.array(50 * (Lifespan / 2) * 0.01 * (mass / 1000))  # Light_Truk_B2 come array

    # --- Module B4: replacement within the study period -------------------------
    GEHPNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFGEHP = (RSP / Lifespan)  # Scaling factor

    # --- Module B6: operational energy over the study period --------------------
    # One-hot flags for the fuel burned.
    GasBlend   = np.where(EnergyInputSource == 'Gas-blend', 1, 0)
    Biomethane = np.where(EnergyInputSource == 'Biomethane', 1, 0)
    Hydrogen   = np.where(EnergyInputSource == 'Hydrogen', 1, 0)
    LPG        = np.where(EnergyInputSource == 'LPG', 1, 0)

    EnergyProduced = np.array(EnergyProduced)
    EnergyProducedforGas = EnergyProduced
    # Heat delivered over the study period [MJ]: kWh/year x 3.6 MJ/kWh x RSP.
    y = (EnergyProduced * 3.6 * RSP).flatten()
    # REPARTITION IN THE ENERGY SOURCE
    # k and h2_term are not used. The commented-out branches are the disabled
    # year-by-year blend split, as in boiler.py.
    k = 0.0256410256410256
    # Base terms calculations
    base = (1 / SGUE) / (HHV)
    h2_term = (1 / (SGUE * (12.7 / 0.09)))
    conditions = [
        (EnergyInputSource == 'Gas-blend'), #& (Year == 2025),
        # (EnergyInputSource == 'Gas-blend') & (Year == 2030),
        # (EnergyInputSource == 'Gas-blend') & (Year == 2035),
        # (EnergyInputSource == 'Gas-blend') & (Year == 2040),
        # (EnergyInputSource == 'Gas-blend') & (Year == 2045),
        # (EnergyInputSource == 'Gas-blend') & (Year == 2050),
        (EnergyInputSource == 'LPG'),
        (EnergyInputSource == 'Biomethane'),
        (EnergyInputSource == 'Hydrogen')
    ]
    values = [
        base,
        # base * 0.90 + base * 0.084 + h2_term * 0.014,
        # base * 0.795 + base * 0.189 + h2_term * 0.016,
        # base * 0.688 + base * 0.294 + h2_term * 0.018,
        # base * 0.582 + base * 0.399 + h2_term * 0.020,
        # base * 0 + base * 0.25 + h2_term * 0.20,
        (1 / SGUE) / (HHV),
        (1 /SGUE) / (HHV),
        (1 / (SGUE * (12.7 / 0.09)))
    ]

    x = np.select(conditions, values, default=np.nan)

    # Gas-blend composition: A natural gas, B biomethane, C hydrogen
    # (config.GAS_BLEND).
    A, B, C = config.GAS_BLEND

    # Fuel consumed over the study period: the three gas-blend components
    # (weighted by A, B, C), then the pure fuels, each gated on its flag. LPG is
    # converted to [kg] via config.LPG_DENSITY; hydrogen is modelled as
    # electrolysis electricity, as in boiler.py.
    GasEngineHeatPump_EnergyVectorNG = ((1 / (SGUE * HHV)) * y) * A * GasBlend
    GasEngineHeatPump_EnergyVectorBiomethane = ((1 / (SGUE * HHV)) * y) * B * GasBlend
    GasEngineHeatPump_EnergyVectorHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * C * GasBlend #120 MJ/kg
    GasEngineHeatPump_EnergyVectorBiomethaneInput = ((1 / (SGUE * HHV)) * y) * Biomethane
    GasEngineHeatPump_EnergyVectorLPGinput = ((1 / (SGUE * HHV)) * y) * LPG * config.LPG_DENSITY
    GasEngineHeatPump_EnergyVectorHydrogeninput = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * Hydrogen
    GasEngineHeatPump_ElectricityB6 = 0.0404 * (1 / SGUE) * EnergyProduced * RSP
    # Combustion emissions, one line per substance, on the gas burned.
    GasEngineHeatPump_Acetaldehyde = 0.000000001 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_AceticAcid = 0.00000015 * (1 / SGUE)  * EnergyProduced * RSP
    GasEngineHeatPump_Benzene = 0.0000004 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Benzoapyrene = 0.00000000001 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Butane = 0.0000007 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_CarbonDioxideFossil = 0.05406 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_CarbonMonoxideFossil = 0.00003 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_DinitrogenMonoxide = 0.0000005 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Formaldehyde = 0.0000001 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Mercury = 0.00000000003 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_MethaneFossil = 0.000002 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_NitrogenOxides = 0.00002 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_PAH = 0.00000001 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Particulates = 0.0000001 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Pentane = 0.0000012 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Propane = 0.0000002 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_PropionicAcid = 0.00000002 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_SulfurDioxide = 0.0000005 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Toluene = 0.0000002 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Nitrate = 0.00000013 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Nitrite = 0.000000003 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Sulfate = 0.00000005 * (1 / SGUE) * EnergyProduced * RSP
    GasEngineHeatPump_Sulfite = 0.00000005 * (1 / SGUE) * EnergyProduced * RSP
    # Operating refrigerant leakage, 4% of the charge per year.
    GasEngineHeatPump_UsePhaseRefrigerantGas = 0.04 * massrefrigerant * RSP
    GasEngineHeatPump_UsePhaseEthanePentafluoro_MethaneDifluoro = 0.04 * massrefrigerant * RSP

    # --- Module C2: transport to treatment --------------------------------------
    GasEngineHeatPump_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    GasEngineHeatPump_EOL_Copper = GasEngineHeatPump_Copper
    GasEngineHeatPump_EOL_Aluminium = GasEngineHeatPump_Aluminium
    GasEngineHeatPump_EOL_LowAlloyedSteel = GasEngineHeatPump_LowAlloyedSteel
    GasEngineHeatPump_EOL_StainlessSteel = GasEngineHeatPump_StainlessSteel
    GasEngineHeatPump_EOL_Ferrite = GasEngineHeatPump_Ferrite
    GasEngineHeatPump_EOL_Brass = GasEngineHeatPump_Brass
    GasEngineHeatPump_EOL_Alumina = GasEngineHeatPump_Alumina
    GasEngineHeatPump_EOL_Electronics = GasEngineHeatPump_Electronics
    GasEngineHeatPump_EOL_lubricatingoil = GasEngineHeatPump_LubricatingOil
    GasEngineHeatPump_EOL_hazardouswaste = GasEngineHeatPump_HazardousWaste
    GasEngineHeatPump_EOL_RefrigerantGas = massrefrigerant

    # --- Module C4: final disposal ----------------------------------------------
    GasEngineHeatPump_EOL_Landfill_Copper = GasEngineHeatPump_EOL_Copper * LandfillMetals
    GasEngineHeatPump_EOL_Landfill_Aluminium = GasEngineHeatPump_EOL_Aluminium * LandfillMetals
    GasEngineHeatPump_EOL_Landfill_LowAlloyedSteel = GasEngineHeatPump_EOL_LowAlloyedSteel * LandfillMetals
    GasEngineHeatPump_EOL_Landfill_StainlessSteel = GasEngineHeatPump_EOL_StainlessSteel * LandfillMetals2
    GasEngineHeatPump_EOL_Landfill_Ferrite  = GasEngineHeatPump_EOL_Ferrite  * LandfillMetals
    GasEngineHeatPump_EOL_Landfill_Brass  = GasEngineHeatPump_EOL_Brass  * LandfillMetals
    GasEngineHeatPump_EOL_Landfill_Alumina  = GasEngineHeatPump_EOL_Alumina  * LandfillMetals
    GasEngineHeatPump_EOL_Inc_Electronics = GasEngineHeatPump_EOL_Electronics * IncinerationElectronics #kg
    GasEngineHeatPump_EOL_Landfill_Electronics = GasEngineHeatPump_EOL_Electronics * LandfillElectronics #kg
    GasEngineHeatPump_EOL_Inc_LubricatingOil = GasEngineHeatPump_EOL_lubricatingoil * IncinerationLubricatingOil #kg
    GasEngineHeatPump_EOL_Inc_HazardousWaste = GasEngineHeatPump_HazardousWaste * IncinerationHazardous #kg
    GasEngineHeatPump_EOL_Landfill_RefrigerantGas = GasEngineHeatPump_EOL_RefrigerantGas * LandfillRefrigerant

    # --- Module D1: credit for exported secondary materials ---------------------
    # Only the four bulk metals earn a credit; brass and ferrite do not.
    GasEngineHeatPump_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * GasEngineHeatPump_EOL_Copper) - (RecycledContentMetals * GasEngineHeatPump_EOL_Copper)
    GasEngineHeatPump_EOL_Primary_Copper = ((RecycledContentMetals * GasEngineHeatPump_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * GasEngineHeatPump_EOL_Copper)) * SRmetals
    GasEngineHeatPump_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * GasEngineHeatPump_EOL_Aluminium) - (RecycledContentMetals * GasEngineHeatPump_EOL_Aluminium)
    GasEngineHeatPump_EOL_Primary_Aluminium = ((RecycledContentMetals * GasEngineHeatPump_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * GasEngineHeatPump_EOL_Aluminium)) * SRmetals
    GasEngineHeatPump_EOL_Recycling_LowAlloyedSteel = (RecyclingMetals * RecyclingEfficiencyMetals * GasEngineHeatPump_EOL_LowAlloyedSteel) - (RecycledContentMetals * GasEngineHeatPump_EOL_LowAlloyedSteel)
    GasEngineHeatPump_EOL_Primary_LowAlloyedSteel = ((RecycledContentMetals * GasEngineHeatPump_EOL_LowAlloyedSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * GasEngineHeatPump_EOL_LowAlloyedSteel)) * SRmetals
    GasEngineHeatPump_EOL_Recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * GasEngineHeatPump_EOL_StainlessSteel) - (RecycledContentMetals * GasEngineHeatPump_EOL_StainlessSteel)
    GasEngineHeatPump_EOL_Primary_StainlessSteel = ((RecycledContentMetals * GasEngineHeatPump_EOL_StainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * GasEngineHeatPump_EOL_StainlessSteel)) * SRmetals

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    GasEngineHeatPump_EOL_EnergyRecoveryHeat_Electronics = - GasEngineHeatPump_EOL_Inc_Electronics * LHVElectronics * Xincheat
    GasEngineHeatPump_EOL_EnergyRecoveryEle_Electronics = - GasEngineHeatPump_EOL_Inc_Electronics * LHVElectronics * Xincele / config.MJ_PER_KWH
    GasEngineHeatPump_EOL_EnergyRecoveryHeat_LubricatingOil = - GasEngineHeatPump_EOL_Inc_LubricatingOil * LHVHazardous * Xincheat
    GasEngineHeatPump_EOL_EnergyRecoveryEle_LubricatingOil = - GasEngineHeatPump_EOL_Inc_LubricatingOil * LHVHazardous * Xincele / config.MJ_PER_KWH
    GasEngineHeatPump_EOL_EnergyRecoveryHeat_HazardousWaste = - GasEngineHeatPump_EOL_Inc_HazardousWaste * LHVHazardous * Xincheat
    GasEngineHeatPump_EOL_EnergyRecoveryEle_HazardousWaste = - GasEngineHeatPump_EOL_Inc_HazardousWaste * LHVHazardous * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_GEHP = np.array([EnergyProduced * RSP])

    # Collect every 'GasEngineHeatPump_' quantity for the exchange rows.
    loc = locals()
    return {
        "activity_data": {name: value for name, value in loc.items()
                          if name.startswith("GasEngineHeatPump_")},
        "sf": SFGEHP,
        "replacements": GEHPNumberReplacements,
        "bd_names": GasEngineHeatPump_BdName,
        "bd_areas": GasEngineHeatPump_BdArea,
        "thermal_energy": ThermalEnergyProduced_GEHP,
    }
