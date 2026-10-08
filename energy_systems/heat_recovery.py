"""
heat_recovery.py - life-cycle inventory of a heat recovery unit.

An air-to-air heat exchanger that recovers heat from an exhaust stream: one
material, stainless steel. It has no module B6 (a passive exchanger consumes
no fuel or electricity), A5 or D3; those activities exist and score zero.
See energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Heat recovery' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Heat recovery")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals2 = eol["LandfillMetals2"]    # share of special metals landfilled
    RecyclingMetals2 = eol["RecyclingMetals2"]  # share of special metals recycled
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                  # substitution ratio, secondary vs primary

    # DASHBOARD - VALUE INPUTS
    HeatRecovery_BdName = energysystem['Building Name']
    HeatRecovery_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Thermal capacity [kW]']
    ThermalEnergyRecovered = energysystem['Thermal energy recovered [kWh/year]']
    # Unit mass [kg], linear in capacity from one manufacturer figure.
    # Note: 12 kg for 450 kW (0.027 kg/kW) is orders of magnitude below every
    # other technology, and mass drives every module of this system. Open
    # question to the inventory authors (12 t would give 26.7 kg/kW).
    massHeatRecovery = Power * (12 / 450) # Source: Nordictec (450 kW - weight: 12 kg)
    Lifespan = 20 #years

    # --- Module A1-3: manufacture -----------------------------------------------
    # The whole unit is stainless steel [kg].
    HeatRecovery_StainlessSteel = massHeatRecovery

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    HeatRecovery_Truck1632 = ((500 + 200)*(massHeatRecovery)/1000)
    HeatRecovery_Light_Truck = (50*(massHeatRecovery)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the unit mass.
    HeatRecovery_Light_Truck_B2 = 50 * (Lifespan/2) * 0.01 * (massHeatRecovery/1000)

    # --- Module B4: replacement within the study period -------------------------
    HeatRecoveryNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFHeatRecovery = (RSP / Lifespan)  # Scaling factor

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km].
    HeatRecovery_Transport_To_Treatment_Plant = 50 * (massHeatRecovery/1000)

    # --- Module C3: waste processing --------------------------------------------
    HeatRecovery_EOL_StainlessSteel = HeatRecovery_StainlessSteel

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled share [kg]. Nothing is incinerated, so there is no D3.
    HeatRecovery_EOL_Landfill_StainlessSteel = HeatRecovery_EOL_StainlessSteel * LandfillMetals2

    # --- Module D1: credit for exported secondary materials ---------------------
    HeatRecovery_EOL_Recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * HeatRecovery_EOL_StainlessSteel) - (RecycledContentMetals * HeatRecovery_EOL_StainlessSteel)
    HeatRecovery_EOL_Primary_StainlessSteel = ((RecycledContentMetals * HeatRecovery_EOL_StainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * HeatRecovery_EOL_StainlessSteel))* SRmetals

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyRecovered = np.array([ThermalEnergyRecovered])
    ThermalEnergyProduced_HeatRecovery = ThermalEnergyRecovered

    # Collect every 'HeatRecovery_' quantity for the exchange rows. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("HeatRecovery_")}

    return {
        "activity_data": activity_data,
        "sf": SFHeatRecovery,
        "replacements": HeatRecoveryNumberReplacements,
        "bd_names": HeatRecovery_BdName,
        "bd_areas": HeatRecovery_BdArea,
        "thermal_energy": ThermalEnergyProduced_HeatRecovery,
    }
