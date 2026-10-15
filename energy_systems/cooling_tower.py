# Derived from LCA4DHC (Energy_systems/CoolingEvaporativeTower.ipynb) -
# Copyright 2026 Kevin Autelitano and Jacopo Famiglietti, licensed under the
# Apache License 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
cooling_tower.py - life-cycle inventory of an evaporative cooling tower.

A wet tower that rejects heat by evaporating water, so unlike the dry cooler it
has a water demand and a wastewater stream in module B6. See
energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Cooling - Cooling tower'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Cooling - Cooling tower")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]      # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]    # share of special metals landfilled
    LandfillPVC = eol["LandfillPVC"]
    IncinerationPVC = eol["IncinerationPVC"]
    RecyclingMetals = eol["RecyclingMetals"]    # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]  # share of special metals recycled
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                  # substitution ratio, secondary vs primary
    LHVPVC = eol["LHVPVC"]                      # lower heating value [MJ/kg], for D3
    Xincheat = eol["Xincheat"]                  # heat recovery efficiency of incineration
    Xincele = eol["Xincele"]                    # electricity recovery efficiency

    # DASHBORD - VALUE INPUTS
    # The seven Electricity* columns [kWh/year] are used only as source shares
    # (module B6).
    CoolingTower_BdName = energysystem['Building Name']
    CoolingTower_BdArea = energysystem['Zone net floor area [m2]']
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
    # Unit mass [kg] scaled linearly from the ecoinvent reference machine:
    # 3,500 kg at 300 kW of cooling capacity.
    massRef = 3500 #kg
    PowerRef = 300 # kW (Source: Ecoinvent database)
    mass = massRef * (Power / PowerRef)
    Lifespan = 20 # year

    # --- Module A1-3: manufacture -----------------------------------------------
    # Material demand as a fraction of unit mass [kg]. The sheet-rolling row is
    # a process applied to the stainless steel, not extra material.
    # Note: the LCI charges the "PVC (fillers)" component against high-density
    # polyethylene; here it is wired to PVC. Open question.
    CoolingTower_StainlessSteel = 0.4738 * mass
    CoolingTower_PVC = 0.10822 * mass
    CoolingTower_CastIron = 0.3376 * mass
    CoolingTower_Airfun = 0.0760 * mass
    CoolingTower_SheetRollingChromiumSteel = 0.4738 * mass

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    CoolingTower_Truck1632 = ((500 + 200)*(mass)/1000)
    CoolingTower_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the unit mass.
    # Uses the first Lifespan (see the B4 note).
    CoolingTower_Light_Truck_B2 = 50 * (Lifespan/2) * 0.01 * (mass/1000)

    # --- Module B4: replacement within the study period -------------------------
    # Note: Lifespan is reassigned here, so B2 uses 20 years while B4 and the
    # scaling factor use 25. Open question to the inventory authors.
    Lifespan = 25 #year Hampoo et al. (2021)
    CoolingTowerNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFCoolingTower = (RSP / Lifespan)  # Scaling factor

    # Shares of the machine's electricity by source. Only the grid and PV
    # shares are used; electricity from on-site CHP units is outside the system
    # boundary (each CHP inventories only its heat share), so the five CHP
    # shares are computed but not wired.
    #Parameters for energy input repartition
    TotalElectricityInput = (ElectricityGrid + ElectricityPV + ElectricityRICE + ElectricityCombinedCycle +
        ElectricityGasTurbine + ElectricityWtE + ElectricityORC)

    CoolingTower_EleGrid = ElectricityGrid / TotalElectricityInput
    CoolingTower_ElePV = ElectricityPV / TotalElectricityInput
    CoolingTower_EleRICE = ElectricityRICE / TotalElectricityInput
    CoolingTower_EleCombinedCycle = ElectricityCombinedCycle / TotalElectricityInput
    CoolingTower_EleGasTurbine = ElectricityGasTurbine / TotalElectricityInput
    CoolingTower_EleWtE = ElectricityWtE / TotalElectricityInput
    CoolingTower_EleORC = ElectricityORC / TotalElectricityInput

    # --- Module B6: operating electricity and water -----------------------------
    # Electricity over the study period [kWh]: cooling delivered / COP x RSP,
    # split between grid and PV. The commented-out RECS lines are disabled
    # renewable-energy-certificate variants.
    CoolingTower_UsePhaseElectricity = (1 / COP) * EnergyCooling * RSP * CoolingTower_EleGrid
    CoolingTower_UsephaseelectricityPV = (1 / COP) * EnergyCooling * RSP * CoolingTower_ElePV

    # CoolingTower_usephaseelectricityRECSPV = CoolingTower_UsePhaseElectricity * 0.0056 * RECSPV
    # CoolingTower_usephaseelectricityRECSHydro = CoolingTower_UsePhaseElectricity * 0.0056 * RECSHydro
    # CoolingTower_usephaseelectricityRECSEolic = CoolingTower_UsePhaseElectricity * 0.0056 * RECSEolic

    # Water demand [kg, for the kilogram-based dataset] and wastewater [m3].
    # Notes: both scale on installed capacity rather than on cooling delivered
    # or the study period; and the wastewater share is 3% where the LCI gives
    # 33%. Both are open questions to the inventory authors.
    waterdemand_m3 = 63740 * (Power / PowerRef)                 # [m3]
    CoolingTower_Waterdemand = waterdemand_m3 * 1000            # [kg]
    CoolingTower_WasteWater = 0.03 * waterdemand_m3             # [m3]

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km].
    CoolingTower_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    CoolingTower_EOL_StainlessSteel = CoolingTower_StainlessSteel
    CoolingTower_EOL_PVC = CoolingTower_PVC
    CoolingTower_EOL_CastIron = CoolingTower_CastIron
    CoolingTower_EOL_Airfun = CoolingTower_Airfun

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled and incinerated shares of each material [kg].
    # Note: the fan is landfilled with LandfillMetals2 but recycled with
    # RecyclingMetals in D1; which metal family it belongs to is an open
    # question.
    CoolingTower_EOL_Landfill_StainlessSteel = CoolingTower_EOL_StainlessSteel * LandfillMetals2
    CoolingTower_EOL_Inc_PVC = CoolingTower_EOL_PVC * IncinerationPVC
    CoolingTower_EOL_Landfill_PVC = CoolingTower_EOL_PVC * LandfillPVC
    CoolingTower_EOL_Landfill_CastIron = CoolingTower_EOL_CastIron * LandfillMetals
    CoolingTower_EOL_Landfill_Airfun = CoolingTower_EOL_Airfun * LandfillMetals2

    # --- Module D1: credit for exported secondary materials ---------------------
    # PVC takes no D1 credit: it is only incinerated or landfilled (the two
    # shares sum to 1). The two PVC lines below repeat the C4 values.
    CoolingTower_EOL_Recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * CoolingTower_EOL_StainlessSteel) - (RecycledContentMetals * CoolingTower_EOL_StainlessSteel)
    CoolingTower_EOL_Primary_StainlessSteel = ((RecycledContentMetals * CoolingTower_EOL_StainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CoolingTower_EOL_StainlessSteel))* SRmetals

    CoolingTower_EOL_Inc_PVC = CoolingTower_EOL_PVC * IncinerationPVC
    CoolingTower_EOL_Landfill_PVC = CoolingTower_EOL_PVC * LandfillPVC

    # Cast iron is treated as a common metal here (LandfillMetals /
    # RecyclingMetals). Note: which family it belongs to is an open question.
    CoolingTower_EOL_Recycling_CastIron = (RecyclingMetals * RecyclingEfficiencyMetals * CoolingTower_EOL_CastIron) - (RecycledContentMetals * CoolingTower_EOL_CastIron)
    CoolingTower_EOL_Primary_CastIron = ((RecycledContentMetals * CoolingTower_EOL_CastIron) - (RecyclingMetals * RecyclingEfficiencyMetals * CoolingTower_EOL_CastIron)) * SRmetals

    CoolingTower_EOL_Recycling_Airfun = (RecyclingMetals * RecyclingEfficiencyMetals * CoolingTower_EOL_Airfun) - (RecycledContentMetals * CoolingTower_EOL_Airfun)
    CoolingTower_EOL_Primary_Airfun = ((RecycledContentMetals * CoolingTower_EOL_Airfun) - (RecyclingMetals * RecyclingEfficiencyMetals * CoolingTower_EOL_Airfun)) * SRmetals

    # --- Module D3: credit for energy recovered from incineration ---------------
    # Heat [MJ] and electricity [kWh, via config.MJ_PER_KWH]; negative credits.
    CoolingTower_EOL_EnergyRecoveryHeat_PVC = - CoolingTower_EOL_Inc_PVC * LHVPVC * Xincheat
    CoolingTower_EOL_EnergyRecoveryEle_PVC = - CoolingTower_EOL_Inc_PVC * LHVPVC * Xincele / config.MJ_PER_KWH

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyAbsorbed_CoolingTower = EnergyCooling * RSP

    # Collect every 'CoolingTower_' quantity for the exchange rows. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("CoolingTower_")}

    return {
        "activity_data": activity_data,
        "sf": SFCoolingTower,
        "replacements": CoolingTowerNumberReplacements,
        "bd_names": CoolingTower_BdName,
        "bd_areas": CoolingTower_BdArea,
        "thermal_energy": ThermalEnergyAbsorbed_CoolingTower,
    }
