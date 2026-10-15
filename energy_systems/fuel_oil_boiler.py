# Derived from LCA4DHC (Energy_systems/FuelOilBoiler.ipynb) - Copyright 2026
# Kevin Autelitano and Jacopo Famiglietti, licensed under the Apache License
# 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
fuel_oil_boiler.py - life-cycle inventory of a fuel-oil boiler.

Same shape as boiler.py, but the unit comes with a storage tank and a chimney,
inventoried separately (the FuelOilBoiler_Tank_* and FuelOilBoiler_Chimney_*
quantities), and it burns one fuel. Heating values are per kilogram of oil.
See energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the boilers.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Fuel oil boiler' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Fuel oil boiler")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    LandfillClaybrick = eol["LandfillClaybrick"]
    LandfillMineralWool = eol["LandfillMineralWool"]
    LandfillBrass = eol["LandfillBrass"]
    LandfillConcrete = eol["LandfillConcrete"]
    LandfillPEHD = eol["LandfillPEHD"]
    LandfillElectronics = eol["LandfillElectronics"]
    IncinerationElectronics = eol["IncinerationElectronics"]
    IncinerationPEHD = eol["IncinerationPEHD"]
    RecyclingMetals = eol["RecyclingMetals"]
    RecyclingMetals2 = eol["RecyclingMetals2"]
    RecyclingConcrete = eol["RecyclingConcrete"]
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyConcrete = eol["RecyclingEfficiencyConcrete"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentConcrete = eol["RecycledContentConcrete"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    SRmetals = eol["SRmetals"]                      # substitution ratio, secondary vs primary
    SRinert = eol["SRinert"]                        # the same, for inert materials
    LHVElectronics = eol["LHVElectronics"]          # lower heating values [MJ/kg], for D3
    LHVHDPE = eol["LHVHDPE"]
    Xincheat = eol["Xincheat"]                      # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                        # electricity recovery efficiency

    # DASHBORD - VALUE INPUTS
    FuelOilBoiler_BdName = energysystem['Building Name']
    FuelOilBoiler_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Thermal capacity [kW]']
    Energy_produced = energysystem['Energy produced [kWh /year]']
    Efficiency = energysystem['Efficiency (between 0 and 1)']

    # DASHBOARD - INPUT PARAMETERS
    Efficiency_LHV = Efficiency

    # DEFAULT PARAMETERS
    LHV = 43.2  # Tabella 3.1 rapporto 06_V_Oil 3 Characterist of the products MJ/kg
    HHV = 45.8  # Tabella 3.1 rapporto 06_V_Oil 3 Characterist of the products MJ/kg
    Efficiency_HHV = Efficiency_LHV*(LHV/HHV)  # Efficiency based on HHV
    TotEnergyNeeds = np.array([Energy_produced])  # Energy need for 1 year kWh per year

    # Define Lifespan
    Lifespan = 28 #years
    # Unit mass [kg] from thermal capacity [kW], quadratic fit.
    # Note: Milestone-3 p.28 sizes appliances above 1 MW with a different
    # equation (m = a * P**b); one quadratic is used at all sizes here. Open
    # question to the inventory authors.
    mass = 0.0001 * (Power)**2 + 4.7974 * Power + 91.539

    # --- Module A1-3: product stage - boiler, storage tank and chimney --------
    # Three size brackets, applied per building (Milestone-3 p.28): 10-100 kW,
    # 100-1000 kW, and above 1000 kW.
    P = Power.to_numpy(dtype=float)          # thermal capacity per building [kW]
    brackets = [P <= 100,                    # 10-100 kW    (Milestone-3 p.28)
                (P > 100) & (P <= 1000)]     # 100-1000 kW
    # anything above 1000 kW falls through to the third set of figures

    def _bracket(small, medium, large):
        """One value per building, picked by that building's size bracket."""
        return np.select(brackets, [small, medium], default=large)

    # Material split as a fraction of unit mass [-]   <=100   <=1000    >1000
    FuelOilBoiler_SteelLowAlloyed = _bracket(0.82,   0.85,    0.04 ) * mass
    FuelOilBoiler_StainlessSteel  = _bracket(0.04,   0.04,    0.05 ) * mass
    FuelOilBoiler_CastIron        = _bracket(0.0,    0.0,     0.84 ) * mass
    FuelOilBoiler_Chamotte        = _bracket(0.0,    0.0,     0.01 ) * mass
    FuelOilBoiler_Aluminium       = _bracket(0.05,   0.03,    0.01 ) * mass
    FuelOilBoiler_MineralWool     = _bracket(0.06,   0.03,    0.01 ) * mass
    FuelOilBoiler_CopperA13       = _bracket(0.02,   0.04,    0.0  ) * mass
    FuelOilBoiler_Electronics     = _bracket(0.01,   0.0,     0.0  ) * mass
    # Above 1 MW the unit is mostly cast iron rather than sheet steel.

    # Storage tank, fixed per size class [kg], concrete in [m3]. The steel
    # figures are the 3,000 / 8,000 / 40,000 litre tanks of Milestone-3 p.28.
    FuelOilBoiler_Tank_Brass           = _bracket(1.4,   3.7,    18.7 )
    FuelOilBoiler_Tank_CastIron        = _bracket(6,     16,     80   )
    FuelOilBoiler_Tank_Concrete        = _bracket(0.2,   0.6,    3.0  )
    FuelOilBoiler_Tank_CopperA13       = _bracket(20.1,  53.6,   268.0)
    FuelOilBoiler_Tank_PEHD            = _bracket(0.6,   1.5,    7.3  )
    FuelOilBoiler_Tank_SteelLowAlloyed = _bracket(452,   1205,   6026 )

    # Chimney: kg/m of flue over 8 m, divided by the concrete density
    # (2400 kg/m3) to give [m3].
    FuelOilBoiler_Chimney_Concrete = _bracket(95 * 8 / 2400,
                                              135 * 8 / 2400,
                                              135 * 8 / 2400)
    FuelOilBoiler_Chimney_StoneWool = np.full(len(Power), 0.5)   # all brackets

    # Manufacturing consumables [kg], from the LCI formulas in absolute
    # kilograms (LCI_Executive Summary.xlsx, 'Oil boiler' sheets, rows 19, 20
    # and 24).
    FuelOilBoiler_Welding          = 0.0222 * Power + 3.7778   # LCI row 19 [kg]
    FuelOilBoiler_WaterConsumption = 6.0608 * Power + 127.83   # LCI row 20 [kg]
    FuelOilBoiler_HazardousWaste   = 0.0011 * Power + 0.1889   # LCI row 24 [kg]

    # Functions of unit mass, identical in all brackets (LCI rows 21-23).
    FuelOilBoiler_ElectricityA13      = 0.59 * mass  # kwh
    FuelOilBoiler_Heatfromnaturalgas  = 1.78 * mass  # MJ
    FuelOilBoiler_Heatfromoil         = 3.37 * mass

    # Water lost to air and water, and wastewater treated, in [m3] (/1000).
    # Note: the LCI gives 15% / 2% / 83% for every size; the second and third
    # brackets here use different figures. Open question.
    FuelOilBoiler_Watertoair   = _bracket(0.15, 0.11, 0.92) * (FuelOilBoiler_WaterConsumption/1000)
    FuelOilBoiler_Watertowater = _bracket(0.02, 0.02, 0.12) * (FuelOilBoiler_WaterConsumption/1000)
    FuelOilBoiler_Wasterwater  = _bracket(0.83, 0.74, 6.18) * (FuelOilBoiler_WaterConsumption/1000)

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    FuelOilBoiler_Truck1632 = ((500 + 200)*(mass)/1000)
    FuelOilBoiler_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the unit mass.
    FuelOilBoiler_Light_Truck_B2 = 50 * (Lifespan/2) * 0.01 * (mass/1000)

    # --- Module B4: replacement within the study period -------------------------
    FueloilboilerNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFFueloilboiler = (RSP / Lifespan)  # Scaling factor

    # --- Module B6: operational energy over the study period --------------------
    TotEnergyNeeds = TotEnergyNeeds.flatten()
    # Heat delivered over the study period [MJ]: kWh/year x 3.6 MJ/kWh x RSP.
    y = (TotEnergyNeeds * 3.6 * RSP).flatten()
    # Fuel burned per unit of heat delivered [kg oil / MJ].
    x = 1 / (Efficiency_HHV * HHV)
    # Grid / PV split of the auxiliary electricity. Placeholder values: all
    # auxiliary electricity is currently charged to the grid; the PV row is
    # kept wired for a future split.
    Grid = 1 #temporary
    PV = 0   #temporary
    FuelOilBoiler_ElectricityB6 = 0.000875 * x * y * Grid
    FuelOilBoiler_ElectricityB6PV = 0.000875 * x * y * PV
    # FuelOilBoiler_electricityB6RECSPV = FuelOilBoiler_ElectricityB6 * 0.0056 * RECSPV
    # FuelOilBoiler_electricityB6RECSHydro = FuelOilBoiler_ElectricityB6 * 0.0056 * RECSHydro
    # FuelOilBoiler_electricityB6RECSEolic = FuelOilBoiler_ElectricityB6 * 0.0056 * RECSEolic
    # The oil itself [MJ]: its dataset is sold per megajoule.
    FuelOilBoiler_EnergyVector = (1 / (Efficiency_HHV)) * y
    # Combustion emissions, per kg of oil burned.
    FuelOilBoiler_Acetaldehyde =  1.91117956137963E-08 * x * y
    FuelOilBoiler_Acetone = 4.66141356434057E-08* x * y
    FuelOilBoiler_Acrolein = 1.07212511979833E-08* x * y
    FuelOilBoiler_Benzaldehyde = 5.59369627720868E-09* x * y
    FuelOilBoiler_Benzene = 1.86456542573623E-08* x * y
    FuelOilBoiler_Butane = 1.39842406930217E-07* x * y
    FuelOilBoiler_CarbonDioxide_Fossil = 0.0689889207522405* x * y
    FuelOilBoiler_CarbonMonoxide_Fossil = 6.99212034651086E-06* x * y
    FuelOilBoiler_CopperB6 = 6.5259789900768E-10* x * y
    FuelOilBoiler_DinitrogenMonoxide = 6.5259789900768E-07* x * y
    FuelOilBoiler_Ethane = 1.86456542573623E-08* x * y
    FuelOilBoiler_ethyne = 9.32282712868113E-09* x * y
    FuelOilBoiler_Formaldehyde = 5.59369627720868E-09* x * y
    FuelOilBoiler_Hydrocarbons_Alkanes = 2.33070678217029E-07* x * y
    FuelOilBoiler_Hydrocarbons_Unsatured = 1.86456542573623E-08* x * y
    FuelOilBoiler_Hydrocarbons_Aromatic = 1.86456542573623E-08* x * y
    FuelOilBoiler_HydrogenChloride = 8.76345750096028E-08* x * y
    FuelOilBoiler_HydrogenFluoride = 8.39054441581303E-09* x * y
    FuelOilBoiler_Mercury = 4.66141356434057E-10* x * y
    FuelOilBoiler_Methanefossil = 1.86456542573623E-07* x * y
    FuelOilBoiler_Nitrogenoxyde = 0.0000256377746038732* x * y
    FuelOilBoiler_PAH = 4.28850047919332E-10* x * y
    FuelOilBoiler_Particulate_025 = 4.66141356434057E-07* x * y
    FuelOilBoiler_Pentane = 9.32282712868113E-08* x * y
    FuelOilBoiler_Propanal = 5.59369627720868E-09* x * y
    FuelOilBoiler_Propane = 2.79684813860435E-08* x * y
    FuelOilBoiler_Propene = 1.86456542573623E-08* x * y
    FuelOilBoiler_Sulfurdioxyde = 0.0000436681222707425* x * y
    FuelOilBoiler_Toluene = 9.32282712868113E-09* x * y
    FuelOilBoiler_Zinc = 6.5259789900768E-10* x * y

    # --- Module C2: transport to treatment --------------------------------------
    FuelOilBoiler_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    # Boiler, tank and chimney all reach end of life together.
    FuelOilBoiler_EOL_SteelLowAlloyed = FuelOilBoiler_SteelLowAlloyed
    FuelOilBoiler_EOL_StainlessSteel = FuelOilBoiler_StainlessSteel
    FuelOilBoiler_EOL_CastIron = FuelOilBoiler_CastIron
    FuelOilBoiler_EOL_Chamotte = FuelOilBoiler_Chamotte
    FuelOilBoiler_EOL_Aluminium = FuelOilBoiler_Aluminium
    FuelOilBoiler_EOL_MineralWool = FuelOilBoiler_MineralWool
    FuelOilBoiler_EOL_Copper = FuelOilBoiler_CopperA13
    FuelOilBoiler_EOL_Electronics = FuelOilBoiler_Electronics
    FuelOilBoiler_EOL_Tank_Brass = FuelOilBoiler_Tank_Brass
    FuelOilBoiler_EOL_Tank_CastIron = FuelOilBoiler_Tank_CastIron
    # Concrete volumes [m3] converted to the [kg] the end-of-life datasets use.
    FuelOilBoiler_EOL_Tank_Concrete = FuelOilBoiler_Tank_Concrete * config.CONCRETE_DENSITY
    FuelOilBoiler_EOL_Tank_Copper = FuelOilBoiler_Tank_CopperA13
    FuelOilBoiler_EOL_Tank_PEHD = FuelOilBoiler_Tank_PEHD
    FuelOilBoiler_EOL_Tank_SteelLowAlloyed = FuelOilBoiler_Tank_SteelLowAlloyed
    FuelOilBoiler_EOL_Chimney_Concrete = FuelOilBoiler_Chimney_Concrete * config.CONCRETE_DENSITY
    FuelOilBoiler_EOL_Chimney_StoneWool = FuelOilBoiler_Chimney_StoneWool

    # --- Module C4: final disposal ----------------------------------------------
    FuelOilBoiler_EOL_Landfill_Steel = FuelOilBoiler_EOL_SteelLowAlloyed * LandfillMetals
    FuelOilBoiler_EOL_Landfill_StainlessSteel = FuelOilBoiler_EOL_StainlessSteel * LandfillMetals2
    FuelOilBoiler_EOL_Landfill_CastIron = FuelOilBoiler_EOL_CastIron * LandfillMetals2
    FuelOilBoiler_EOL_Landfill_Chamotte = FuelOilBoiler_EOL_Chamotte * LandfillClaybrick
    FuelOilBoiler_EOL_Landfill_Aluminium = FuelOilBoiler_EOL_Aluminium * LandfillMetals
    FuelOilBoiler_EOL_Landfill_MineralWool = FuelOilBoiler_EOL_MineralWool * LandfillMineralWool
    FuelOilBoiler_EOL_Landfill_Copper = FuelOilBoiler_EOL_Copper * LandfillMetals
    FuelOilBoiler_EOL_Inc_Electronics = FuelOilBoiler_EOL_Electronics * IncinerationElectronics #kg
    FuelOilBoiler_EOL_Landfill_Electronics = FuelOilBoiler_EOL_Electronics * LandfillElectronics #kg
    FuelOilBoiler_EOL_Landfill_Tank_Brass = FuelOilBoiler_EOL_Tank_Brass * LandfillBrass
    FuelOilBoiler_EOL_Landfill_Tank_CastIron = FuelOilBoiler_EOL_Tank_CastIron * LandfillMetals2
    FuelOilBoiler_EOL_Landfill_Tank_Concrete = FuelOilBoiler_EOL_Tank_Concrete * LandfillConcrete
    FuelOilBoiler_EOL_Landfill_Tank_Copper = FuelOilBoiler_EOL_Tank_Copper * LandfillMetals
    FuelOilBoiler_EOL_Inc_Tank_PEHD = FuelOilBoiler_EOL_Tank_PEHD * IncinerationPEHD
    FuelOilBoiler_EOL_Landfill_Tank_PEHD = FuelOilBoiler_EOL_Tank_PEHD * LandfillPEHD
    FuelOilBoiler_EOL_Landfill_Tank_SteelLowAlloyed = FuelOilBoiler_EOL_Tank_SteelLowAlloyed * LandfillMetals
    FuelOilBoiler_EOL_Landfill_Chimney_Concrete = FuelOilBoiler_EOL_Chimney_Concrete * LandfillConcrete
    FuelOilBoiler_EOL_Landfill_Chimney_StoneWool = FuelOilBoiler_EOL_Chimney_StoneWool * LandfillMineralWool

    # --- Module D1: credit for exported secondary materials ---------------------
    # Concrete and PEHD carry their own recycling parameters and SRinert.
    FuelOilBoiler_EOL_Recycling_Steel = (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_SteelLowAlloyed) - (RecycledContentMetals * FuelOilBoiler_EOL_SteelLowAlloyed)
    FuelOilBoiler_EOL_Primary_Steel = ((RecycledContentMetals * FuelOilBoiler_EOL_SteelLowAlloyed) - (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_SteelLowAlloyed))* SRmetals
    FuelOilBoiler_EOL_Recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_StainlessSteel) - (RecycledContentMetals * FuelOilBoiler_EOL_StainlessSteel)
    FuelOilBoiler_EOL_Primary_StainlessSteel = ((RecycledContentMetals * FuelOilBoiler_EOL_StainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_StainlessSteel))* SRmetals
    # Cast iron is treated as a special metal (LandfillMetals2 /
    # RecyclingMetals2). Note: whether it should count as a common metal is an
    # open question to the inventory authors.
    FuelOilBoiler_EOL_Recycling_CastIron = (RecyclingMetals2 * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_CastIron) - (RecycledContentMetals * FuelOilBoiler_EOL_CastIron)
    FuelOilBoiler_EOL_Primary_CastIron = ((RecycledContentMetals * FuelOilBoiler_EOL_CastIron) - (RecyclingMetals2 * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_CastIron))* SRmetals
    FuelOilBoiler_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Aluminium) - (RecycledContentMetals * FuelOilBoiler_EOL_Aluminium)
    FuelOilBoiler_EOL_Primary_Aluminium = ((RecycledContentMetals * FuelOilBoiler_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Aluminium))* SRmetals
    FuelOilBoiler_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Copper) - (RecycledContentMetals * FuelOilBoiler_EOL_Copper)
    FuelOilBoiler_EOL_Primary_Copper = ((RecycledContentMetals * FuelOilBoiler_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Copper))* SRmetals
    FuelOilBoiler_EOL_Recycling_Tank_CastIron = (RecyclingMetals2 * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Tank_CastIron) - (RecycledContentMetals * FuelOilBoiler_EOL_Tank_CastIron)
    FuelOilBoiler_EOL_Primary_Tank_CastIron = ((RecycledContentMetals * FuelOilBoiler_EOL_Tank_CastIron) - (RecyclingMetals2 * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Tank_CastIron))* SRmetals
    FuelOilBoiler_EOL_Recycling_Tank_Concrete = (RecyclingConcrete * RecyclingEfficiencyConcrete * FuelOilBoiler_EOL_Tank_Concrete) - (RecycledContentConcrete * FuelOilBoiler_EOL_Tank_Concrete)
    # The primary concrete dataset is sold in [m3], so the credit is divided by
    # the density.
    FuelOilBoiler_EOL_Primary_Tank_Concrete = (((RecycledContentConcrete * FuelOilBoiler_EOL_Tank_Concrete) - (RecyclingConcrete * RecyclingEfficiencyConcrete * FuelOilBoiler_EOL_Tank_Concrete)) * SRinert) / config.CONCRETE_DENSITY
    FuelOilBoiler_EOL_Recycling_Tank_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Tank_Copper) - (RecycledContentMetals * FuelOilBoiler_EOL_Tank_Copper)
    FuelOilBoiler_EOL_Primary_Tank_Copper = ((RecycledContentMetals * FuelOilBoiler_EOL_Tank_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Tank_Copper))* SRmetals
    FuelOilBoiler_EOL_Recycling_Tank_PEHD = (RecyclingPEHD * RecyclingEfficiencyPlastics * FuelOilBoiler_EOL_Tank_PEHD) - (RecycledContentPlastic * FuelOilBoiler_EOL_Tank_PEHD)
    FuelOilBoiler_EOL_Primary_Tank_PEHD = ((RecycledContentPlastic * FuelOilBoiler_EOL_Tank_PEHD) - (RecyclingPEHD * RecyclingEfficiencyPlastics * FuelOilBoiler_EOL_Tank_PEHD))* SRinert
    FuelOilBoiler_EOL_Recycling_Tank_SteelLowAlloyed = (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Tank_SteelLowAlloyed) - (RecycledContentMetals * FuelOilBoiler_EOL_Tank_SteelLowAlloyed)
    FuelOilBoiler_EOL_Primary_Tank_SteelLowAlloyed = ((RecycledContentMetals * FuelOilBoiler_EOL_Tank_SteelLowAlloyed) - (RecyclingMetals * RecyclingEfficiencyMetals * FuelOilBoiler_EOL_Tank_SteelLowAlloyed))* SRmetals
    FuelOilBoiler_EOL_Recycling_Chimney_Concrete = (RecyclingConcrete * RecyclingEfficiencyConcrete * FuelOilBoiler_EOL_Chimney_Concrete) - (RecycledContentConcrete * FuelOilBoiler_EOL_Chimney_Concrete)
    FuelOilBoiler_EOL_Primary_Chimney_Concrete = (((RecycledContentConcrete * FuelOilBoiler_EOL_Chimney_Concrete) - (RecyclingConcrete * RecyclingEfficiencyConcrete * FuelOilBoiler_EOL_Chimney_Concrete))* SRinert) / config.CONCRETE_DENSITY

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Only the two incinerated streams earn a credit.
    FuelOilBoiler_EOL_EnergyRecoveryHeat_Electronics = - FuelOilBoiler_EOL_Inc_Electronics * LHVElectronics * Xincheat
    FuelOilBoiler_EOL_EnergyRecoveryEle_Electronics = - FuelOilBoiler_EOL_Inc_Electronics * LHVElectronics * Xincele / config.MJ_PER_KWH
    FuelOilBoiler_EOL_EnergyRecoveryHeat_PEHD = - FuelOilBoiler_EOL_Inc_Tank_PEHD * LHVHDPE * Xincheat
    FuelOilBoiler_EOL_EnergyRecoveryEle_PEHD = - FuelOilBoiler_EOL_Inc_Tank_PEHD * LHVHDPE * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, annual here; see energy_systems/__init__.py).
    ThermalEnergyProduced_fueloilboiler = TotEnergyNeeds

    # Collect every 'FuelOilBoiler_' quantity for the exchange rows.
    loc = locals()
    return {
        "activity_data": {name: value for name, value in loc.items()
                          if name.startswith("FuelOilBoiler_")},
        "sf": SFFueloilboiler,
        "replacements": FueloilboilerNumberReplacements,
        "bd_names": FuelOilBoiler_BdName,
        "bd_areas": FuelOilBoiler_BdArea,
        "thermal_energy": ThermalEnergyProduced_fueloilboiler,
    }
