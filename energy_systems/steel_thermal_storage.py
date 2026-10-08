"""
steel_thermal_storage.py - life-cycle inventory of a steel thermal store.

An insulated steel tank used as a buffer or seasonal heat store. Passive like
the concrete store, so no module B6, and it shares that file's sizing code.
The building label columns are SteelStorage_*, while every inventory quantity
is SteelThermalStorage_*. See energy_systems/__init__.py for the conventions
shared by all modules.
"""

import numpy as np


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Steel thermal storage'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Steel thermal storage")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]      # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]    # share of special metals landfilled
    LandfillMineralWool = eol["LandfillMineralWool"]
    RecyclingMetals = eol["RecyclingMetals"]    # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]  # share of special metals recycled
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                  # substitution ratio, secondary vs primary

    # DASHBOARD - VALUE INPUTS
    SteelStorage_BdName = energysystem['Building Name']
    SteelStorage_BdArea = energysystem['Zone net floor area [m2]']
    VolumeStored = energysystem['Storage [m3]']
    EnergyStored = energysystem['Energy stored [kWh/year]']

    # Sizing against the ecoinvent reference tank (500 m3); 7850 kg/m3 is the
    # density of steel.
    # Note: as in concrete_thermal_storage.py, x = RefVolume / volume is
    # inverted (a larger tank gets a smaller inventory). Open question to the
    # inventory authors.
    VolumeStored = np.array(VolumeStored)
    Lifespan_Storage = 40
    RefVolume = 10000 * 0.05 #cubic meters
    volume = VolumeStored
    x = RefVolume / volume
    mass = 7850 * x

    # --- Module A1-3: manufacture -----------------------------------------------
    # Material demand as a fraction of tank mass [kg]. The sheet-rolling rows
    # are processes applied to the aluminium and steel above.
    SteelThermalStorage_AlkydPaint = 0.0011 * mass
    SteelThermalStorage_Aluminium = 0.0277 * mass
    SteelThermalStorage_ReinforcingSteel = 0.4622 * mass
    SteelThermalStorage_SheetrollingAluminium = 0.0277 * mass
    SteelThermalStorage_SheetrollingSteel = 0.4622 * mass
    SteelThermalStorage_ChromiumSteel = 0.0010 * mass
    SteelThermalStorage_StoneWool = 0.0219 * mass
    # Weld length [m]. Note: constant per tank, not scaled by size; open
    # question to the inventory authors.
    SteelThermalStorage_Weldingarcaluminium = np.full(len(VolumeStored), 177) # m
    SteelThermalStorage_Weldingarcsteel = np.full(len(VolumeStored), 154) # m

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    SteelThermalStorage_Truck1632 = ((500 + 200)*(mass)/1000)
    SteelThermalStorage_Light_Truck = (50*(mass)/1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the tank mass.
    SteelThermalStorage_Light_Truck_B2 = (50 * (Lifespan_Storage/2) * 0.01 * (mass/1000))

    # --- Module B4: replacement within the study period -------------------------
    ThermalSteelStorageNumberReplacements = (np.maximum(np.divide(RSP, Lifespan_Storage) - 1, 0))
    SFThermalSteelStorage = (RSP / Lifespan_Storage)  # Scaling factor

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km].
    SteelThermalStorage_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    # Note: unlike every other system, the sheet-rolling rows are carried into
    # C3, C4 and D1, so the aluminium and steel are disposed of and credited
    # twice. Open question to the inventory authors.
    SteelThermalStorage_EOL_AlkydPaint = SteelThermalStorage_AlkydPaint
    SteelThermalStorage_EOL_Aluminium = SteelThermalStorage_Aluminium
    SteelThermalStorage_EOL_ReinforcingSteel = SteelThermalStorage_ReinforcingSteel
    SteelThermalStorage_EOL_SheetrollingAluminium = SteelThermalStorage_SheetrollingAluminium
    SteelThermalStorage_EOL_SheetrollingSteel = SteelThermalStorage_SheetrollingSteel
    SteelThermalStorage_EOL_ChromiumSteel = SteelThermalStorage_ChromiumSteel
    SteelThermalStorage_EOL_StoneWool = SteelThermalStorage_StoneWool

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled and incinerated shares [kg]. Alkyd paint has no end-of-life
    # share parameter and is 100% incinerated; this system has no D3 block, so
    # it takes no energy-recovery credit for it.
    SteelThermalStorage_EOL_Inc_AlkydPaint = SteelThermalStorage_EOL_AlkydPaint
    SteelThermalStorage_EOL_Landfill_Aluminium = SteelThermalStorage_EOL_Aluminium * LandfillMetals
    SteelThermalStorage_EOL_Landfill_ReinforcingSteel = SteelThermalStorage_EOL_ReinforcingSteel * LandfillMetals
    SteelThermalStorage_EOL_Landfill_SheetRollingAluminium = SteelThermalStorage_EOL_Aluminium * LandfillMetals
    SteelThermalStorage_EOL_Landfill_SheetRollingSteel = SteelThermalStorage_EOL_SheetrollingSteel * LandfillMetals
    SteelThermalStorage_EOL_Landfill_ChromiumSteel = SteelThermalStorage_EOL_ChromiumSteel * LandfillMetals2
    SteelThermalStorage_EOL_Landfill_StoneWool = SteelThermalStorage_EOL_StoneWool * LandfillMineralWool

    # --- Module D1: credit for exported secondary materials ---------------------
    # The sheet-rolling steel pair reads _EOL_ReinforcingSteel, which has the
    # same value as _EOL_SheetrollingSteel.
    SteelThermalStorage_EOL_Recycling_Aluminium = (RecyclingMetals * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_Aluminium) - (RecycledContentMetals * SteelThermalStorage_EOL_Aluminium)
    SteelThermalStorage_EOL_Primary_Aluminium = ((RecycledContentMetals * SteelThermalStorage_EOL_Aluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_Aluminium))* SRmetals

    SteelThermalStorage_EOL_Recycling_ReinforcingSteel = (RecyclingMetals * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_ReinforcingSteel) - (RecycledContentMetals * SteelThermalStorage_EOL_ReinforcingSteel)
    SteelThermalStorage_EOL_Primary_ReinforcingSteel = ((RecycledContentMetals * SteelThermalStorage_EOL_ReinforcingSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_ReinforcingSteel))* SRmetals

    SteelThermalStorage_EOL_Recycling_SheetRollingAluminium = (RecyclingMetals * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_SheetrollingAluminium) - (RecycledContentMetals * SteelThermalStorage_EOL_SheetrollingAluminium)
    SteelThermalStorage_EOL_Primary_SheetRollingAluminium = ((RecycledContentMetals * SteelThermalStorage_EOL_SheetrollingAluminium) - (RecyclingMetals * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_SheetrollingAluminium))* SRmetals

    SteelThermalStorage_EOL_Recycling_SheetRollingSteel = (RecyclingMetals * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_ReinforcingSteel) - (RecycledContentMetals * SteelThermalStorage_EOL_ReinforcingSteel)
    SteelThermalStorage_EOL_Primary_SheetRollingSteel = ((RecycledContentMetals * SteelThermalStorage_EOL_ReinforcingSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_ReinforcingSteel))* SRmetals

    SteelThermalStorage_EOL_Recycling_ChromiumSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_ChromiumSteel) - (RecycledContentMetals * SteelThermalStorage_EOL_ChromiumSteel)
    SteelThermalStorage_EOL_Primary_ChromiumSteel = ((RecycledContentMetals * SteelThermalStorage_EOL_ChromiumSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * SteelThermalStorage_EOL_ChromiumSteel))* SRmetals

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_ThermalSteelStorage = np.array([EnergyStored * RSP])

    # Collect every 'SteelThermalStorage_' quantity for the exchange rows.
    # locals() is bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("SteelThermalStorage_")}

    return {
        "activity_data": activity_data,
        "sf": SFThermalSteelStorage,
        "replacements": ThermalSteelStorageNumberReplacements,
        "bd_names": SteelStorage_BdName,
        "bd_areas": SteelStorage_BdArea,
        "thermal_energy": ThermalEnergyProduced_ThermalSteelStorage,
    }
