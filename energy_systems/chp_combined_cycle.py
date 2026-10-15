# Derived from LCA4DHC (Energy_systems/CombinedHeatPower_CombinedCycle.ipynb) -
# Copyright 2026 Kevin Autelitano and Jacopo Famiglietti, licensed under the
# Apache License 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
chp_combined_cycle.py - life-cycle inventory of a combined-cycle CHP plant.

A gas turbine with a steam bottoming cycle, producing heat and power and
burning a gas blend, biogas or hydrogen. Every quantity is multiplied by
AFQ_CombinedCycle, the share of the burden allocated to HEAT (the electricity
leaves the system boundary). Unlike chp_turbogas.py, the default allocation is
the power-loss method. The building label columns are CHP_CombCycle_*, the
inventory quantities CHP_CombinedCycle_*. See energy_systems/__init__.py for
the conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the plants.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'CHP-Combined Cycle'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("CHP-Combined Cycle")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillClaybrick = eol["LandfillClaybrick"]    # share of clay bricks landfilled
    LandfillConcrete = eol["LandfillConcrete"]      # share of concrete landfilled
    LandfillMetals = eol["LandfillMetals"]          # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    LandfillMineralWool = eol["LandfillMineralWool"]
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
    # 'Multifunctionality Approach' selects the allocation method; the supply
    # and return temperatures are only used to detect rows without them; the
    # three EnergyInputSource columns [kWh/year] are used only as fuel shares.
    CHP_CombCycle_BdName = energysystem['Building Name']
    CHP_CombCycle_BdArea = energysystem['Zone net floor area [m2]']
    Multifunctionality = energysystem['Multifunctionality Approach']
    Power = energysystem['Thermal capacity [kW]']
    EfficiencyW = energysystem['Electrical efficiency based on LHV (between 0 and 1)']
    EfficiencyQ = energysystem['Heat efficiency based on LHV (between 0 and 1)']
    ElectricEnergyproduced = energysystem['Electric energy produced in a year (exported and consumed) [kWh /year]']
    ThermalEnergyproduced_primary = energysystem['Thermal energy produced used [kWh /year]']
    Qused = 1
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
    Power = np.array(Power)
    Lifespan = np.array(Lifespan)
    EfficiencyW = np.array(EfficiencyW)
    EfficiencyQ = np.array(EfficiencyQ)
    EnergyProducedLHV = (Power * EquivalentHours * RSP) / EfficiencyW
    EnergyProducedHHV = EnergyProducedLHV * (HHV/LHV)
    TotW = EnergyProducedLHV * EfficiencyW
    TotQ = EnergyProducedLHV * EfficiencyQ * Qused

    # Earlier whole-column if/else version of the allocation below, kept for
    # reference; the live version applies the same arithmetic per building.
    # # MULTIFUNCTIONALITY AND ALLOCATION OF output
    # ElectricEnergyproduced = (EnergyProducedHHV / EfficiencyQ) * EfficiencyW #mode cogen
    # InletEnergyCogenmode = (ElectricEnergyproduced) / EfficiencyW
    # DeltaElProduced = InletEnergyCogenmode * 0.55 - ElectricEnergyproduced #from BREF EU
    # if Multifunctionality == 'Default': #Power loss method
    #     ThermalEnergyproduced = EnergyProducedHHV
    #     ElectricEnergyproduced = (EnergyProducedHHV / EfficiencyQ) * EfficiencyW
    #     # AFQ calculation
    #     AFQ = DeltaElProduced / (ElectricEnergyproduced + DeltaElProduced)
    #     AFQ_CombinedCycle = np.array(AFQ)
    #     # AFW calculation
    #     AFW_CombinedCycle = (1 - AFQ_CombinedCycle)


    # else: #Energy carrier is the natural gas
    #     InletEnergyCogenmode = EnergyProducedHHV / EfficiencyQ
    #     fwecr = 0.7 #weighting factor from energy carrier. EN 15316: 2017 - table B2 pag. 24
    #     fweexp = fwecr

    #     AFQ = (InletEnergyCogenmode * fwecr - (ElectricEnergyproduced *fweexp)) / EnergyProducedHHV
    #     AFW = (1 - AFQ)
    #     AFQ_CombinedCycle = np.array(AFQ)
    #     AFW_CombinedCycle = np.array(AFW)

    # if SupplyTemperature.eq(0).all() and ReturnTemperature.eq(0).all():
    #     AFQ_CombinedCycle = np.zeros_like(AFQ_CombinedCycle)
    #     AFW_CombinedCycle = np.zeros_like(AFW_CombinedCycle)

    # --- Multifunctionality: splitting the burden between heat and power -------
    # AFQ is the share charged to HEAT, AFW to POWER. Two methods, per building:
    #
    #   'Default' - power-loss method: heat carries the electricity lost by
    #               running in cogeneration mode instead of at the 0.55
    #               electrical efficiency of a condensing plant (BREF EU).
    #   otherwise - EN 15316:2017 primary-energy weighting, fwecr = 0.7 for the
    #               electricity carrier (table B2, p. 24).
    #
    # Both branches use the cogeneration-mode ElectricEnergyproduced. Rows with
    # no temperatures get no allocation.
    # Note: with the default method AFQ_CombinedCycle can come out negative
    # (it does on the test workbook), which inverts the sign of every quantity
    # in this file. Open question to the inventory authors.
    # MULTIFUNCTIONALITY AND ALLOCATION OF output
    # Calculations for 'Else' condition (computed first to preserve original ElectricEnergyproduced)
    ElectricEnergyproduced = (EnergyProducedHHV / EfficiencyQ) * EfficiencyW #mode cogen
    InletEnergyCogenmode_else = EnergyProducedHHV / EfficiencyQ
    fwecr = 0.7 #weighting factor from energy carrier. EN 15316: 2017 - table B2 pag. 24
    fweexp = fwecr
    AFQ_CombinedCycle_else = (InletEnergyCogenmode_else * fwecr - (ElectricEnergyproduced * fweexp)) / EnergyProducedHHV
    AFW_CombinedCycle_else = 1 - AFQ_CombinedCycle_else

    # Calculations for 'Default' condition
    InletEnergyCogenmode_default = ElectricEnergyproduced / EfficiencyW
    DeltaElProduced = InletEnergyCogenmode_default * 0.55 - ElectricEnergyproduced #from BREF EU
    ThermalEnergyproduced = EnergyProducedHHV

    # AFQ calculation
    AFQ_CombinedCycle_default = DeltaElProduced / (ElectricEnergyproduced + DeltaElProduced)
    AFQ_CombinedCycle_default = np.array(AFQ_CombinedCycle_default)

    # AFW calculation
    AFW_CombinedCycle_default = (1 - AFQ_CombinedCycle_default)

    # Apply conditions row by row
    AFQ_CombinedCycle = np.where(Multifunctionality == 'Default', AFQ_CombinedCycle_default, AFQ_CombinedCycle_else)
    AFW_CombinedCycle = np.where(Multifunctionality == 'Default', AFW_CombinedCycle_default, AFW_CombinedCycle_else)

    # Handle zero temperatures row by row
    zero_mask = (SupplyTemperature == 0) & (ReturnTemperature == 0)
    AFQ_CombinedCycle = np.where(zero_mask, 0, AFQ_CombinedCycle)
    AFW_CombinedCycle = np.where(zero_mask, 0, AFW_CombinedCycle)

    # Unit mass [kg], scaled linearly from a 430 MW electrical reference plant
    # of 2.79e7 kg.
    PowerEle = (Power / EfficiencyQ) * EfficiencyW
    RefPowerEle = 430000 #kW
    RefMass = 2.79E+07
    mass = PowerEle * (RefMass / RefPowerEle)

    # --- Module A1-3: manufacture ---------------------------------------------
    # Material and construction demand, allocated to heat. Material rows are
    # fractions of unit mass [kg]; the concretes [m3] and the energy rows
    # (diesel and heat [MJ], electricity [kWh]) scale on the reference plant's
    # capacity ratio.
    CHP_CombinedCycle_AluminiumCastalloy = 0.0105 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_AluminiumWroughtalloy = 0.0222 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_Ceramictile = 0.00003 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_ChromiumInSteel = 0.00007 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_CobaltInSteel = 0.00005 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_ConcreteAT = 2127 * (PowerEle / RefPowerEle) * AFQ_CombinedCycle
    CHP_CombinedCycle_ConcreteCH = 3872 * (PowerEle / RefPowerEle) * AFQ_CombinedCycle
    CHP_CombinedCycle_Copper = 0.0327 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_Diesel = 3441860 * (PowerEle / RefPowerEle) * AFQ_CombinedCycle
    CHP_CombinedCycle_ElectricityA13 = 3020000 * (PowerEle / RefPowerEle) * AFQ_CombinedCycle
    CHP_CombinedCycle_Heat = 140600000 * (PowerEle / RefPowerEle) * AFQ_CombinedCycle
    CHP_CombinedCycle_NickelInSteel = 0.0047 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_PEHD = 0.031 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_ReinforcingSteel = 0.6542 * mass * AFQ_CombinedCycle
    CHP_CombinedCycle_ChromiumSteel = 0.0645 * mass * AFQ_CombinedCycle
    # Note: stone wool is zero by construction, yet its A1-3, C3 and C4 rows
    # are wired; open question to the inventory authors.
    CHP_CombinedCycle_StoneWool = 0.0 * mass * AFQ_CombinedCycle

    # --- Module A4: transport to site -----------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    CHP_CombinedCycle_Truck1632 = (((500 + 200)*(mass)/1000)) * AFQ_CombinedCycle
    CHP_CombinedCycle_Light_Truck = ((50*(mass)/1000)) * AFQ_CombinedCycle

    # --- Module B2: maintenance transport -------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the unit mass.
    CHP_CombinedCycle_LightTruck_B2 = ((50 * (Lifespan/2) * 0.01 * (mass/1000))) * AFQ_CombinedCycle

    # --- Module B4: replacement within the study period ------------------------
    CombinedCycleNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFCombinedCycle = (RSP / Lifespan)  # Scaling factor

    # Shares of the fuel input, from the three [kWh/year] columns.
    #Repartition parameters for energy source input
    GasBlend = EnergyInputSourceGasBlend / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)
    Biogas = EnergyInputSourceBiogas / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)
    Hydrogen = EnergyInputSourceHydrogen / (EnergyInputSourceGasBlend + EnergyInputSourceBiogas + EnergyInputSourceHydrogen)

    # --- Module B6: fuel and combustion emissions over the lifetime ------------
    # y is the fuel input over the study period [MJ], allocated to heat; x = 1
    # (no year-by-year blend split). Natural gas, biomethane and biogas in [m3]
    # (1 / HHV), hydrogen in [kWh] of photovoltaic electrolysis electricity
    # (120 MJ/kg / 3.6 / 0.9). WaterCooling, WaterIn and WaterOut are
    # technosphere [kg]; the emissions, WaterAir and WaterWater are biosphere.
    x = 1
    TotEnergyNeeds = np.array([EnergyProducedHHV])
    TotEnergyNeeds = TotEnergyNeeds.flatten()
    y = (TotEnergyNeeds * 3.6).flatten() * AFQ_CombinedCycle

    # Gas-blend composition: A natural gas, B biomethane, C hydrogen
    # (config.GAS_BLEND).
    A, B, C = config.GAS_BLEND

    # The 0.95 and 0.042 are factors from the reference inventory, separate
    # from the blend shares A and B.
    CHP_CombinedCycle_EnergyVectorNG = (((1 / (HHV)) * 0.95) * A) * x * y * GasBlend
    CHP_CombinedCycle_EnergyVectorBiomethane = (((1 / (HHV)) * 0.042) * B) * x * y * GasBlend
    CHP_CombinedCycle_EnergyVectorHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * C * GasBlend #120 MJ/kg
    CHP_CombinedCycle_EnergyVectorInputBiogas = ((1 / (HHV))) * x * y * Biogas
    CHP_CombinedCycle_EnergyVectorInputHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * x * y) * Hydrogen #120 MJ/kg
    CHP_CombinedCycle_WaterCooling = (0.00662935643564359 * x * y).flatten()
    CHP_CombinedCycle_WaterIn2 = (0.00579207920792081 * x * y).flatten()
    CHP_CombinedCycle_WaterIn3 = (0.193069306930693 * x * y).flatten()
    CHP_CombinedCycle_WaterOut4 = (9.65346534653468E-07 * x * y).flatten()
    CHP_CombinedCycle_Acenaphthene = (0.000000000000765520 * x * y).flatten()
    CHP_CombinedCycle_Acetaldehyde = (7.72277227722775E-10 * x * y).flatten()
    CHP_CombinedCycle_AceticAcid = (1.1680693069307E-07 * x * y).flatten()
    CHP_CombinedCycle_Arsenic = (3.96757425742575E-11 * x * y).flatten()
    CHP_CombinedCycle_Benzene = (8.70742574257428E-10 * x * y).flatten()
    CHP_CombinedCycle_Benzoapyrene = (5.10668316831685E-13 * x * y).flatten()
    CHP_CombinedCycle_Beryllium = (2.38440594059407E-12 * x * y).flatten()
    CHP_CombinedCycle_Butane = (8.93910891089111E-07 * x * y).flatten()
    CHP_CombinedCycle_Cadmium = (2.18168316831684E-10 * x * y).flatten()
    CHP_CombinedCycle_CarbonDioxideFossil = (0.0515495049504952 * x * y).flatten()
    CHP_CombinedCycle_CarbonMonoxideFossil = (2.12376237623763E-06 * x * y).flatten()
    CHP_CombinedCycle_ChromiumVIEmission = (2.77054455445546E-10 * x * y).flatten()
    CHP_CombinedCycle_CobaltEmission = (1.66039603960396E-11 * x * y).flatten()
    CHP_CombinedCycle_DinitrogenMonoxide = (9.43143564356438E-07 * x * y).flatten()
    CHP_CombinedCycle_Ethane = (1.32252475247525E-06 * x * y).flatten()
    CHP_CombinedCycle_Formaldehyde = (3.1180693069307E-08 * x * y).flatten()
    CHP_CombinedCycle_Hexane = (0.0000007655198019802 * x * y).flatten()
    CHP_CombinedCycle_Lead = (9.94306930693072E-11 * x * y).flatten()
    CHP_CombinedCycle_Manganese = (7.53935643564359E-11 * x * y).flatten()
    CHP_CombinedCycle_Mercury = (6.64158415841586E-11 * x * y).flatten()
    CHP_CombinedCycle_MethaneFossil = (9.37351485148517E-07 * x * y).flatten()
    CHP_CombinedCycle_NickelEmission = (4.16064356435644E-10 * x * y).flatten()
    CHP_CombinedCycle_NitrogenOxides = (0.0000246163366336634 * x * y).flatten()
    CHP_CombinedCycle_PAH = (7.72277227722775E-09 * x * y).flatten()
    CHP_CombinedCycle_Particulates = (4.73985148514853E-07 * x * y).flatten()
    CHP_CombinedCycle_Pentane = (1.11014851485149E-06 * x * y).flatten()
    CHP_CombinedCycle_Propane = (6.80569306930695E-07 * x * y).flatten()
    CHP_CombinedCycle_PropionicAcid = (1.54455445544554E-08 * x * y).flatten()
    CHP_CombinedCycle_Selenium = (4.73985148514853E-12 * x * y).flatten()
    CHP_CombinedCycle_SulfurDioxide = (5.52178217821784E-07 * x * y).flatten()
    CHP_CombinedCycle_Toluene = (1.4480198019802E-09 * x * y).flatten()
    CHP_CombinedCycle_WaterAir = (0.0000813864357863667 * x * y).flatten()
    CHP_CombinedCycle_WaterWater = (0.00674683138599583 * x * y).flatten()

    # --- Module C2: transport to the treatment plant ---------------------------
    # 50 km [t.km].
    CHP_CombinedCycle_Transport_To_Treatment_Plant = (50 * (mass/1000)) * AFQ_CombinedCycle

    # --- Module C3: waste processing ------------------------------------------
    CHP_CombinedCycle_EOL_AluminiumCastalloy = CHP_CombinedCycle_AluminiumCastalloy
    CHP_CombinedCycle_EOL_AluminiumWroughtalloy = CHP_CombinedCycle_AluminiumWroughtalloy
    CHP_CombinedCycle_EOL_Ceramictile = CHP_CombinedCycle_Ceramictile
    CHP_CombinedCycle_EOL_Chromium = CHP_CombinedCycle_ChromiumInSteel
    CHP_CombinedCycle_EOL_Cobalt = CHP_CombinedCycle_CobaltInSteel
    # Concrete volumes [m3] converted to the [kg] the end-of-life datasets use.
    CHP_CombinedCycle_EOL_ConcreteAT = CHP_CombinedCycle_ConcreteAT * config.CONCRETE_DENSITY
    CHP_CombinedCycle_EOL_ConcreteCH = CHP_CombinedCycle_ConcreteCH * config.CONCRETE_DENSITY
    CHP_CombinedCycle_EOL_Copper = CHP_CombinedCycle_Copper
    CHP_CombinedCycle_EOL_Nickel = CHP_CombinedCycle_NickelInSteel
    CHP_CombinedCycle_EOL_PEHD = CHP_CombinedCycle_PEHD
    CHP_CombinedCycle_EOL_ReinforcingSteel = CHP_CombinedCycle_ReinforcingSteel
    CHP_CombinedCycle_EOL_ChromiumSteel = CHP_CombinedCycle_ChromiumSteel
    CHP_CombinedCycle_EOL_StoneWool = CHP_CombinedCycle_StoneWool

    # --- Module C4: disposal ---------------------------------------------------
    # The landfilled and incinerated shares of each material [kg].
    # Note: the first two lines assign the same name, so only the wrought
    # aluminium is landfilled and the cast alloy never is. Open question to
    # the inventory authors.
    CHP_CombinedCycle_EOL_Landfill_Aluminium = CHP_CombinedCycle_EOL_AluminiumCastalloy * LandfillMetals
    CHP_CombinedCycle_EOL_Landfill_Aluminium = CHP_CombinedCycle_EOL_AluminiumWroughtalloy * LandfillMetals
    CHP_CombinedCycle_EOL_Landfill_Ceramictile = CHP_CombinedCycle_EOL_Ceramictile * LandfillClaybrick
    CHP_CombinedCycle_EOL_Landfill_Chromium = CHP_CombinedCycle_EOL_Chromium * LandfillMetals2
    CHP_CombinedCycle_EOL_Landfill_Cobalt = CHP_CombinedCycle_EOL_Cobalt * LandfillMetals2
    CHP_CombinedCycle_EOL_Landfill_ConcreteAT = CHP_CombinedCycle_EOL_ConcreteAT * LandfillConcrete
    CHP_CombinedCycle_EOL_Landfill_ConcreteCH = CHP_CombinedCycle_EOL_ConcreteCH * LandfillConcrete
    CHP_CombinedCycle_EOL_Landfill_Copper = CHP_CombinedCycle_EOL_Copper * LandfillMetals
    CHP_CombinedCycle_EOL_Landfill_Nickel = CHP_CombinedCycle_EOL_Nickel * LandfillMetals2
    CHP_CombinedCycle_EOL_Inc_PEHD = CHP_CombinedCycle_EOL_PEHD * IncinerationPEHD
    CHP_CombinedCycle_EOL_Landfill_PEHD = CHP_CombinedCycle_EOL_PEHD * LandfillPEHD
    CHP_CombinedCycle_EOL_Landfill_ReinforcingSteel = CHP_CombinedCycle_EOL_ReinforcingSteel * LandfillMetals
    CHP_CombinedCycle_EOL_Landfill_ChromiumSteel = CHP_CombinedCycle_EOL_ChromiumSteel * LandfillMetals2
    CHP_CombinedCycle_EOL_Landfill_StoneWool = CHP_CombinedCycle_EOL_StoneWool * LandfillMineralWool

    # --- Module D1: recycling credits and primary-production burdens ------------
    # The HDPE primary line carries an extra RecyclingEfficiencyPlastics factor
    # on the recycled-content term, unlike every other primary line; kept as in
    # the source inventory.
    CHP_CombinedCycle_EOL_Recycling_AluminiumCastalloy = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_AluminiumCastalloy) - (RecycledContentMetals * CHP_CombinedCycle_EOL_AluminiumCastalloy)
    CHP_CombinedCycle_EOL_Primary_AluminiumCastalloy = ((RecycledContentMetals * CHP_CombinedCycle_EOL_AluminiumCastalloy)
                                                    - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_AluminiumCastalloy)) * SRmetals

    CHP_CombinedCycle_EOL_Recycling_AluminiumWroughtalloy = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_AluminiumWroughtalloy) - (RecycledContentMetals * CHP_CombinedCycle_EOL_AluminiumWroughtalloy)
    CHP_CombinedCycle_EOL_Primary_AluminiumWroughtalloy = ((RecycledContentMetals * CHP_CombinedCycle_EOL_AluminiumWroughtalloy) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_AluminiumWroughtalloy)) * SRmetals

    # Chromium, chromium steel, cobalt and nickel are special metals
    # (LandfillMetals2 / RecyclingMetals2).
    CHP_CombinedCycle_EOL_Recycling_Chromium = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_Chromium) - (RecycledContentMetals * CHP_CombinedCycle_EOL_Chromium)
    CHP_CombinedCycle_EOL_Primary_Chromium = ((RecycledContentMetals * CHP_CombinedCycle_EOL_Chromium) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_Chromium)) * SRmetals

    CHP_CombinedCycle_EOL_Recycling_Cobalt = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_Cobalt) - (RecycledContentMetals * CHP_CombinedCycle_EOL_Cobalt)
    CHP_CombinedCycle_EOL_Primary_Cobalt = ((RecycledContentMetals * CHP_CombinedCycle_EOL_Cobalt) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_Cobalt)) * SRmetals

    CHP_CombinedCycle_EOL_Recycling_ConcreteAT = (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_CombinedCycle_EOL_ConcreteAT) - (RecycledContentConcrete * CHP_CombinedCycle_EOL_ConcreteAT)
    # The primary concrete dataset is sold in [m3], so the credit is divided by
    # the density.
    CHP_CombinedCycle_EOL_Primary_ConcreteAT = (((RecycledContentConcrete * CHP_CombinedCycle_EOL_ConcreteAT) - (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_CombinedCycle_EOL_ConcreteAT)) * SRinert) / config.CONCRETE_DENSITY

    CHP_CombinedCycle_EOL_Recycling_ConcreteCH = (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_CombinedCycle_EOL_ConcreteCH) - (RecycledContentConcrete * CHP_CombinedCycle_EOL_ConcreteCH)
    CHP_CombinedCycle_EOL_Primary_ConcreteCH = (((RecycledContentConcrete * CHP_CombinedCycle_EOL_ConcreteCH) - (RecyclingConcrete * RecyclingEfficiencyConcrete * CHP_CombinedCycle_EOL_ConcreteCH)) * SRinert) / config.CONCRETE_DENSITY

    CHP_CombinedCycle_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_Copper) - (RecycledContentMetals * CHP_CombinedCycle_EOL_Copper)
    CHP_CombinedCycle_EOL_Primary_Copper = ((RecycledContentMetals * CHP_CombinedCycle_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_Copper)) * SRmetals

    CHP_CombinedCycle_EOL_Recycling_Nickel = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_Nickel) - (RecycledContentMetals * CHP_CombinedCycle_EOL_Nickel)
    CHP_CombinedCycle_EOL_Primary_Nickel = ((RecycledContentMetals * CHP_CombinedCycle_EOL_Nickel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_Nickel)) * SRmetals

    CHP_CombinedCycle_EOL_Recycling_HDPE = (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_CombinedCycle_EOL_PEHD) - (RecycledContentPlastic * CHP_CombinedCycle_EOL_PEHD)
    CHP_CombinedCycle_EOL_Primary_HDPE = ((RecycledContentPlastic * RecyclingEfficiencyPlastics * CHP_CombinedCycle_EOL_PEHD) - (RecyclingPEHD * RecyclingEfficiencyPlastics * CHP_CombinedCycle_EOL_PEHD)) * SRinert

    CHP_CombinedCycle_EOL_Recycling_ReinforcingSteel = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_ReinforcingSteel) - (RecycledContentMetals * CHP_CombinedCycle_EOL_ReinforcingSteel)
    CHP_CombinedCycle_EOL_Primary_ReinforcingSteel = ((RecycledContentMetals * CHP_CombinedCycle_EOL_ReinforcingSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_ReinforcingSteel)) * SRmetals

    CHP_CombinedCycle_EOL_Recycling_ChromiumSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_ChromiumSteel) - (RecycledContentMetals * CHP_CombinedCycle_EOL_ChromiumSteel)
    CHP_CombinedCycle_EOL_Primary_ChromiumSteel = ((RecycledContentMetals * CHP_CombinedCycle_EOL_ChromiumSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_CombinedCycle_EOL_ChromiumSteel)) * SRmetals

    # --- Module D3: energy recovered from incineration -------------------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    CHP_CombinedCycle_EOL_EnergyRecoveryHeat_PEHD = - CHP_CombinedCycle_EOL_Inc_PEHD * LHVHDPE * Xincheat
    CHP_CombinedCycle_EOL_EnergyRecoveryEle_PEHD = - CHP_CombinedCycle_EOL_Inc_PEHD * LHVHDPE * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_CombinedCycle = np.array(TotQ)

    # Collect every 'CHP_CombinedCycle_' quantity for the exchange rows.
    # locals() is bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("CHP_CombinedCycle_")}

    return {
        "activity_data": activity_data,
        "sf": SFCombinedCycle,
        "replacements": CombinedCycleNumberReplacements,
        "bd_names": CHP_CombCycle_BdName,
        "bd_areas": CHP_CombCycle_BdArea,
        "thermal_energy": ThermalEnergyProduced_CombinedCycle,
    }
