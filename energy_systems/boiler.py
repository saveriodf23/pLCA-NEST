"""
boiler.py - life-cycle inventory of a condensing boiler.

One boiler per building, burning one of four fuels: a natural-gas blend, LPG,
biomethane or hydrogen. See energy_systems/__init__.py for the conventions
shared by all technology modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the boilers.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Boiler' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Boiler")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]          # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    LandfillElastomer = eol["LandfillElastomer"]
    LandfillPVC = eol["LandfillPVC"]
    LandfillRefrigerant = eol["LandfillRefrigerant"]
    LandfillElectronics = eol["LandfillElectronics"]
    IncinerationElastomer = eol["IncinerationElastomer"]
    IncinerationPVC = eol["IncinerationPVC"]
    IncinerationElectronics = eol["IncinerationElectronics"]
    IncinerationLubricatingOil = eol["IncinerationLubricatingOil"]
    IncinerationHazardous = eol["IncinerationHazardous"]
    RecyclingMetals = eol["RecyclingMetals"]        # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]      # share of special metals recycled
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                      # substitution ratio, secondary vs primary
    LHVElastomer = eol["LHVElastomer"]              # lower heating values [MJ/kg], for the
    LHVHDPE = eol["LHVHDPE"]                        # energy recovered by incineration (D3)
    LHVElectronics = eol["LHVElectronics"]
    LHVHazardous = eol["LHVHazardous"]
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency

    # DASHBORD - VALUE INPUTS
    Boiler_BdName = energysystem['Building Name']
    Boiler_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Thermal capacity [kW]']
    Energy_produced = energysystem['Energy produced [kWh /year]']
    Efficiency = energysystem['Efficiency (between 0 and 1)']
    EnergyInputSource = energysystem['Energy source (Gas-blend, LPG, Biomethane, Hydrogen)']

    # DASHBOARD - INPUT PARAMETERS
    Efficiency_LHV = Efficiency

    # DEFAULT PARAMETERS
    # Lower and higher heating values of the fuel [MJ/m3]. The stated efficiency
    # is on the LHV, so both are needed.
    LHV = np.where(EnergyInputSource == 'Gas-blend', 36.8,
          np.where(EnergyInputSource == 'LPG', 93,
          np.where(EnergyInputSource == 'Biomethane', 35,
          np.where(EnergyInputSource == 'Hydrogen', 10.8, np.nan))))

    HHV = np.where(EnergyInputSource == 'Gas-blend', 40.4,
          np.where(EnergyInputSource == 'LPG', 102,
          np.where(EnergyInputSource == 'Biomethane', 38,
          np.where(EnergyInputSource == 'Hydrogen', 12.7, np.nan))))

    Efficiency_HHV = Efficiency_LHV*(LHV/HHV)  # Efficiency based on HHV

    TotEnergyNeeds = np.array([Energy_produced])  # Energy need for 1 year kWh per year

    # Define lifespan [years], by thermal capacity class
    Lifespan = np.where(Power <= 70, 19, np.where(Power <= 400, 21, 26))

    def calculate_mass(Power):
        """Boiler mass [kg] from thermal capacity [kW].

        Three regimes fitted to product data: a small-unit curve below 24.5 kW,
        a single-unit curve up to 100 kW, and above that a cascade of i units
        of up to 100 kW each.
        """
        if Power < 24.5:
            return 7.430 * np.log(Power) + 11.875
        elif 24.5 <= Power <= 100:
            return 140.86 * np.log(Power) - 415
        else:
            i = np.ceil(Power / 100)
            return (140.86 * np.log(Power / i) - 415) * i

    mass = Power.apply(calculate_mass)

    # --- Module A1-3: product stage --------------------------------------------
    # Material split as a fraction of unit mass [kg].
    Boiler_StainlessSteel = 0.156 * mass
    Boiler_Steel = 0.532 * mass
    Boiler_Aluminium = 0.128 * mass
    Boiler_Elastomer = 0.0003 * mass
    Boiler_PVC = 0.003 * mass
    # Note: the source inventory calls this component a refrigerant gas but
    # charges it against ABS copolymer here, then disposes of it as R134a at C3
    # and C4. Open question to the inventory authors; the three rows must
    # change together if it is settled.
    Boiler_RefrigerantGas = 0.065 * mass
    Boiler_Copper = 0.098 * mass
    Boiler_Electronic = np.ones(len(Power)) #kg
    # Brazing solder [kg], by capacity class: 4 up to 100 kW, 6 to 1 MW, 8 above.
    Boiler_Welding = np.where((0 <= Power) & (Power <= 100),
                              np.full(len(Power), 4),
                              np.where((100 < Power) & (Power <= 1000),
                                       np.full(len(Power), 6),
                                       np.full(len(Power), 8)
                                      )
                             )

    # Manufacturing inputs, linear in capacity [kW]: process water [kg], the
    # shares lost to air and water, wastewater treatment [m3], lubricating oil
    # [kg], electricity [kWh] and heat [MJ].
    Boiler_WaterConsumption = 6.21 * Power + 119.89
    Boiler_Emission_Water_Air = 0.015 * Boiler_WaterConsumption
    Boiler_Emission_Water_Water = 0.002 * Boiler_WaterConsumption
    Boiler_WasteWater_Treatment = (0.83 * Boiler_WaterConsumption) / 1000
    Boiler_Lubricating_Oil = 0.27 * Power          # [kg]
    Boiler_A13electricity = 0.59 * Power           # [kWh], medium-voltage market
    Boiler_Heat = 5.15 * Power                     # [MJ], district/industrial heat
    # Hazardous manufacturing waste [kg] by capacity class - zero above 1 MW.
    Boiler_Hazardous = np.where((0 <= Power) & (Power <= 100),
                                np.full(len(Power), 0.2),
                                np.where((100 < Power) & (Power <= 1000),
                                         np.full(len(Power), 0.3),
                                         np.full(len(Power), 0)
                                        )
                               )

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry and 50 km by light lorry.
    Boiler_Truck1632 = ((500 + 200)*(mass)/1000)
    Boiler_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # Service trips over the boiler's life [t.km]: 50 km per visit, one visit
    # every two years, carrying 1% of the unit mass in spare parts.
    Boiler_Light_Truck_B2 = 50 * (Lifespan/2) * 0.01 * (mass/1000)

    # --- Module B4: replacement within the study period -------------------------
    BoilerNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFBoiler = (RSP / Lifespan)  # Scaling factor

    # --- Module B6: operational energy over the study period --------------------
    # One-hot flags for the fuel burned.
    GasBlend   = np.where(EnergyInputSource == 'Gas-blend', 1, 0)
    Biomethane = np.where(EnergyInputSource == 'Biomethane', 1, 0)
    Hydrogen   = np.where(EnergyInputSource == 'Hydrogen', 1, 0)
    LPG        = np.where(EnergyInputSource == 'LPG', 1, 0)

    # Gas-blend composition: A natural gas, B biomethane, C hydrogen
    # (config.GAS_BLEND).
    A, B, C = config.GAS_BLEND

    TotEnergyNeeds = TotEnergyNeeds.flatten()

    # Heat delivered over the study period [MJ]: kWh/year x 3.6 MJ/kWh x RSP.
    y = (TotEnergyNeeds * 3.6 * RSP).flatten()

    # REPARTITION IN THE ENERGY SOURCE
    # Note: k = 1/39 [m3/MJ] is undocumented in the source inventory (39 MJ/m3
    # is close to the HHV of natural gas). It enters `x`, and so every
    # combustion emission and auxiliary electricity row. Open question to the
    # inventory authors.
    k = 0.0256410256410256

    # Fuel volume per unit of delivered heat.
    base = (1 / Efficiency_HHV) / (k * HHV)
    # h2_term = (1 / (Efficiency_HHV * (12.7 / 0.09)))

    # The commented-out branches are a year-by-year blend split (natural gas /
    # biomethane / hydrogen between 2030 and 2050), currently disabled.
    conditions = [
        (EnergyInputSource == 'Gas-blend'),
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
        (1 / Efficiency_HHV) / (k * HHV),
        (1 / Efficiency_HHV) / (k * HHV),
        (1 / (Efficiency_HHV * (12.7 / 0.09)))
    ]

    x = np.select(conditions, values, default=np.nan)

    # Grid / PV split of the auxiliary electricity. Placeholder values: all
    # auxiliary electricity is currently charged to the grid; the PV row is
    # kept wired for a future split.
    Grid = 1   # temporary
    PV = 0     # temporary
    Boiler_Electricity = 0.0136 * x * y * Grid      # [kWh], Italian low-voltage market
    Boiler_ElectricityPV = 0.0136 * x * y * PV      # [kWh], photovoltaic
    # Boiler_electricityRECSPV = Boiler_Electricity * 0.0056 * RECSPV
    # Boiler_electricityRECSHydro = Boiler_Electricity * 0.0056 * RECSHydro
    # Boiler_electricityRECSEolic = Boiler_Electricity * 0.0056 * RECSEolic

    # Fuel consumed over the study period: the three gas-blend components
    # (weighted by A, B, C), then the three pure fuels, each gated on its flag.
    # Units follow the wired datasets: natural gas and biomethane [m3], LPG
    # [kg, via config.LPG_DENSITY], hydrogen [kWh]. Hydrogen is modelled as
    # electrolysis powered by photovoltaic electricity: 120 MJ/kg / 3.6 at 90%
    # efficiency.
    Boiler_EnergyVectorNG = (((1 / (Efficiency_HHV * HHV))) * y) * A * GasBlend
    Boiler_EnergyVectorBiomethane = ((1 / (Efficiency_HHV * HHV)) * y) * B * GasBlend
    Boiler_EnergyVectorHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * C * GasBlend #120 MJ/kg
    Boiler_EnergyVectorBiomethaneInput = (((1 / (Efficiency_HHV * HHV))) * y) * Biomethane
    Boiler_EnergyVectorLPGinput = (((1 / (Efficiency_HHV * HHV))) * y) * LPG * config.LPG_DENSITY
    Boiler_EnergyVectorHydrogeninput = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * Hydrogen

    # Combustion emissions over the study period: an emission factor per unit
    # of fuel burned (x * y). Biosphere flows, in kg (cubic metres for the water
    # flows). The last five (...H) are the bulk flue-gas components: water
    # vapour, nitrogen, oxygen, NOx and condensate.
    Boiler_Acetaldehyde = 0.000000001* x * y
    Boiler_AceticAcid = 0.00000015* x * y
    Boiler_Benzene = 0.0000004* x * y
    Boiler_Benzoapyrene = 0.00000000001* x * y
    Boiler_Butane = 0.0000007* x * y
    Boiler_CarbonDioxideFossil = 0.056* x * y
    Boiler_CarbonMonoxideFossil = 0.00003* x * y
    Boiler_DinitrogenMonoxide = 0.0000005* x * y
    Boiler_Formaldehyde = 0.0000001* x * y
    Boiler_Mercury = 0.00000000003* x * y
    Boiler_MethaneFossil = 0.000002* x * y
    Boiler_NitrogenOxides = 0.00002* x * y
    Boiler_PAH = 0.00000001* x * y
    Boiler_Particulates = 0.0000001* x * y
    Boiler_Pentane = 0.0000012* x * y
    Boiler_Propane = 0.0000002* x * y
    Boiler_PropionicAcid = 0.00000002* x * y
    Boiler_SulfurDioxide = 0.0000005* x * y
    Boiler_Toluene = 0.0000002* x * y
    Boiler_Nitrate = 0.00000013* x * y
    Boiler_Nitrite = 0.000000003* x * y
    Boiler_Sulfate = 0.00000005* x * y
    Boiler_Sulfite = 0.00000005* x * y
    Boiler_WatervaporH = 6.79E-01 * x * y
    Boiler_NitrogenH = 3.29E+01 * x * y
    Boiler_OxygenH = 2.00E+00 * x * y
    Boiler_NOXH = 2.83E-03 * x * y
    Boiler_WatercondensateH = 8.32E+00 * x * y

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km to the treatment plant [t.km].
    Boiler_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    # The whole unit reaches end of life, so each material is carried over as-is.
    Boiler_EOL_StainlessSteel = Boiler_StainlessSteel
    Boiler_EOL_Steel = Boiler_Steel
    Boiler_EOL_Aluminium = Boiler_Aluminium
    Boiler_EOL_Elastomer = Boiler_Elastomer
    Boiler_EOL_PVC = Boiler_PVC
    Boiler_EOL_RefrigerantGas = Boiler_RefrigerantGas
    Boiler_EOL_Copper = Boiler_Copper
    Boiler_EOL_Electronic = Boiler_Electronic #kg
    Boiler_EOL_Lubricating_Oil = Boiler_Lubricating_Oil #kg
    Boiler_EOL_Hazardous = Boiler_Hazardous #kg

    # --- Module C4: final disposal ----------------------------------------------
    # Each material times the share of it that is landfilled or incinerated.
    Boiler_EOL_Landfill_StainlessSteel = Boiler_EOL_StainlessSteel * LandfillMetals2
    Boiler_EOL_Landfill_Steel = Boiler_EOL_Steel * LandfillMetals
    Boiler_EOL_Landfill_Aluminium = Boiler_EOL_Aluminium * LandfillMetals
    Boiler_EOL_Inc_Elastomer = Boiler_EOL_Elastomer * IncinerationElastomer
    Boiler_EOL_Landfill_Elastomer = Boiler_EOL_Elastomer * LandfillElastomer
    Boiler_EOL_Inc_PVC = Boiler_EOL_PVC * IncinerationPVC
    Boiler_EOL_Landfill_PVC = Boiler_EOL_PVC * LandfillPVC
    # LandfillRefrigerant is 1.0: the whole component is landfilled as a
    # refrigerant (see the A1-3 note).
    Boiler_EOL_Landfill_RefrigerantGas = Boiler_EOL_RefrigerantGas * LandfillRefrigerant
    Boiler_EOL_Landfill_Copper = Boiler_EOL_Copper * LandfillMetals
    Boiler_EOL_Inc_Electronic = Boiler_EOL_Electronic * IncinerationElectronics #kg
    Boiler_EOL_Landfill_Electronic = Boiler_EOL_Electronic * LandfillElectronics #kg
    Boiler_EOL_Inc_LubricatingOil = Boiler_Lubricating_Oil * IncinerationLubricatingOil #kg
    Boiler_EOL_Inc_HazardousWaste = Boiler_Hazardous * IncinerationHazardous #kg

    # --- Module D1: credit for exported secondary materials ---------------------
    # Recycling: net secondary material exported; Primary: the displaced primary
    # production (sign reversed, times the substitution ratio).
    Boiler_EOL_Recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * Boiler_EOL_StainlessSteel) - (RecycledContentMetals * Boiler_EOL_StainlessSteel)
    Boiler_EOL_Primary_StainlessSteel = ((RecycledContentMetals * Boiler_EOL_StainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * Boiler_EOL_StainlessSteel)) * SRmetals

    Boiler_EOL_Recycling_Steel = (RecyclingMetals * RecyclingEfficiencyMetals * Boiler_EOL_Steel) - (RecycledContentMetals * Boiler_EOL_Steel)
    Boiler_EOL_Primary_Steel = ((RecycledContentMetals * Boiler_EOL_Steel) - (RecyclingMetals * RecyclingEfficiencyMetals * Boiler_EOL_Steel)) * SRmetals

    Boiler_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * Boiler_EOL_Aluminium) - (RecycledContentMetals * Boiler_EOL_Aluminium)
    Boiler_EOL_Primary_Aluminium = ((RecycledContentMetals * Boiler_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * Boiler_EOL_Aluminium)) * SRmetals

    Boiler_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * Boiler_EOL_Copper) - (RecycledContentMetals * Boiler_EOL_Copper)
    Boiler_EOL_Primary_Copper = ((RecycledContentMetals * Boiler_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * Boiler_EOL_Copper)) * SRmetals

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    Boiler_EOL_EnergyRecoveryHeat_Elastomer = - Boiler_EOL_Inc_Elastomer * LHVElastomer * Xincheat
    Boiler_EOL_EnergyRecoveryEle_Elastomer = - Boiler_EOL_Inc_Elastomer * LHVElastomer * Xincele / config.MJ_PER_KWH
    Boiler_EOL_EnergyRecoveryHeat_PVC = - Boiler_EOL_Inc_PVC * LHVHDPE * Xincheat
    Boiler_EOL_EnergyRecoveryEle_PVC = - Boiler_EOL_Inc_PVC * LHVHDPE * Xincele / config.MJ_PER_KWH
    Boiler_EOL_EnergyRecoveryHeat_Electronics = - Boiler_EOL_Inc_Electronic * LHVElectronics * Xincheat
    Boiler_EOL_EnergyRecoveryEle_Electronics = - Boiler_EOL_Inc_Electronic * LHVElectronics * Xincele / config.MJ_PER_KWH
    Boiler_EOL_EnergyRecoveryHeat_LubricatingOil = - Boiler_EOL_Inc_LubricatingOil * LHVHazardous * Xincheat
    Boiler_EOL_EnergyRecoveryEle_LubricatingOil = - Boiler_EOL_Inc_LubricatingOil * LHVHazardous * Xincele / config.MJ_PER_KWH
    Boiler_EOL_EnergyRecoveryHeat_HazardousWaste = - Boiler_EOL_Inc_HazardousWaste * LHVHazardous * Xincheat
    Boiler_EOL_EnergyRecoveryEle_HazardousWaste = - Boiler_EOL_Inc_HazardousWaste * LHVHazardous * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_Boiler = Energy_produced * RSP

    # Collect every 'Boiler_' quantity for the exchange rows. locals() is bound
    # before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("Boiler_")}
    # Labels, not quantities: returned separately below.
    activity_data.pop("Boiler_BdName")
    activity_data.pop("Boiler_BdArea")

    return {
        "activity_data": activity_data,
        "sf": SFBoiler,
        "replacements": BoilerNumberReplacements,
        "bd_names": Boiler_BdName,
        "bd_areas": Boiler_BdArea,
        "thermal_energy": ThermalEnergyProduced_Boiler,
    }
