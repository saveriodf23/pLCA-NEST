# Derived from LCA4DHC (Energy_systems/GeothermalPlant.ipynb) - Copyright 2026
# Kevin Autelitano and Jacopo Famiglietti, licensed under the Apache License
# 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
geothermal.py - life-cycle inventory of a geothermal plant.

A deep well delivering geothermal vapour, plus a heat exchanger transferring
that heat to the neighbourhood circuit.

This is the one composite system: one worksheet, three registry entries in
plca/config.py, because the well (50 years) and the heat exchanger (15 years)
need different scaling factors and replacement counts:

  Geothermal_DeepWell        A13, A4, A5, C2, C3, C4, D1, D3 - scaled by SFwell
  Geothermal_HeatExchanger   the same modules             - scaled by SFHRX
  Geothermal                 B2 and B6, plus the sum of the other two

Each part is scaled and has its own B4 inclusion applied to D1 and D3 before
the two are added into `Geothermal` (see plca.lca_model.assemble_composite).

Variable prefixes:

  Geothermal_*                  shared quantities (A1-3 materials, C3/C4/D1,
                                B2 and B6)
  Geothermal_DeepWell_*         the well's transport rows (A4, A5, C2)
  Geothermal_HeatExchanger_*    the exchanger's transport rows (A4, A5, C2)

so activity_data is filtered on the common 'Geothermal' stem. `sf` and
`replacements` are returned as dicts keyed by registry system name.
"""

import numpy as np


def compute(sc, eol):
    """Per-building quantities for the deep well and the heat exchanger.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Geothermal plant' worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, bd_names, bd_areas and thermal_energy, plus `sf` and
        `replacements` as dicts keyed by registry system name.
    """
    energysystem = sc.sheet("Geothermal plant")

    # --- scenario and end-of-life parameters ----------------------------------
    RSP = sc.rsp                                    # reference study period [years]

    LandfillMetals = eol["LandfillMetals"]          # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    RecyclingMetals = eol["RecyclingMetals"]        # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]      # share of special metals recycled
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                      # substitution ratio, secondary vs primary

    # DASHBOARD - VALUE INPUTS
    # The vapour input and the two vapour temperatures are currently unused.
    Geothermal_BdName = energysystem['Building Name']
    Geothermal_BdArea = energysystem['Zone net floor area [m2]']
    Power = energysystem['Thermal capacity [kW]']
    EnergyProduced = energysystem['Thermal energy produced [kWh/year]']
    EnergyInputVapour = energysystem['Energy input vapour [kWh/year]']
    SupplyTemperatureVapour = energysystem['Supply temperature vapour [°C]']
    ReturnTemperatureVapour = energysystem['Return temperature vapour [°C]']

    # Two lifetimes: the well (civil asset) and the heat exchanger (machine).
    Lifespan = 50 #years
    HRXLifespan = 15 #years

    # Heat-exchanger mass [kg], from the same manufacturer figure as
    # heat_recovery.py.
    # Note: 12 kg for 450 kW (0.027 kg/kW) is orders of magnitude below every
    # other technology; open question to the inventory authors.
    massHRXGeothermal = Power * (12 / 450) # Source: Nordictec (450 kW - weight: 12 kg)

    # --- Module A1-3: manufacture -----------------------------------------------
    # Well casing steel [kg], scaled from the ecoinvent reference plant (223 t
    # for 5.5 MW electrical; 5500 * 6.4 converts that to thermal capacity), and
    # the exchanger's stainless steel. `mass` is currently unused.
    Geothermal_LowAlloyedSteel = 223000 * (Power / (5500 * 6.4) )
    Geothermal_StainlessSteel = massHRXGeothermal
    massDeepwell = Geothermal_LowAlloyedSteel
    massHRX = Geothermal_StainlessSteel
    mass = Geothermal_LowAlloyedSteel + massHRXGeothermal

    # --- Module A4: transport to site -------------------------------------------
    # Freight [t.km] per part: 700 km by heavy lorry, 50 km by light lorry.
    Geothermal_DeepWell_Truck1632 = ((500 + 200)*(Geothermal_LowAlloyedSteel)/1000)
    Geothermal_DeepWell_Light_Truck = (50*(Geothermal_LowAlloyedSteel)/1000)

    Geothermal_HeatExchanger_Truck1632 = ((500 + 200)*(massHRXGeothermal)/1000)
    Geothermal_HeatExchanger_Light_Truck = (50*(massHRXGeothermal)/1000)

    # --- Module A5: installation ------------------------------------------------
    # Well drilling [m] (same reference plant), drilling diesel [MJ] and site
    # transport of both parts [t.km].
    # Note: the diesel is a flat 5,900 per building regardless of capacity or
    # depth; open question to the inventory authors.
    Geothermal_Deepwell = 32000 * (Power / (5500 * 6.4) ) # 5.5 MWel (Ecoinvent)
    Geothermal_DieselA5 = np.full(len(Power), 5900)
    Geothermal_DeepWell_Light_TruckA5 = (160 * (Geothermal_LowAlloyedSteel) / 1000)
    Geothermal_DeepWell_Truck1632A5 = (180 * (Geothermal_LowAlloyedSteel) / 1000)

    Geothermal_HeatExchanger_Light_TruckA5 = (160 * (massHRXGeothermal) / 1000)
    Geothermal_HeatExchanger_Truck1632A5 = (180 * (massHRXGeothermal) / 1000)

    # --- Module B2: maintenance -------------------------------------------------
    # 50 km per visit, one visit every two years of each part's life, carrying
    # 1% of its mass. Both rows belong to the parent's B2, which is scaled by
    # SFwell - so the exchanger's maintenance uses the well's scaling factor.
    Geothermal_Light_Truck_B2_HRX = np.array(50 * (HRXLifespan / 2) * 0.01 * (massHRXGeothermal / 1000))  # Light_Truk_B2 come array
    Geothermal_Light_Truck_B2_Well = np.array(50 * (Lifespan / 2) * 0.01 * (Geothermal_LowAlloyedSteel / 1000))  # Light_Truk_B2 come array

    # --- Module B4: replacement within the study period -------------------------
    # One count and one scaling factor per part.
    DeepwellNumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    HRXNumberReplacements = (np.maximum(np.divide(RSP, HRXLifespan) - 1, 0))

    SFwell = (RSP / Lifespan)  # Scaling factor
    SFHRX = (RSP / HRXLifespan)  # Scaling factor

    # --- Module B6: operating stimulation ---------------------------------------
    # Chemical stimulation of the reservoir [m3] over the study period, scaled
    # from the reference plant. The geothermal heat itself carries no upstream
    # burden.
    Geothermal_UsePhaseStimulation = 40000 * (Power / (5500 * 6.4)) * RSP #cubic meter (This is a chemical technique for incresing the vapour flow rate)

    # --- Module C2: transport to treatment --------------------------------------
    # 50 km [t.km], once per part.
    Geothermal_DeepWell_Transport_To_Treatment_Plant = 50 * (massDeepwell/1000)
    Geothermal_HeatExchanger_Transport_To_Treatment_Plant = 50 * (massHRX/1000)

    # --- Module C3: waste processing --------------------------------------------
    Geothermal_EOL_LowAlloyedSteel = massDeepwell
    Geothermal_EOL_stainlessSteel = massHRX

    # --- Module C4: final disposal ----------------------------------------------
    # The landfilled share of each metal [kg]. Nothing is incinerated, so the D3
    # activities score zero.
    Geothermal_EOL_Landfill_LowAlloyedSteel = Geothermal_EOL_LowAlloyedSteel * LandfillMetals
    Geothermal_EOL_Landfill_StainlessSteel = Geothermal_EOL_stainlessSteel * LandfillMetals2

    # --- Module D1: credit for exported secondary materials ---------------------
    Geothermal_EOL_Recycling_LowAlloyedSteel = (RecyclingMetals * RecyclingEfficiencyMetals * Geothermal_EOL_LowAlloyedSteel) - (RecycledContentMetals * Geothermal_EOL_LowAlloyedSteel)
    Geothermal_EOL_Primary_LowAlloyedSteel = ((RecycledContentMetals * Geothermal_EOL_LowAlloyedSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * Geothermal_EOL_LowAlloyedSteel)) * SRmetals

    Geothermal_EOL_Recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * Geothermal_EOL_stainlessSteel) - (RecycledContentMetals * Geothermal_EOL_stainlessSteel)
    Geothermal_EOL_Primary_StainlessSteel = ((RecycledContentMetals * Geothermal_EOL_stainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * Geothermal_EOL_stainlessSteel)) * SRmetals

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_Geothermal = np.array([EnergyProduced * RSP])

    # Collect every quantity with the 'Geothermal' stem (all three prefixes)
    # for the exchange rows, minus the two building label columns. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("Geothermal")}
    activity_data.pop("Geothermal_BdName", None)
    activity_data.pop("Geothermal_BdArea", None)

    return {
        "activity_data": activity_data,
        # The parent's own modules are B2 (scaled by SFwell) and B6 (never
        # scaled).
        "sf": {
            "Geothermal": SFwell,
            "Geothermal_DeepWell": SFwell,
            "Geothermal_HeatExchanger": SFHRX,
        },
        # The parent's B4, D1 and D3 are the sum of the two parts'.
        "replacements": {
            "Geothermal_DeepWell": DeepwellNumberReplacements,
            "Geothermal_HeatExchanger": HRXNumberReplacements,
        },
        "bd_names": Geothermal_BdName,
        "bd_areas": Geothermal_BdArea,
        "thermal_energy": ThermalEnergyProduced_Geothermal,
    }
