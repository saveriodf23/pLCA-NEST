# Derived from LCA4DHC (Energy_systems/ThermalConcreteStorage.ipynb) -
# Copyright 2026 Kevin Autelitano and Jacopo Famiglietti, licensed under the
# Apache License 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
concrete_thermal_storage.py - life-cycle inventory of a concrete thermal store.

A buried concrete mass used as a seasonal or daily heat store. It is passive,
so there is no module B6. Shares its sizing code with
steel_thermal_storage.py. The building label columns are ConcreteStorage_*,
while every inventory quantity is ConcreteThermalStorage_*. See
energy_systems/__init__.py for the conventions shared by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Concrete thermal storage'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names and bd_areas (see
        energy_systems/__init__.py).
    """
    energysystem = sc.sheet("Concrete thermal storage")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillConcrete = eol["LandfillConcrete"]  # share of concrete landfilled
    LandfillMetals = eol["LandfillMetals"]      # share of low-alloyed metals landfilled
    LandfillMineralWool = eol["LandfillMineralWool"]
    RecyclingConcrete = eol["RecyclingConcrete"]
    RecyclingMetals = eol["RecyclingMetals"]    # share of low-alloyed metals recycled
    RecyclingEfficiencyConcrete = eol["RecyclingEfficiencyConcrete"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentConcrete = eol["RecycledContentConcrete"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                  # substitution ratios, secondary vs primary
    SRinert = eol["SRinert"]

    # DASHBOARD - VALUE INPUTS
    ConcreteStorage_BdName = energysystem['Building Name']
    ConcreteStorage_BdArea = energysystem['Zone net floor area [m2]']
    VolumeStored = energysystem['Storage [m3]'];
    EnergyStored = energysystem['Energy stored [kWh/year]'];    # currently unused

    # Sizing against the ecoinvent reference store (1000 m3).
    # Note: x = RefVolume / volume is inverted with respect to every other
    # technology (a larger store gets a smaller inventory), and mass, the
    # steels, the stone wool and the A5 excavation all follow x. Open question
    # to the inventory authors.
    Lifespan_Storage = 40
    RefVolume = 10000 * 0.1 #cubic meters
    volume = VolumeStored
    x = RefVolume / volume
    mass = 2400 * x

    # --- Module A1-3: manufacture -----------------------------------------------
    # Material demand [kg]: reinforcement and shell steel, stone wool
    # insulation. Concrete is in [m3].
    # Note: the concrete is a fixed 0.98 m3 per store, not scaled by size; open
    # question to the inventory authors.
    ConcreteThermalStorage_SteelLowAlloyed = 0.37 * mass
    ConcreteThermalStorage_SteelUnalloyed = 0.63 * mass
    ConcreteThermalStorage_Concrete = np.full(len(VolumeStored), 0.98)
    ConcreteThermalStorage_StoneWool = 0.00219 * mass

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    ConcreteThermalStorage_Truck1632 = ((500 + 200)*(mass)/1000)
    ConcreteThermalStorage_Light_Truck = (50*(mass)/1000)

    # --- Module A5: installation ------------------------------------------------
    # Excavation, relative to the reference store's earthworks.
    # Note: computed but not wired - this system has no A5 exchange rows, while
    # the LCI lists excavation and refilling. Open question to the inventory
    # authors.
    ConcreteThermalStorage_excavation = x

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the store mass.
    ConcreteThermalStorage_Light_Truck_B2 = (50 * (Lifespan_Storage/2) * 0.01 * (mass/1000))

    # --- Module B4: replacement within the study period -------------------------
    ThermalConcreteStorageNumberReplacements = (np.maximum(np.divide(RSP, Lifespan_Storage) - 1, 0))
    SFThermalConcreteStorage = (RSP / Lifespan_Storage)  # Scaling factor

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km].
    ConcreteThermalStorage_Transport_To_Treatment_Plant = 50 * (mass/1000)

    # --- Module C3: waste processing --------------------------------------------
    ConcreteThermalStorage_EOL_SteelLowAlloyed = ConcreteThermalStorage_SteelLowAlloyed
    ConcreteThermalStorage_EOL_SteelUnalloyed = ConcreteThermalStorage_SteelUnalloyed
    # Concrete volume [m3] converted to the [kg] the end-of-life datasets use
    # (LCI: "Mass of input material in product stage A1-3 * 2400").
    ConcreteThermalStorage_EOL_Concrete = ConcreteThermalStorage_Concrete * config.CONCRETE_DENSITY
    ConcreteThermalStorage_EOL_StoneWool = ConcreteThermalStorage_StoneWool

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled share of each material [kg]. Nothing is incinerated, so
    # there is no D3.
    ConcreteThermalStorage_EOL_Landfill_SteelLowAlloyed = ConcreteThermalStorage_EOL_SteelLowAlloyed * LandfillMetals
    ConcreteThermalStorage_EOL_Landfill_SteelUnalloyed = ConcreteThermalStorage_EOL_SteelUnalloyed * LandfillMetals
    ConcreteThermalStorage_EOL_Landfill_Concrete = ConcreteThermalStorage_EOL_Concrete * LandfillConcrete
    ConcreteThermalStorage_EOL_Landfill_StoneWool = ConcreteThermalStorage_EOL_StoneWool * LandfillMineralWool

    # --- Module D1: credit for exported secondary materials ---------------------
    ConcreteThermalStorage_EOL_Recycling_SteelLowAlloyed = (RecyclingMetals * RecyclingEfficiencyMetals * ConcreteThermalStorage_EOL_SteelLowAlloyed) - (RecycledContentMetals * ConcreteThermalStorage_EOL_SteelLowAlloyed)
    ConcreteThermalStorage_EOL_Primary_SteelLowAlloyed = ((RecycledContentMetals * ConcreteThermalStorage_EOL_SteelLowAlloyed) - (RecyclingMetals * RecyclingEfficiencyMetals * ConcreteThermalStorage_EOL_SteelLowAlloyed))* SRmetals

    ConcreteThermalStorage_EOL_Recycling_SteelUnalloyed = (RecyclingMetals * RecyclingEfficiencyMetals * ConcreteThermalStorage_EOL_SteelUnalloyed) - (RecycledContentMetals * ConcreteThermalStorage_EOL_SteelUnalloyed)
    ConcreteThermalStorage_EOL_Primary_SteelUnalloyed = ((RecycledContentMetals * ConcreteThermalStorage_EOL_SteelUnalloyed) - (RecyclingMetals * RecyclingEfficiencyMetals * ConcreteThermalStorage_EOL_SteelUnalloyed))* SRmetals

    ConcreteThermalStorage_EOL_Recycling_Concrete = (RecyclingConcrete * RecyclingEfficiencyConcrete * ConcreteThermalStorage_EOL_Concrete) - (RecycledContentConcrete * ConcreteThermalStorage_EOL_Concrete)
    # The primary concrete dataset is sold in [m3], so the credit is divided by
    # the density.
    ConcreteThermalStorage_EOL_Primary_Concrete = (((RecycledContentConcrete * ConcreteThermalStorage_EOL_Concrete) - (RecyclingConcrete * RecyclingEfficiencyConcrete * ConcreteThermalStorage_EOL_Concrete)) * SRinert) / config.CONCRETE_DENSITY

    # Collect every 'ConcreteThermalStorage_' quantity for the exchange rows.
    # locals() is bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("ConcreteThermalStorage_")}

    return {
        "activity_data": activity_data,
        "sf": SFThermalConcreteStorage,
        "replacements": ThermalConcreteStorageNumberReplacements,
        "bd_names": ConcreteStorage_BdName,
        "bd_areas": ConcreteStorage_BdArea,
    }
