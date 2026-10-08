"""
chp_orc.py - life-cycle inventory of an Organic Rankine Cycle CHP plant.

A biomass furnace raising heat, an ORC turbine turning part of it into power,
and a dust collector cleaning the flue gas. The working fluid is
perfluoropentane, which appears as a hazardous-waste stream at end of life. The
fuel is wood: heating values are per kilogram.

Modules A1-3 to B6 are multiplied by AFQ_ORC, the share of the burden
allocated to HEAT (the electricity leaves the system boundary); the two
allocation methods are the same as chp_turbogas.py's.
Note: from module C2 onwards the allocation factor is not applied, so the
whole plant is disposed of against the heat service. Open question.

The plant is inventoried component by component: A1-3 buys a dust collector, a
furnace and an ORC module as whole ecoinvent units, and modules C3 onwards
resolve them into materials, so end-of-life names carry the component as a
suffix (...Dustcollector, ...Furnace, ...CHP). See energy_systems/__init__.py
for the conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the ORC plants.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'CHP-Organic Rankine Cycle'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("CHP-Organic Rankine Cycle")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillClaybrick = eol["LandfillClaybrick"]
    LandfillConcrete = eol["LandfillConcrete"]
    LandfillElectronics = eol["LandfillElectronics"]
    LandfillGlass = eol["LandfillGlass"]
    LandfillMetals = eol["LandfillMetals"]          # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    LandfillMineralWool = eol["LandfillMineralWool"]
    LandfillPEHD = eol["LandfillPEHD"]
    IncinerationElectronics = eol["IncinerationElectronics"]
    IncinerationEPS = eol["IncinerationEPS"]
    IncinerationHazardous = eol["IncinerationHazardous"]
    IncinerationLubricatingOil = eol["IncinerationLubricatingOil"]
    IncinerationPEHD = eol["IncinerationPEHD"]
    RecyclingConcrete = eol["RecyclingConcrete"]
    RecyclingMetals = eol["RecyclingMetals"]        # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]      # share of special metals recycled
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingEfficiencyConcrete = eol["RecyclingEfficiencyConcrete"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecycledContentClaybrick = eol["RecycledContentClaybrick"]
    RecyclingClaybrick = eol["RecyclingClaybrick"]
    RecyclingEfficiencyClaybrick = eol["RecyclingEfficiencyClaybrick"]
    RecycledContentConcrete = eol["RecycledContentConcrete"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    SRclaybrick = eol["SRclaybrick"]                # substitution ratios, secondary vs primary
    SRmetals = eol["SRmetals"]
    SRinert = eol["SRinert"]
    LHVElectronics = eol["LHVElectronics"]          # lower heating values [MJ/kg], for the
    LHVEPS = eol["LHVEPS"]                          # energy recovered by incineration (D3)
    LHVHDPE = eol["LHVHDPE"]
    LHVHazardous = eol["LHVHazardous"]
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency


    # DASHBOARD - VALUE INPUT - SPECIFIC DATA
    # 'Multifunctionality Approach' selects the allocation method; the three
    # temperatures drive the Carnot factor of the default method. WasteO says
    # whether the biomass is a waste rather than a purchased fuel (module B6).
    # EquivalentHours [h/year] is the full-load running time.
    # DASHBOARD - VALUE INPUT - SPECIFIC DATA
    CHP_ORC_BdName = energysystem['Building Name']
    CHP_ORC_BdArea = energysystem['Zone net floor area [m2]']
    Multifunctionality = energysystem['Multifunctionality Approach']
    Power = energysystem['Thermal capacity [kW]']
    EfficiencyW = energysystem['Electrical efficiency based on LHV (between 0 and 1)']
    EfficiencyQ = energysystem['Heat efficiency based on LHV (between 0 and 1)']
    ElectricEnergyproduced = energysystem['Electric energy produced in a year (exported and consumed) [kWh /year]']
    ThermalEnergyproduced_primary = energysystem['Thermal energy produced used [kWh /year]']
    Qused = 1
    WasteO = energysystem["Biomass used as a waste ['yes' or 'no']"]
    ExternalTemperature = energysystem['External temperature [°C]']
    SupplyTemperature = energysystem['Supply temperature [°C]']
    ReturnTemperature = energysystem['Return temperature [°C]']
    EquivalentHours = ThermalEnergyproduced_primary / Power

    # DEFAULT PARAMETERS and energy balance.
    # Heating values per kg of wood. Lifespan [years]: rated operating hours
    # (40,000 below 25 kW electrical, 100,000 above) divided by the full-load
    # hours per year. The fuel input over the study period is divided by the
    # thermal efficiency (heat-led plant).
    # Note: the gas-fired CHPs divide by the electrical efficiency instead;
    # which is intended is an open question to the inventory authors.
    HHV = 18.9  # In MJ per kg
    LHV = 18 #MJ per kg

    Lifespan = np.where(
        Power * (EfficiencyW / EfficiencyQ)  < 25,
        40000 / EquivalentHours,
        100000 / EquivalentHours
    )

    # ADDITIONAL CALCULATIONS
    EfficiencyTot = EfficiencyW + EfficiencyQ
    EnergyProducedLHV = (Power * EquivalentHours * RSP) / EfficiencyQ
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
    #     AFQ_ORC = (ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature))) / (ElectricEnergyproduced + ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature)))
    #     AFQ_ORC = np.array(AFQ_ORC)

    #     # AFW calculation
    #     AFW_ORC = (1 - AFQ_ORC)

    # else:
    #     fwecr = 0.7
    #     fweexp = fwecr

    #     # Calculations
    #     InletEnergyCogenmode = EnergyProducedHHV * EfficiencyTot
    #     AFW_ORC = (InletEnergyCogenmode * fwecr - (ElectricEnergyproduced * fweexp)) / EnergyProducedHHV
    #     AFQ_ORC = 1 - AFW_ORC

    # if SupplyTemperature.eq(0).all() and ReturnTemperature.eq(0).all():
    #     AFQ_ORC = np.zeros_like(AFQ_ORC)
    #     AFW_ORC = np.zeros_like(AFW_ORC)

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
    AFW_ORC_else = (InletEnergyCogenmode * fwecr - (ElectricEnergyproduced * fweexp)) / EnergyProducedHHV
    AFQ_ORC_else = 1 - AFW_ORC_else

    # Calculations for 'Default' condition
    ExternalTemperature = ExternalTemperature + 273.15 #K
    SupplyTemperature = SupplyTemperature + 273.15 #K
    ReturnTemperature = ReturnTemperature + 273.15 #K
    CarnotTemperature = (SupplyTemperature - ReturnTemperature) / np.log(SupplyTemperature / ReturnTemperature)
    ThermalEnergyproduced = EnergyProducedHHV
    ElectricEnergyproduced = (EnergyProducedHHV / EfficiencyQ) * EfficiencyW

    # AFQ calculation
    AFQ_ORC_default = (ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature))) / (ElectricEnergyproduced + ThermalEnergyproduced * (1 - (ExternalTemperature / CarnotTemperature)))
    AFQ_ORC_default = np.array(AFQ_ORC_default)

    # AFW calculation
    AFW_ORC_default = (1 - AFQ_ORC_default)

    # Apply conditions row by row
    AFQ_ORC = np.where(Multifunctionality == 'Default', AFQ_ORC_default, AFQ_ORC_else)
    AFW_ORC = np.where(Multifunctionality == 'Default', AFW_ORC_default, AFW_ORC_else)

    # Handle zero temperatures row by row
    zero_mask = (SupplyTemperature == 273.15) & (ReturnTemperature == 273.15)
    AFQ_ORC = np.where(zero_mask, 0, AFQ_ORC)
    AFW_ORC = np.where(zero_mask, 0, AFW_ORC)

    # --- Module A1-3: manufacture ---------------------------------------------
    # Component counts [unit], allocated to heat: a dust collector, furnaces of
    # the 1 MW reference and ORC modules of the 200 kW reference, by size
    # bracket (below 500 kW, 500-2000 kW, above 2000 kW as i modules of
    # 2000 kW), applied per building.
    brackets = [
        Power < 500,
        (Power >= 500) & (Power < 2000),
        Power >= 2000,
    ]
    Power_op = np.array(Power)
    i = np.ceil(Power_op/2000)

    CHP_ORC_DustCollector = np.select(brackets, [
        np.full(len(Power_op), 1) * AFQ_ORC,
        np.full(len(Power_op), 1) * AFQ_ORC,
        (np.full(len(Power_op), 1) * i * AFQ_ORC).flatten(),
    ])
    CHP_ORC_Furnace = np.select(brackets, [
        Power_op/1000 * AFQ_ORC,
        (Power_op/1000) * AFQ_ORC,
        (Power_op/1000) * i * AFQ_ORC,
    ])
    CHP_ORC_CHP = np.select(brackets, [
        Power_op/200 * AFQ_ORC,
        (Power_op/1000) * AFQ_ORC,
        (Power_op/3000) * i * AFQ_ORC,
    ])

    # --- Module A4: transport to site -----------------------------------------
    # Whole-plant mass [kg] from ecoinvent, by size bracket. Freight [t.km]:
    # 700 km by heavy lorry, 50 km by light lorry.
    mass = np.where(Power < 500, 385977, 403394.5)   #kg  ecoinvent data

    mass = np.full(len(Power), mass)
    CHP_ORC_Truck1632 = ((500 + 200)*(mass)/1000) * AFQ_ORC
    CHP_ORC_Light_Truck = (50*(mass)/1000) * AFQ_ORC

    # --- Module B2: maintenance transport --------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the plant mass.
    mass = np.full(len(Power), mass)
    CHP_ORC_Light_Truck_B2 = (50 * (Lifespan/2) * 0.01 * (mass/1000)) * AFQ_ORC

    # --- Module B4: replacement within the study period ------------------------
    ORCNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFORC = (RSP / Lifespan)  # Scaling factor

    # --- Module B6: fuel, consumables and combustion emissions -----------------
    # y is the fuel input over the study period [MJ], allocated to heat; x = 1.
    # First the operating consumables and residues (ammonia, organic chemical,
    # chlorine, mineral oil, NOx retained by selective catalytic reduction,
    # sodium chloride, water and the wood fuel), then the combustion emissions.
    # CHP_ORC_NOx (abatement reagent) and CHP_ORC_NitrogenOxides (emission to
    # air) are different flows, as are CHP_ORC_Chlorine / CHP_ORC_Chlorineair
    # and CHP_ORC_Sodium / CHP_ORC_Sodiumair (purchase / emission).
    x = 1
    TotEnergyNeeds = np.array([EnergyProducedHHV])
    TotEnergyNeeds = TotEnergyNeeds.flatten()
    y = (TotEnergyNeeds * 3.6).flatten() * AFQ_ORC

    CHP_ORC_Ammonia1 = (0.0000000082 * x * y).flatten()
    CHP_ORC_Chemical = (5.84999999999999E-06 * x * y).flatten()
    CHP_ORC_Chlorine = (0.000000328 * x * y).flatten()
    CHP_ORC_Oil = (0.00000328 * x * y).flatten()
    CHP_ORC_NOx = (0.0000269859002222463 * x * y).flatten()
    CHP_ORC_Sodium = (0.0000041 * x * y).flatten()
    CHP_ORC_Water = (0.000786999999999999 * x * y).flatten()
    # No wood is purchased when the biomass is declared a waste.
    if (WasteO == 'yes').all():
        CHP_ORC_Wood = np.zeros_like((x * y).flatten())
    else:
        CHP_ORC_Wood = (0.000529100529100529 * x * y).flatten()

    CHP_ORC_Acetaldehyde = (4.57261087099173E-08 * x * y).flatten()
    CHP_ORC_Ammonia2 = (0.0000127433417716163 * x * y).flatten()
    CHP_ORC_Benzene = (6.82143588951226E-07 * x * y).flatten()
    CHP_ORC_Benzeneethyl = (2.24882501852052E-08 * x * y).flatten()
    CHP_ORC_Benzenehexachloro = (5.39718004444926E-15 * x * y).flatten()
    CHP_ORC_Benzoapyrene = (3.74804169753421E-10 * x * y).flatten()
    CHP_ORC_Bromine = (4.49765003704105E-08 * x * y).flatten()
    CHP_ORC_Cadmium = (5.24725837654789E-10 * x * y).flatten()
    CHP_ORC_Calcium = (4.38520878611502E-06 * x * y).flatten()
    CHP_ORC_CarbonDioxideBiogenic = ((0.0719624005926568) * x * y).flatten()
    CHP_ORC_CarbonMonoxideBiogenic = ((0.0000749608339506842) * x * y).flatten()
    CHP_ORC_Chlorineair = (1.34929501111231E-07 * x * y).flatten()
    CHP_ORC_Chromium = (2.96844902444709E-09 * x * y).flatten()
    CHP_ORC_ChromiumVI = (2.99843335802737E-11 * x * y).flatten()
    CHP_ORC_Copper = (1.64913834691505E-08 * x * y).flatten()
    CHP_ORC_DinitrogenMonoxide = (1.72409918086574E-06 * x * y).flatten()
    CHP_ORC_Dioxin = (2.32378585247121E-14 * x * y).flatten()
    CHP_ORC_Fluorine = (3.74804169753421E-08 * x * y).flatten()
    CHP_ORC_Formaldehyde = (9.74490841358894E-08 * x * y).flatten()
    CHP_ORC_Hydrocarbonsaliphaticalkanesunspecified = (6.82143588951226E-07 * x * y).flatten()
    CHP_ORC_Hydrocarbonsaliphaticunsaturated = (2.32378585247121E-06 * x * y).flatten()
    CHP_ORC_Lead = (1.8740208487671E-08 * x * y).flatten()
    CHP_ORC_Magnesium = (2.69859002222463E-07 * x * y).flatten()
    CHP_ORC_Manganese = (1.27433417716163E-07 * x * y).flatten()
    CHP_ORC_Mercury = (2.24882501852052E-10 * x * y).flatten()
    CHP_ORC_Methanebiogenic = (8.9953000740821E-07 * x * y).flatten()
    CHP_ORC_MXylene = (8.9953000740821E-08 * x * y).flatten()
    CHP_ORC_Nickel = (4.49765003704105E-09 * x * y).flatten()
    CHP_ORC_NitrogenOxides = (0.0000599686671605473 * x * y).flatten()
    CHP_ORC_NMVOC = (2.09890335061916E-06 * x * y).flatten()
    CHP_ORC_PAH = (8.32065256852594E-09 * x * y).flatten()
    CHP_ORC_Particulates = (3.74804169753421E-06 * x * y).flatten()
    CHP_ORC_Phenolpentachloro = (6.07182755000542E-12 * x * y).flatten()
    CHP_ORC_Phosphorus = (2.24882501852052E-07 * x * y).flatten()
    CHP_ORC_Potassium = (0.0000175408351444601 * x * y).flatten()
    CHP_ORC_Sodiumair = (9.74490841358894E-07 * x * y).flatten()
    CHP_ORC_SulfurDioxide = (0.0000018740208487671 * x * y).flatten()
    CHP_ORC_Toluene = (2.24882501852052E-07 * x * y).flatten()
    CHP_ORC_Watermc = (0.0000436272053592982 * x * y).flatten()
    CHP_ORC_Zinc = (2.24882501852052E-07 * x * y).flatten()
    CHP_ORC_Solidwaste = (0.00000328 * x * y).flatten()
    CHP_ORC_MineralOilWaste = (0.00000328 * x * y).flatten()
    CHP_ORC_WasteWater = (0.000000787 * x * y).flatten()

    # --- Module C2: transport to the treatment plant ---------------------------
    # 50 km [t.km], with the A4 mass brackets. Not allocated to heat.
    mass = np.where(Power < 500, 385977, 403394.5)   #kg ecoinvent data

    mass = np.full(len(Power), mass)
    CHP_ORC_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing ------------------------------------------
    # The three A1-3 components resolved into materials [kg], per 200 kW of
    # thermal capacity (Power / 200). Not allocated to heat (see the module
    # docstring). Furnace concrete is in [kg] here.
    CHP_ORC_EOL_AluminiumDustcollector = (12 * Power) / 200
    CHP_ORC_EOL_CeramictileDustcollector = (42 * Power) / 200
    CHP_ORC_EOL_CopperDustcollector = (37 * Power) / 200
    CHP_ORC_EOL_DrawingpipeSteelDustcollector = (83 * Power) / 200
    CHP_ORC_EOL_ElectronicsDustcollector = (5 * Power) / 200
    CHP_ORC_EOL_GlasswoolmatDustcollector = (55 * Power) / 200
    CHP_ORC_EOL_HDPEDustcollector = (31 * Power) / 200
    CHP_ORC_EOL_SheetrollingsteelDustcollector = (83 * Power) / 200
    CHP_ORC_EOL_ChromiumsteelDustcollector = (810 * Power) / 200
    CHP_ORC_EOL_LowalloyedsteelDustcollector = (690 * Power) / 200
    CHP_ORC_EOL_AlkydpaintFurnace = (12 * Power) / 200
    CHP_ORC_EOL_AluminiumFurnace = (104 * Power) / 200
    CHP_ORC_EOL_CastironFurnace = (1115 * Power) / 200
    CHP_ORC_EOL_ConcreteFurnace = (134400 * Power) / 200
    CHP_ORC_EOL_CopperFurnace = (46 * Power) / 200
    CHP_ORC_EOL_DrawingpipeFurnace = (37410 * Power) / 200
    CHP_ORC_EOL_ElectronicsFurnace = (12 * Power) / 200
    CHP_ORC_EOL_IronnickelchromiumalloyFurnace = (528 * Power) / 200
    CHP_ORC_EOL_LubricatingoilFurnace = (32 * Power) / 200
    CHP_ORC_EOL_HDPEFurnace = (18 * Power) / 200
    CHP_ORC_EOL_PolystyreneFurnace = (361 * Power) / 200
    CHP_ORC_EOL_ClaybrickFurnace = (41220 * Power) / 200
    CHP_ORC_EOL_SheetrollingsteelFurnace = (37410 * Power) / 200
    CHP_ORC_EOL_ChromiumsteelFurnace = (70 * Power) / 200
    CHP_ORC_EOL_LowalloyedsteelFurnace = (74820 * Power) / 200
    CHP_ORC_EOL_StonewoolFurnace = (1846 * Power) / 200

    # ORC module materials, by size bracket (below / above 500 kW).
    small = Power < 500
    CHP_ORC_EOL_CopperCHP = np.where(small, (67 * Power) / 200, (87.1 * Power) / 200)
    CHP_ORC_EOL_ElectronicsCHP = np.where(small, (30 * Power) / 200, (39 * Power) / 200)
    CHP_ORC_EOL_PerfluoropentaneCHP = np.where(small, (1200 * Power) / 200, (1560 * Power) / 200)
    CHP_ORC_EOL_HDPECHP = np.where(small, (18 * Power) / 200, (23.4 * Power) / 200)
    CHP_ORC_EOL_ChromiumsteelCHP = np.where(small, (7950 * Power) / 200, (10335 * Power) / 200)
    CHP_ORC_EOL_LowalloyedsteelCHP = np.where(small, (45050 * Power) / 200, (58565 * Power) / 200)
    CHP_ORC_EOL_StonewoolCHP = np.where(small, (410 * Power) / 200, (533 * Power) / 200)

    # --- Module C4: disposal ---------------------------------------------------
    # The landfilled and incinerated shares of each material [kg].
    #
    # Alkyd paint has no end-of-life share parameter and is 100% incinerated.
    CHP_ORC_EOL_Landfill_AluminiumDustcollector = CHP_ORC_EOL_AluminiumDustcollector * LandfillMetals
    CHP_ORC_EOL_Landfill_CeramictileDustcollector = CHP_ORC_EOL_CeramictileDustcollector * LandfillClaybrick
    CHP_ORC_EOL_Landfill_CopperDustcollector = CHP_ORC_EOL_CopperDustcollector * LandfillMetals
    CHP_ORC_EOL_Landfill_DrawingpipesteelDustcollector = CHP_ORC_EOL_DrawingpipeSteelDustcollector * LandfillMetals
    CHP_ORC_EOL_Inc_ElectronicsDustcollector = CHP_ORC_EOL_ElectronicsDustcollector * IncinerationElectronics #kg
    CHP_ORC_EOL_Landfill_ElectronicsDustcollector = CHP_ORC_EOL_ElectronicsDustcollector * LandfillElectronics #kg
    CHP_ORC_EOL_Landfill_GlasswoolmatDustcollector = CHP_ORC_EOL_GlasswoolmatDustcollector * LandfillGlass #kg
    CHP_ORC_EOL_Inc_HDPEDustcollector = CHP_ORC_EOL_HDPEDustcollector * IncinerationPEHD
    CHP_ORC_EOL_Landfill_HDPEDustcollector = CHP_ORC_EOL_HDPEDustcollector * LandfillPEHD
    CHP_ORC_EOL_Landfill_SheetrollingsteelDustcollector = CHP_ORC_EOL_SheetrollingsteelDustcollector * LandfillMetals
    CHP_ORC_EOL_Landfill_ChromiumsteelDustcollector = CHP_ORC_EOL_ChromiumsteelDustcollector * LandfillMetals2
    CHP_ORC_EOL_Landfill_LowalloyedsteelDustcollector = CHP_ORC_EOL_LowalloyedsteelDustcollector * LandfillMetals
    CHP_ORC_EOL_Inc_AlkydpaintFurnace = CHP_ORC_EOL_AlkydpaintFurnace
    CHP_ORC_EOL_Landfill_AluminiumFurnace = CHP_ORC_EOL_AluminiumFurnace * LandfillMetals
    CHP_ORC_EOL_Landfill_CastironFurnace = CHP_ORC_EOL_CastironFurnace * LandfillMetals2
    CHP_ORC_EOL_Landfill_ConcreteFurnace = CHP_ORC_EOL_ConcreteFurnace * LandfillConcrete
    CHP_ORC_EOL_Landfill_CopperFurnace = CHP_ORC_EOL_CopperFurnace * LandfillMetals
    CHP_ORC_EOL_Landfill_DrawingpipesteelFurnace = CHP_ORC_EOL_DrawingpipeFurnace * LandfillMetals
    CHP_ORC_EOL_Inc_ElectronicsFurnace = CHP_ORC_EOL_ElectronicsFurnace * IncinerationElectronics #kg
    CHP_ORC_EOL_Landfill_ElectronicsFurnace = CHP_ORC_EOL_ElectronicsFurnace * LandfillElectronics #kg
    CHP_ORC_EOL_Landfill_IronnickelchromiumalloyFurnace = CHP_ORC_EOL_IronnickelchromiumalloyFurnace * LandfillMetals
    CHP_ORC_EOL_Inc_LubricatingoilFurnace = CHP_ORC_EOL_LubricatingoilFurnace * IncinerationLubricatingOil #kg
    CHP_ORC_EOL_Inc_HDPEFurnace = CHP_ORC_EOL_HDPEFurnace * IncinerationPEHD
    CHP_ORC_EOL_Landfill_HDPEFurnace = CHP_ORC_EOL_HDPEFurnace * LandfillPEHD
    CHP_ORC_EOL_Inc_PolystyreneFurnace = CHP_ORC_EOL_PolystyreneFurnace * IncinerationEPS
    CHP_ORC_EOL_Landfill_ClaybrickFurnace = CHP_ORC_EOL_ClaybrickFurnace * LandfillClaybrick
    CHP_ORC_EOL_Landfill_SheetrollingsteelFurnace = CHP_ORC_EOL_SheetrollingsteelFurnace * LandfillMetals
    CHP_ORC_EOL_Landfill_ChromiumsteelFurnace = CHP_ORC_EOL_ChromiumsteelFurnace * LandfillMetals2
    CHP_ORC_EOL_Landfill_LowalloyedsteelFurnace = CHP_ORC_EOL_LowalloyedsteelFurnace * LandfillMetals
    CHP_ORC_EOL_Landfill_StonewoolFurnace = CHP_ORC_EOL_StonewoolFurnace * LandfillMineralWool
    CHP_ORC_EOL_Landfill_CopperCHP = CHP_ORC_EOL_CopperCHP * LandfillMetals
    CHP_ORC_EOL_Inc_ElectronicsCHP = CHP_ORC_EOL_ElectronicsCHP * IncinerationElectronics #kg
    CHP_ORC_EOL_Landfill_ElectronicsCHP = CHP_ORC_EOL_ElectronicsCHP * LandfillElectronics #kg
    CHP_ORC_EOL_Inc_PerfluoropentaneCHP = CHP_ORC_EOL_PerfluoropentaneCHP * IncinerationHazardous #kg
    CHP_ORC_EOL_Inc_HDPECHP = CHP_ORC_EOL_HDPECHP * IncinerationPEHD
    CHP_ORC_EOL_Landfill_HDPEDCHP = CHP_ORC_EOL_HDPECHP * LandfillPEHD
    CHP_ORC_EOL_Landfill_ChromiumsteelCHP = CHP_ORC_EOL_ChromiumsteelCHP * LandfillMetals2
    CHP_ORC_EOL_Landfill_LowalloyedsteelCHP = CHP_ORC_EOL_LowalloyedsteelCHP * LandfillMetals
    CHP_ORC_EOL_Landfill_StonewoolCHP = CHP_ORC_EOL_StonewoolCHP * LandfillMineralWool

    # --- Module D1: recycling credits and primary-production burdens ------------
    # Chromium steel and the iron-nickel-chromium alloy are special metals
    # (RecyclingMetals2) in D1.
    # Note: the alloy is landfilled with LandfillMetals (common metals) but
    # recycled with RecyclingMetals2; which family it belongs to is an open
    # question to the inventory authors.
    CHP_ORC_EOL_Recycling_AluminiumDustcollector = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_AluminiumDustcollector) - (RecycledContentMetals * CHP_ORC_EOL_AluminiumDustcollector)
    CHP_ORC_EOL_Primary_AluminiumDustcollector = ((RecycledContentMetals * CHP_ORC_EOL_AluminiumDustcollector) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_AluminiumDustcollector))* SRmetals

    CHP_ORC_EOL_Recycling_CopperDustcollector = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_CopperDustcollector) - (RecycledContentMetals * CHP_ORC_EOL_CopperDustcollector)
    CHP_ORC_EOL_Primary_CopperDustcollector = ((RecycledContentMetals * CHP_ORC_EOL_CopperDustcollector) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_CopperDustcollector))* SRmetals

    CHP_ORC_EOL_Recycling_DrawingpipeDustcollector = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_DrawingpipeSteelDustcollector) - (RecycledContentMetals * CHP_ORC_EOL_DrawingpipeSteelDustcollector)
    CHP_ORC_EOL_Primary_DrawingpipeDustcollector = ((RecycledContentMetals * CHP_ORC_EOL_DrawingpipeSteelDustcollector) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_DrawingpipeSteelDustcollector))* SRmetals

    CHP_ORC_EOL_Recycling_HDPEDustcollector = (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_ORC_EOL_HDPEDustcollector) - (RecycledContentPlastic * CHP_ORC_EOL_HDPEDustcollector)
    CHP_ORC_EOL_Primary_HDPEDustcollector = ((RecycledContentPlastic * CHP_ORC_EOL_HDPEDustcollector) - (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_ORC_EOL_HDPEDustcollector))* SRinert

    CHP_ORC_EOL_Recycling_SheetrollingsteelDustcollector = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_SheetrollingsteelDustcollector) - (RecycledContentMetals * CHP_ORC_EOL_SheetrollingsteelDustcollector)
    CHP_ORC_EOL_Primary_SheetrollingsteelDustcollector = ((RecycledContentMetals * CHP_ORC_EOL_SheetrollingsteelDustcollector) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_SheetrollingsteelDustcollector))* SRmetals

    CHP_ORC_EOL_Recycling_ChromiumsteelDustcollector = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_ChromiumsteelDustcollector) - (RecycledContentMetals * CHP_ORC_EOL_ChromiumsteelDustcollector)
    CHP_ORC_EOL_Primary_ChromiumsteelDustcollector = ((RecycledContentMetals * CHP_ORC_EOL_ChromiumsteelDustcollector) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_ChromiumsteelDustcollector))* SRmetals

    CHP_ORC_EOL_Recycling_LowalloyedsteelDustcollector = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_LowalloyedsteelDustcollector) - (RecycledContentMetals * CHP_ORC_EOL_LowalloyedsteelDustcollector)
    CHP_ORC_EOL_Primary_LowalloyedsteelDustcollector = ((RecycledContentMetals * CHP_ORC_EOL_LowalloyedsteelDustcollector) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_LowalloyedsteelDustcollector))* SRmetals

    CHP_ORC_EOL_Recycling_AluminiumFurnace = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_AluminiumFurnace) - (RecycledContentMetals * CHP_ORC_EOL_AluminiumFurnace)
    CHP_ORC_EOL_Primary_AluminiumFurnace = ((RecycledContentMetals * CHP_ORC_EOL_AluminiumFurnace) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_AluminiumFurnace))* SRmetals

    # Cast iron is treated as a special metal (LandfillMetals2 /
    # RecyclingMetals2). Note: which family it belongs to is an open question.
    CHP_ORC_EOL_Recycling_CastironFurnace = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_CastironFurnace) - (RecycledContentMetals * CHP_ORC_EOL_CastironFurnace)
    CHP_ORC_EOL_Primary_CastironFurnace = ((RecycledContentMetals * CHP_ORC_EOL_CastironFurnace) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_CastironFurnace))* SRmetals

    CHP_ORC_EOL_Recycling_ConcreteFurnace = (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_ORC_EOL_ConcreteFurnace) - (RecycledContentConcrete * CHP_ORC_EOL_ConcreteFurnace)
    # The concrete is in [kg]; the primary concrete dataset is sold in [m3].
    CHP_ORC_EOL_Primary_ConcreteFurnace = (((RecycledContentConcrete * CHP_ORC_EOL_ConcreteFurnace) - (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_ORC_EOL_ConcreteFurnace))* SRinert) / config.CONCRETE_DENSITY

    CHP_ORC_EOL_Recycling_CopperFurnace = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_CopperFurnace) - (RecycledContentMetals * CHP_ORC_EOL_CopperFurnace)
    CHP_ORC_EOL_Primary_CopperFurnace = ((RecycledContentMetals * CHP_ORC_EOL_CopperFurnace) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_CopperFurnace))* SRmetals

    CHP_ORC_EOL_Recycling_DrawingpipesteelFurnace = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_DrawingpipeFurnace) - (RecycledContentMetals * CHP_ORC_EOL_DrawingpipeFurnace)
    CHP_ORC_EOL_Primary_DrawingpipesteelFurnace = ((RecycledContentMetals * CHP_ORC_EOL_DrawingpipeFurnace) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_DrawingpipeFurnace))* SRmetals

    CHP_ORC_EOL_Recycling_IronickelchromiumsteelFurnace = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_IronnickelchromiumalloyFurnace) - (RecycledContentMetals * CHP_ORC_EOL_IronnickelchromiumalloyFurnace)
    CHP_ORC_EOL_Primary_IronickelchromiumsteelFurnace = ((RecycledContentMetals * CHP_ORC_EOL_IronnickelchromiumalloyFurnace) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_IronnickelchromiumalloyFurnace))* SRmetals

    CHP_ORC_EOL_Recycling_HDPEFurnace = (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_ORC_EOL_HDPEFurnace) - (RecycledContentPlastic * CHP_ORC_EOL_HDPEFurnace)
    CHP_ORC_EOL_Primary_HDPEFurnace = ((RecycledContentPlastic * CHP_ORC_EOL_HDPEFurnace) - (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_ORC_EOL_HDPEFurnace))* SRinert

    CHP_ORC_EOL_Recycling_ClaybrickFurnace = (RecyclingClaybrick * RecyclingEfficiencyClaybrick * CHP_ORC_EOL_ClaybrickFurnace) - (RecycledContentClaybrick * CHP_ORC_EOL_ClaybrickFurnace)
    CHP_ORC_EOL_Primary_ClaybrickFurnace = ((RecycledContentClaybrick * CHP_ORC_EOL_ClaybrickFurnace) - (RecyclingClaybrick * RecyclingEfficiencyClaybrick * CHP_ORC_EOL_ClaybrickFurnace))* SRclaybrick

    CHP_ORC_EOL_Recycling_SheetrollingsteelFurnace = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_SheetrollingsteelFurnace) - (RecycledContentMetals * CHP_ORC_EOL_SheetrollingsteelFurnace)
    CHP_ORC_EOL_Primary_SheetrollingsteelFurnace = ((RecycledContentMetals * CHP_ORC_EOL_SheetrollingsteelFurnace) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_SheetrollingsteelFurnace))* SRmetals

    CHP_ORC_EOL_Recycling_ChromiumsteelFurnace = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_ChromiumsteelFurnace) - (RecycledContentMetals * CHP_ORC_EOL_ChromiumsteelFurnace)
    CHP_ORC_EOL_Primary_ChromiumsteelFurnace = ((RecycledContentMetals * CHP_ORC_EOL_ChromiumsteelFurnace) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_ChromiumsteelFurnace))* SRmetals

    CHP_ORC_EOL_Recycling_LowalloyedsteelFurnace = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_LowalloyedsteelFurnace) - (RecycledContentMetals * CHP_ORC_EOL_LowalloyedsteelFurnace)
    CHP_ORC_EOL_Primary_LowalloyedsteelFurnace = ((RecycledContentMetals * CHP_ORC_EOL_LowalloyedsteelFurnace) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_LowalloyedsteelFurnace))* SRmetals

    CHP_ORC_EOL_Recycling_CopperCHP = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_CopperCHP) - (RecycledContentMetals * CHP_ORC_EOL_CopperCHP)
    CHP_ORC_EOL_Primary_CopperCHP = ((RecycledContentMetals * CHP_ORC_EOL_CopperCHP) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_CopperCHP))* SRmetals

    CHP_ORC_EOL_Recycling_HDPECHP = (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_ORC_EOL_HDPECHP) - (RecycledContentPlastic * CHP_ORC_EOL_HDPECHP)
    CHP_ORC_EOL_Primary_HDPECHP = ((RecycledContentPlastic * CHP_ORC_EOL_HDPECHP) - (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_ORC_EOL_HDPECHP))* SRinert

    CHP_ORC_EOL_Recycling_ChromiumsteelCHP = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_ChromiumsteelCHP) - (RecycledContentMetals * CHP_ORC_EOL_ChromiumsteelCHP)
    CHP_ORC_EOL_Primary_ChromiumsteelCHP = ((RecycledContentMetals * CHP_ORC_EOL_ChromiumsteelCHP) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_ORC_EOL_ChromiumsteelCHP))* SRmetals

    CHP_ORC_EOL_Recycling_LowalloyedsteelCHP = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_LowalloyedsteelCHP) - (RecycledContentMetals * CHP_ORC_EOL_LowalloyedsteelCHP)
    CHP_ORC_EOL_Primary_LowalloyedsteelCHP = ((RecycledContentMetals * CHP_ORC_EOL_LowalloyedsteelCHP) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_ORC_EOL_LowalloyedsteelCHP))* SRmetals

    # --- Module D3: energy recovered from incineration -------------------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    CHP_ORC_EOL_EnergyRecoveryHeat_ElectronicsDustcollector = - CHP_ORC_EOL_Inc_ElectronicsDustcollector * LHVElectronics * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_ElectronicsDustcollector = - CHP_ORC_EOL_Inc_ElectronicsDustcollector * LHVElectronics * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_HDPEDustcollector = - CHP_ORC_EOL_Inc_HDPEDustcollector * LHVHDPE * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_HDPEDustcollector = - CHP_ORC_EOL_Inc_HDPEDustcollector * LHVHDPE * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_AlkydpaintFurnace = - CHP_ORC_EOL_Inc_AlkydpaintFurnace * LHVHazardous * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_AlkydpaintFurnace = - CHP_ORC_EOL_Inc_AlkydpaintFurnace * LHVHazardous * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_ElectronicsFurnace = - CHP_ORC_EOL_Inc_ElectronicsFurnace * LHVElectronics * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_ElectronicsFurnace = - CHP_ORC_EOL_Inc_ElectronicsFurnace * LHVElectronics * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_LubricatingoilFurnace = - CHP_ORC_EOL_Inc_LubricatingoilFurnace * LHVHazardous  * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_LubricatingoilFurnace = - CHP_ORC_EOL_Inc_LubricatingoilFurnace * LHVHazardous  * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_HDPEFurnace = - CHP_ORC_EOL_Inc_HDPEFurnace * LHVHDPE * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_HDPEFurnace = - CHP_ORC_EOL_Inc_HDPEFurnace * LHVHDPE * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_PolystyreneFurnace = - CHP_ORC_EOL_Inc_PolystyreneFurnace * LHVEPS * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_PolystyreneFurnace = - CHP_ORC_EOL_Inc_PolystyreneFurnace * LHVEPS * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_Electronics = - CHP_ORC_EOL_Inc_ElectronicsCHP * LHVElectronics * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_Electronics = - CHP_ORC_EOL_Inc_ElectronicsCHP * LHVElectronics * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_PerfluoropentaneCHP = - CHP_ORC_EOL_Inc_PerfluoropentaneCHP * LHVHazardous  * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_PerfluoropentaneCHP = - CHP_ORC_EOL_Inc_PerfluoropentaneCHP * LHVHazardous  * Xincele / config.MJ_PER_KWH

    CHP_ORC_EOL_EnergyRecoveryHeat_HDPECHP = - CHP_ORC_EOL_Inc_HDPECHP * LHVHDPE * Xincheat
    CHP_ORC_EOL_EnergyRecoveryEle_HDPECHP = - CHP_ORC_EOL_Inc_HDPECHP * LHVHDPE * Xincele / config.MJ_PER_KWH

    # Data for export (informative only: the fuel input; see energy_systems/__init__.py).
    ThermalEnergyProduced_ORC = TotEnergyNeeds

    # Collect every 'CHP_ORC_' quantity for the exchange rows. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("CHP_ORC_")}

    return {
        "activity_data": activity_data,
        "sf": SFORC,
        "replacements": ORCNumberReplacements,
        "bd_names": CHP_ORC_BdName,
        "bd_areas": CHP_ORC_BdArea,
        "thermal_energy": ThermalEnergyProduced_ORC,
    }
