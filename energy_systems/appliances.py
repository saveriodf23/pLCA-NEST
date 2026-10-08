"""
appliances.py - operating electricity of the building's appliances.

Not an energy system: the plug and lighting load of the building, carried so
that the whole-life-cycle totals can include it. It has one module, B6, and no
physical equipment - no materials, no transport, no end of life - so there is
no lifespan, no scaling factor and no replacement count (both returned as
None). It is listed under APPLIANCE_SYSTEMS in plca/config.py.
"""

import numpy as np


def compute(sc, eol):
    """Per-building appliance electricity over the study period.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'Appliances demand' worksheet.
    eol : plca.eol.EolParameters
        Unused: nothing reaches end of life.

    Returns
    -------
    dict
        activity_data, bd_names, bd_areas, and sf = replacements = None.
    """
    energysystem = sc.sheet("Appliances demand")

    RSP = sc.rsp                                    # reference study period [years]

    # DASHBOARD - VALUE INPUTS
    # Annual demands [kWh/year], split by electricity source.
    Appliances_BdName = energysystem['Building Name']
    Appliances_BdArea = energysystem['Zone net floor area [m2]']
    ElectricityGrid = energysystem['Energy input from National grid [kWh/year]']
    ElectricityPV = energysystem['Energy input from Photovoltaic system [kWh/year]']

    # --- Module B6: operating electricity ---------------------------------------
    # Electricity over the study period [kWh]. B6 is never scaled by SF.
    Appliances_UsePhaseElectricity =  ElectricityGrid * RSP
    Appliances_UsephaseelectricityPV = ElectricityPV * RSP

    # Collect every 'Appliances_' quantity for the exchange rows. locals() is
    # bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("Appliances_")}

    return {
        "activity_data": activity_data,
        "sf": None,             # no lifespan: B6 is never scaled, and there is
        "replacements": None,   # no other module to replace
        "bd_names": Appliances_BdName,
        "bd_areas": Appliances_BdArea,
    }
