# Derived from LCA4DHC (Energy_systems/CoolingCompressionChiller.ipynb) -
# Copyright 2026 Kevin Autelitano and Jacopo Famiglietti, licensed under the
# Apache License 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
compression_chiller.py - life-cycle inventory of a vapour-compression chiller.

An electrically driven compression chiller. Its refrigerant charge and leakage
are not modelled (no module B1, unlike the electric heat pump). See
energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the
        'Cooling - Compression chiller' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Cooling - Compression chiller")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]      # share of low-alloyed metals landfilled
    RecyclingMetals = eol["RecyclingMetals"]    # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]  # share of special metals recycled
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                  # substitution ratio, secondary vs primary

    # DASHBORD - VALUE INPUTS
    # SCOP is the seasonal coefficient of performance. The seven Electricity*
    # columns [kWh/year] are used only as source shares (module B6).
    CompressionChiller_BdName = energysystem['Building Name']
    CompressionChiller_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Cooling capacity [kW]']
    EnergyCooling = energysystem['Energy produced [kWh /year]']
    SCOP = energysystem['COP']
    ElectricityGrid = energysystem['Energy input from national grid [kWh/year]']
    ElectricityPV = energysystem['Energy input from Photovoltaic system [kWh/year]']
    ElectricityRICE = energysystem['Energy input from CHP-Internal Combustion Engine [kWh/year]']
    ElectricityCombinedCycle = energysystem['Energy input from CHP-Combined cycle [kWh/year]']
    ElectricityGasTurbine = energysystem['Energy input from CHP-Gas Turbine [kWh/year]']
    ElectricityWtE = energysystem['Energy input from CHP-Waste-to-Energy [kWh/year]']
    ElectricityORC = energysystem['Energy input from CHP-Organic Rankine Cycle [kWh/year]']

    # DASHBOARD - INPUT PARAMETERS
    # Unit mass [kg] scaled linearly from the ecoinvent reference machine:
    # 3,500 kg at 300 kW of cooling capacity.
    massRef = 3500 #kg
    PowerRef = 300 # kW (Source: Ecoinvent database)
    mass = massRef * (Power / PowerRef)
    Lifespan = 15 #years

    # --- Module A1-3: manufacture -----------------------------------------------
    # Material demand as a fraction of unit mass [kg]. The two sheet-rolling rows
    # are processes applied to the steel and aluminium above, not extra material,
    # so they have no end-of-life counterpart.
    CompressionChiller_Aluminium = 0.0427 * mass
    CompressionChiller_CastIron = 0.1921 * mass
    CompressionChiller_Copper = 0.0138 * mass
    CompressionChiller_LowAlloyedSteel = 0.7515 * mass
    CompressionChiller_SheetRollingSteel = 0.7515 * mass
    CompressionChiller_SheetRollingAluminium = 0.0427 * mass

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    CompressionChiller_Truck1632 = ((500 + 200)*(mass)/1000)
    CompressionChiller_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the unit mass.
    # Uses the first Lifespan (see the B4 note).
    CompressionChiller_Light_Truck_B2 = 50 * (Lifespan/2) * 0.01 * (mass/1000)

    # --- Module B4: replacement within the study period -------------------------
    # Note: Lifespan is reassigned here, so B2 uses 15 years while B4 and the
    # scaling factor use 25. Open question to the inventory authors.
    Lifespan = 25 #year Hampoo et al. (2021)
    CompressionChillerNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFCompressionChiller = (RSP / (Lifespan))  # Scaling factor

    # Shares of the machine's electricity by source. Only the grid and PV
    # shares are used; electricity from on-site CHP units is outside the system
    # boundary (each CHP inventories only its heat share), so the five CHP
    # shares are computed but not wired.
    #Parameters for energy input repartition
    TotalElectricityInput = (ElectricityGrid + ElectricityPV + ElectricityRICE + ElectricityCombinedCycle +
        ElectricityGasTurbine + ElectricityWtE + ElectricityORC)

    CompressionChiller_EleGrid = ElectricityGrid / TotalElectricityInput
    CompressionChiller_ElePV = ElectricityPV / TotalElectricityInput
    CompressionChiller_EleRICE = ElectricityRICE / TotalElectricityInput
    CompressionChiller_EleCombinedCycle = ElectricityCombinedCycle / TotalElectricityInput
    CompressionChiller_EleGasTurbine = ElectricityGasTurbine / TotalElectricityInput
    CompressionChiller_EleWtE = ElectricityWtE / TotalElectricityInput
    CompressionChiller_EleORC = ElectricityORC / TotalElectricityInput

    # --- Module B6: operating electricity ---------------------------------------
    # Electricity over the study period [kWh]: cooling delivered / SCOP x RSP,
    # split between grid and PV. The commented-out RECS lines are disabled
    # renewable-energy-certificate variants.
    CompressionChiller_UsePhaseElectricity = (1 / SCOP) * EnergyCooling * RSP * CompressionChiller_EleGrid
    CompressionChiller_UsephaseelectricityPV = (1 / SCOP) * EnergyCooling * RSP * CompressionChiller_ElePV

    # CompressionChiller_usephaseelectricityRECSPV = CompressionChiller_UsePhaseElectricity * 0.0056 * RECSPV
    # CompressionChiller_usephaseelectricityRECSHydro = CompressionChiller_UsePhaseElectricity * 0.0056 * RECSHydro
    # CompressionChiller_usephaseelectricityRECSEolic = CompressionChiller_UsePhaseElectricity * 0.0056 * RECSEolic

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km].
    CompressionChiller_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    CompressionChiller_EOL_Aluminium = CompressionChiller_Aluminium
    CompressionChiller_EOL_Copper = CompressionChiller_Copper
    CompressionChiller_EOL_CastIron = CompressionChiller_CastIron
    CompressionChiller_EOL_LowAlloyedSteel = CompressionChiller_LowAlloyedSteel

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled share of each metal [kg]. Nothing is incinerated, so there
    # is no module D3.
    CompressionChiller_EOL_Landfill_Aluminium = CompressionChiller_EOL_Aluminium * LandfillMetals
    CompressionChiller_EOL_Landfill_Copper = CompressionChiller_EOL_Copper * LandfillMetals
    CompressionChiller_EOL_Landfill_LowAlloyedSteel = CompressionChiller_EOL_LowAlloyedSteel * LandfillMetals
    CompressionChiller_EOL_Landfill_CastIron = CompressionChiller_EOL_CastIron * LandfillMetals

    # --- Module D1: credit for exported secondary materials ---------------------
    # Cast iron is treated as a common metal here (LandfillMetals /
    # RecyclingMetals), unlike in the boilers. Note: which family it belongs to
    # is an open question to the inventory authors.
    CompressionChiller_EOL_Recycling_CastIron = (RecyclingMetals * RecyclingEfficiencyMetals * CompressionChiller_EOL_CastIron) - (RecycledContentMetals * CompressionChiller_EOL_CastIron)
    CompressionChiller_EOL_Primary_CastIron = ((RecycledContentMetals * CompressionChiller_EOL_CastIron) - (RecyclingMetals * RecyclingEfficiencyMetals * CompressionChiller_EOL_CastIron)) * SRmetals

    CompressionChiller_EOL_Recycling_Steel = (RecyclingMetals * RecyclingEfficiencyMetals * CompressionChiller_EOL_LowAlloyedSteel) - (RecycledContentMetals * CompressionChiller_EOL_LowAlloyedSteel)
    CompressionChiller_EOL_Primary_Steel = ((RecycledContentMetals * CompressionChiller_EOL_LowAlloyedSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * CompressionChiller_EOL_LowAlloyedSteel)) * SRmetals

    CompressionChiller_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * CompressionChiller_EOL_Aluminium) - (RecycledContentMetals * CompressionChiller_EOL_Aluminium)
    CompressionChiller_EOL_Primary_Aluminium = ((RecycledContentMetals * CompressionChiller_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * CompressionChiller_EOL_Aluminium)) * SRmetals

    CompressionChiller_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * CompressionChiller_EOL_Copper) - (RecycledContentMetals * CompressionChiller_EOL_Copper)
    CompressionChiller_EOL_Primary_Copper = ((RecycledContentMetals * CompressionChiller_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * CompressionChiller_EOL_Copper)) * SRmetals

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyAbsorbed_CompressionChiller = EnergyCooling * RSP

    # Collect every 'CompressionChiller_' quantity for the exchange rows.
    # locals() is bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("CompressionChiller_")}

    return {
        "activity_data": activity_data,
        "sf": SFCompressionChiller,
        "replacements": CompressionChillerNumberReplacements,
        "bd_names": CompressionChiller_BdName,
        "bd_areas": CompressionChiller_BdArea,
        "thermal_energy": ThermalEnergyAbsorbed_CompressionChiller,
    }
