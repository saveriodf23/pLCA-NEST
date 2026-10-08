"""
dry_cooler.py - life-cycle inventory of a dry cooler.

A finned-coil air cooler that rejects heat straight to ambient air, with no
water circuit - which distinguishes it from the evaporative cooling tower.
See energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Cooling - Dry cooler'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Cooling - Dry cooler")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]      # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]    # share of special metals landfilled
    RecyclingMetals = eol["RecyclingMetals"]    # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]  # share of special metals recycled
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                  # substitution ratio, secondary vs primary

    # DASHBORD - VALUE INPUTS
    # The seven Electricity* columns [kWh/year] are used only as source shares
    # (module B6).
    DryCooler_BdName = energysystem['Building Name']
    DryCooler_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Cooling capacity [kW]']
    EnergyCooling = energysystem['Energy produced [kWh /year]']
    COP = energysystem['COP']
    ElectricityGrid = energysystem['Energy input from national grid [kWh/year]']
    ElectricityPV = energysystem['Energy input from Photovoltaic system [kWh/year]']
    ElectricityRICE = energysystem['Energy input from CHP-Internal Combustion Engine [kWh/year]']
    ElectricityCombinedCycle = energysystem['Energy input from CHP-Combined cycle [kWh/year]']
    ElectricityGasTurbine = energysystem['Energy input from CHP-Gas Turbine [kWh/year]']
    ElectricityWtE = energysystem['Energy input from CHP-Waste-to-Energy [kWh/year]']
    ElectricityORC = energysystem['Energy input from CHP-Organic Rankine Cycle [kWh/year]']

    # DASHBOARD - INPUT PARAMETERS
    # Unit mass [kg], quadratic in cooling capacity [kW]. The fit turns over
    # above about 910 kW, so it is only meaningful within its fitted range.
    mass = -0.0027 * (Power**2) + 4.9167 * Power
    Lifespan = 15 #years

    # --- Module A1-3: manufacture -----------------------------------------------
    # Material demand as a fraction of unit mass [kg]. The two sheet-rolling rows
    # are processes applied to the steel and aluminium above, not extra material,
    # so they have no end-of-life counterpart.
    DryCooler_LowAlloyedSteel = 0.84 * mass
    DryCooler_Aluminium = 0.07 * mass
    DryCooler_ChromiumSteel = 0.05 * mass
    DryCooler_Copper = 0.05 * mass
    DryCooler_SheetRollingSteel = 0.84 * mass
    DryCooler_SheetRollingAluminium = 0.07 * mass

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    DryCooler_Truck1632 = ((500 + 200)*(mass)/1000)
    DryCooler_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the unit mass.
    # Uses the first Lifespan (see the B4 note).
    DryCooler_Light_Truck_B2 = 50 * (Lifespan/2) * 0.01 * (mass/1000)

    # --- Module B4: replacement within the study period -------------------------
    # Note: Lifespan is reassigned here, so B2 uses 15 years while B4 and the
    # scaling factor use 25. Open question to the inventory authors.
    Lifespan = 25 #year
    DryCoolerNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFDryCooler = (RSP / Lifespan)  # Scaling factor

    # Shares of the machine's electricity by source. Only the grid and PV
    # shares are used; electricity from on-site CHP units is outside the system
    # boundary (each CHP inventories only its heat share), so the five CHP
    # shares are computed but not wired.
    #Parameters for energy input repartition
    TotalElectricityInput = (ElectricityGrid + ElectricityPV + ElectricityRICE + ElectricityCombinedCycle +
        ElectricityGasTurbine + ElectricityWtE + ElectricityORC)

    DryCooler_EleGrid = ElectricityGrid / TotalElectricityInput
    DryCooler_ElePV = ElectricityPV / TotalElectricityInput
    DryCooler_EleRICE = ElectricityRICE / TotalElectricityInput
    DryCooler_EleCombinedCycle = ElectricityCombinedCycle / TotalElectricityInput
    DryCooler_EleGasTurbine = ElectricityGasTurbine / TotalElectricityInput
    DryCooler_EleWtE = ElectricityWtE / TotalElectricityInput
    DryCooler_EleORC = ElectricityORC / TotalElectricityInput

    # --- Module B6: operating electricity ---------------------------------------
    # Electricity over the study period [kWh]: cooling delivered / COP x RSP,
    # split between grid and PV. The commented-out RECS lines are disabled
    # renewable-energy-certificate variants.
    DryCooler_UsePhaseElectricity = (1 / COP) * EnergyCooling * RSP * DryCooler_EleGrid
    DryCooler_UsephaseelectricityPV = (1 / COP) * EnergyCooling * RSP * DryCooler_ElePV

    # DryCooler_usephaseelectricityRECSPV = DryCooler_UsePhaseElectricity * 0.0056 * RECSPV
    # DryCooler_usephaseelectricityRECSHydro = DryCooler_UsePhaseElectricity * 0.0056 * RECSHydro
    # DryCooler_usephaseelectricityRECSEolic = DryCooler_UsePhaseElectricity * 0.0056 * RECSEolic

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km].
    DryCooler_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    DryCooler_EOL_Aluminium = DryCooler_Aluminium
    DryCooler_EOL_Copper = DryCooler_Copper
    DryCooler_EOL_ChromiumSteel = DryCooler_ChromiumSteel
    DryCooler_EOL_LowAlloyedSteel = DryCooler_LowAlloyedSteel

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled share of each metal [kg]. Nothing is incinerated, so there
    # is no module D3.
    DryCooler_EOL_Landfill_Aluminium = DryCooler_EOL_Aluminium * LandfillMetals
    DryCooler_EOL_Landfill_Copper = DryCooler_EOL_Copper * LandfillMetals
    DryCooler_EOL_Landfill_LowAlloyedSteel = DryCooler_EOL_LowAlloyedSteel * LandfillMetals
    DryCooler_EOL_Landfill_ChromiumSteel = DryCooler_EOL_ChromiumSteel * LandfillMetals2

    # --- Module D1: credit for exported secondary materials ---------------------
    DryCooler_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * DryCooler_EOL_Aluminium) - (RecycledContentMetals * DryCooler_EOL_Aluminium)
    DryCooler_EOL_Primary_Aluminium = ((RecycledContentMetals * DryCooler_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * DryCooler_EOL_Aluminium)) * SRmetals

    DryCooler_EOL_Recycling_Copper = (RecyclingMetals * RecyclingEfficiencyMetals * DryCooler_EOL_Copper) - (RecycledContentMetals * DryCooler_EOL_Copper)
    DryCooler_EOL_Primary_Copper = ((RecycledContentMetals * DryCooler_EOL_Copper) - (RecyclingMetals * RecyclingEfficiencyMetals * DryCooler_EOL_Copper)) * SRmetals

    DryCooler_EOL_Recycling_LowAlloyedSteel = (RecyclingMetals * RecyclingEfficiencyMetals * DryCooler_EOL_LowAlloyedSteel) - (RecycledContentMetals * DryCooler_EOL_LowAlloyedSteel)
    DryCooler_EOL_Primary_LowAlloyedSteel = ((RecycledContentMetals * DryCooler_EOL_LowAlloyedSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * DryCooler_EOL_LowAlloyedSteel)) * SRmetals

    DryCooler_EOL_Recycling_ChromiumSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * DryCooler_EOL_ChromiumSteel) - (RecycledContentMetals * DryCooler_EOL_ChromiumSteel)
    DryCooler_EOL_Primary_ChromiumSteel = ((RecycledContentMetals * DryCooler_EOL_ChromiumSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * DryCooler_EOL_ChromiumSteel)) * SRmetals

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyAbsorbed_DryCooler = EnergyCooling * RSP

    # Collect every 'DryCooler_' quantity for the exchange rows. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("DryCooler_")}

    return {
        "activity_data": activity_data,
        "sf": SFDryCooler,
        "replacements": DryCoolerNumberReplacements,
        "bd_names": DryCooler_BdName,
        "bd_areas": DryCooler_BdArea,
        "thermal_energy": ThermalEnergyAbsorbed_DryCooler,
    }
