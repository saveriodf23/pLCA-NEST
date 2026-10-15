# Derived from LCA4DHC (Energy_systems/CombinedHeatPower_WasteToEnergy.ipynb) -
# Copyright 2026 Kevin Autelitano and Jacopo Famiglietti, licensed under the
# Apache License 2.0 (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module,
# reviewed and corrected (see CHANGELOG.md).

"""
chp_waste_to_energy.py - life-cycle inventory of a waste-to-energy plant.

A municipal waste incinerator delivering heat and power, with natural gas as a
support fuel. The plant is sized as a fraction `x` of the ecoinvent reference
incinerator (100,000 t of waste a year): the six A1-3 materials are that
plant's bill of materials scaled by x.

Note: the heat allocation factor AFQ_WtE is set to 0, so this technology
currently contributes nothing to any result. This is deliberate; enabling it
is a modelling decision.

The building label columns are CHP_WtE_*, the inventory quantities
CHP_WasteToEnergy_*. See energy_systems/__init__.py for the conventions shared
by all modules.
"""

import numpy as np

from plca import config


def compute(sc, eol):
    """Per-building material, energy and end-of-life quantities for the plants.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open; reads the 'CHP-Waste-to-Energy'
        worksheet.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Returns
    -------
    dict
        activity_data, sf, replacements, bd_names, bd_areas and
        thermal_energy (see energy_systems/__init__.py).
    """
    energysystem = sc.sheet("CHP-Waste-to-Energy")

    # --- scenario and end-of-life parameters ----------------------------------
    # Nothing is incinerated at end of life, so there are no heating values
    # and no module D3.
    RSP = sc.rsp                                    # reference study period [years]

    LandfillInert = eol["LandfillInert"]            # share of inert material landfilled
    LandfillMetals = eol["LandfillMetals"]          # share of low-alloyed metals landfilled
    LandfillMetals2 = eol["LandfillMetals2"]        # share of special metals landfilled
    RecyclingMetals = eol["RecyclingMetals"]        # share of low-alloyed metals recycled
    RecyclingMetals2 = eol["RecyclingMetals2"]      # share of special metals recycled
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    SRmetals = eol["SRmetals"]                      # substitution ratio, secondary vs primary


    # DASHBOARD - VALUE INPUTS
    # Waste and NaturalGas [kWh/year] are the two energy inputs; Waste also sets
    # the plant size (x below). EquivalentHours [h/year] is the full-load
    # running time implied by the heat delivered.
    CHP_WtE_BdName = energysystem['Building Name']
    CHP_WtE_BdArea = energysystem['Zone net floor area [m2]']
    ElectricEnergyproduced = energysystem['Electric energy produced in a year (exported and consumed)[kWh /year]']
    ThermalEnergyproduced_primary = energysystem['Thermal energy produced in a year [kWh /year]']
    Waste = energysystem['Energy input from burning waste residue [kWh/year]']
    NaturalGas = energysystem['Energy input from natural gas [kWh/year]']
    SupplyTemperature = energysystem['Supply temperature [°C]']
    ReturnTemperature = energysystem['Return temperature [°C]']
    Power = energysystem['Thermal capacity [kW]']
    EfficiencyW = energysystem['Electrical efficiency based on LHV (between 0 and 1)']
    EfficiencyQ = energysystem['Heat efficiency based on LHV (between 0 and 1)']
    EquivalentHours = ThermalEnergyproduced_primary / Power

    # Plant size as a fraction of the reference incinerator (100,000 t of
    # waste a year); heating values in kWh per kg of waste. Lifespan is a flat
    # 40 years (a civil structure, not rated in operating hours).
    # Note: x divides by the biogenic heating value and then adds the
    # non-biogenic one as a constant; the same expression sizes
    # CHP_WasteToEnergy_Waste in B6. Open question.
    LHVbiowaste = 2.50 # kWh / kg
    LHVnonbiowaste = 3.50 #kWh / kg
    x = np.array(((Waste / LHVbiowaste + LHVnonbiowaste)) / 100000) #100000 They are the tons of waste burned by the Swiss system taken as a reference #np.ones(len(Power))
    Lifespan = 40 # years

    # ADDITIONAL CALCULATIONS
    # Energy balance over the study period, divided by the thermal efficiency
    # (heat-led plant, as the ORC).
    EfficiencyTot = EfficiencyW + EfficiencyQ
    EnergyInput = (Power * EquivalentHours * RSP) / EfficiencyQ
    TotalW = EnergyInput * EfficiencyW
    TotalQ = EnergyInput * EfficiencyQ

    # --- Multifunctionality: splitting the burden between heat and power -------
    # AFQ is the share charged to HEAT, AFW the share charged to POWER.
    #
    # Both set to zero by design (see the module docstring), so every quantity
    # below is multiplied by 0.
    AFQ_WtE = 0
    AFW_WtE = 0

    # --- Module A1-3: manufacture ---------------------------------------------
    # The reference incinerator's bill of materials [kg], scaled by x: 4,990 t
    # of cement, 35,000 t of gravel, 10,000 t of sand, 3,920 t of reinforcing
    # steel, 800 t of pitch and 80 t of chromium steel. `mass` is their sum.
    # MODULE A1-3
    CHP_WasteToEnergy_Cement = (4990000 * x) * AFQ_WtE
    CHP_WasteToEnergy_Gravel = (35000000 * x) * AFQ_WtE
    CHP_WasteToEnergy_Pitch = (800000 * x) * AFQ_WtE
    CHP_WasteToEnergy_ReinforcingSteel = (3920000 * x) * AFQ_WtE
    CHP_WasteToEnergy_Sand = (10000000 * x) * AFQ_WtE
    CHP_WasteToEnergy_ChromiumSteel = (80000 * x) * AFQ_WtE

    mass = (
        CHP_WasteToEnergy_Cement +
        CHP_WasteToEnergy_Gravel +
        CHP_WasteToEnergy_Pitch +
        CHP_WasteToEnergy_ReinforcingSteel +
        CHP_WasteToEnergy_Sand +
        CHP_WasteToEnergy_ChromiumSteel
    )

    # --- Module A4: transport to site -----------------------------------------
    # Freight [t.km]: 700 km by heavy lorry, 50 km by light lorry.
    mass = np.array(mass)
    CHP_WasteToEnergy_Truck1632 = ((500 + 200)*(mass)/1000) * AFQ_WtE
    CHP_WasteToEnergy_Light_Truck = (50*(mass)/1000) * AFQ_WtE

    # --- Module B2: maintenance transport --------------------------------------
    # 50 km per visit, one visit every two years, carrying 1% of the plant mass.
    Lifespan = np.array(Lifespan)
    CHP_WasteToEnergy_LightTruck_B2 = (50 * (Lifespan/2) * 0.01 * (mass/1000)) * AFQ_WtE

    # --- Module B4: replacement within the study period ------------------------
    WtENumberReplacements = (np.maximum(np.divide(RSP, Lifespan) - 1, 0))
    SFWtE = (RSP / Lifespan)  # Scaling factor

    # --- Support-fuel preparation for module B6 --------------------------------
    # y is the support natural-gas input over the study period [MJ]. The `k`
    # to `Gas` block is the disabled year-by-year blend split, as in
    # boiler.py; `Gas` stays at `base`.
    # Note: k = 1/39 [m3/MJ] is undocumented in the source inventory; open
    # question to the inventory authors.
    Efficiency_LHV = EfficiencyW

    # DEFAULT PARAMETERS
    LHV = 36.8
    HHV = 40.4

    Efficiency_HHV = Efficiency_LHV*(LHV/HHV)  # Efficiency based on HHV

    NaturalGas = np.array([NaturalGas])  # Energy need for 1 year kWh per year

    NaturalGas = NaturalGas.flatten()

    y = (NaturalGas * 3.6 * RSP).flatten() #* (1 + Losses)

    # REPARTITION IN THE ENERGY SOURCE
    # Costants
    k = 0.0256410256410256

    # Base terms calculations
    base = (1 / Efficiency_HHV) / (k * HHV)
    h2_term = (1 / (Efficiency_HHV * (12.7 / 0.09)))

    # conditions = [
    #     (Year == 2020),
    #     (Year == 2025),
    #     (Year == 2030),
    #     (Year == 2035),
    #     (Year == 2040),
    #     (Year == 2045),
    #     (Year == 2050),
    # ]

    # values = [
    #     base,
    #     base * 0.95 + base * 0.042 + h2_term * 0.007,
    #     base * 0.90 + base * 0.084 + h2_term * 0.014,
    #     base * 0.795 + base * 0.189 + h2_term * 0.016,
    #     base * 0.688 + base * 0.294 + h2_term * 0.018,
    #     base * 0.582 + base * 0.399 + h2_term * 0.020,
    #     base * 0 + base * 0.25 + h2_term * 0.20,
    # ]

    # Gas = np.select(conditions, values, default=np.nan)

    Gas = base

    # --- Module B6: fuel and waste throughput ----------------------------------
    # Natural gas and biomethane [m3] (weighted by the blend shares A and B),
    # hydrogen [kWh] of electrolysis electricity, and the waste rows [kg].
    # Gas-blend composition: A natural gas, B biomethane, C hydrogen
    # (config.GAS_BLEND).
    A, B, C = config.GAS_BLEND

    CHP_WasteToEnergy_EnergyVectorNG = (((1 / (Efficiency_HHV * HHV))) * y) * A * AFQ_WtE
    CHP_WasteToEnergy_EnergyVectorBiomethane = ((1 / (Efficiency_HHV * HHV)) * y) * B * AFQ_WtE
    CHP_WasteToEnergy_EnergyVectorHydrogen = ((((1 / 0.9) * (1 / 3.6)) * 120) * Gas * y) * C * AFQ_WtE #120 MJ/kg

    CHP_WasteToEnergy_Waste = np.array(((Waste / LHVbiowaste + LHVnonbiowaste)) * RSP) * AFQ_WtE

    # Note: the literal 0 keeps this row at zero even if the plant were
    # enabled; open question to the inventory authors.
    CHP_WasteToEnergy_Municipalsolidwaste = (0 * Waste * 1000 * 50) * AFQ_WtE

    # --- Module C2: transport to the treatment plant ---------------------------
    # 50 km [t.km], allocated to heat.
    CHP_WasteToEnergy_Transport_To_Treatment_Plant = 50 * (mass/1000) * AFQ_WtE

    # --- Module C3: waste processing ------------------------------------------
    # All materials are in [kg] on both sides.
    CHP_WasteToEnergy_EOL_Cement = CHP_WasteToEnergy_Cement
    CHP_WasteToEnergy_EOL_Gravel = CHP_WasteToEnergy_Gravel
    CHP_WasteToEnergy_EOL_Pitch = CHP_WasteToEnergy_Pitch
    CHP_WasteToEnergy_EOL_ReinforcingSteel = CHP_WasteToEnergy_ReinforcingSteel
    CHP_WasteToEnergy_EOL_Sand = CHP_WasteToEnergy_Sand
    CHP_WasteToEnergy_EOL_ChromiumSteel = CHP_WasteToEnergy_ChromiumSteel

    # --- Module C4: disposal ---------------------------------------------------
    # The landfilled share of each material [kg]. Nothing is incinerated.
    CHP_WasteToEnergy_EOL_Landfill_Cement = CHP_WasteToEnergy_EOL_Cement * LandfillInert
    CHP_WasteToEnergy_EOL_Landfill_Gravel = CHP_WasteToEnergy_EOL_Gravel * LandfillInert
    CHP_WasteToEnergy_EOL_Landfill_Pitch = CHP_WasteToEnergy_EOL_Pitch * LandfillInert
    CHP_WasteToEnergy_EOL_Landfill_ReinforcingSteel = CHP_WasteToEnergy_EOL_ReinforcingSteel * LandfillMetals
    CHP_WasteToEnergy_EOL_Landfill_Sand = CHP_WasteToEnergy_EOL_Sand * LandfillInert
    CHP_WasteToEnergy_EOL_Landfill_ChromiumSteel = CHP_WasteToEnergy_EOL_ChromiumSteel * LandfillMetals2

    # --- Module D1: recycling credits and primary-production burdens ------------
    # Only the two steels are credited.
    CHP_WasteToEnergy_EOL_Recycling_ReinforcingSteel = (RecyclingMetals * RecyclingEfficiencyMetals * CHP_WasteToEnergy_EOL_ReinforcingSteel) - (RecycledContentMetals * CHP_WasteToEnergy_EOL_ReinforcingSteel)
    CHP_WasteToEnergy_EOL_Primary_ReinforcingSteel = ((RecycledContentMetals * CHP_WasteToEnergy_EOL_ReinforcingSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * CHP_WasteToEnergy_EOL_ReinforcingSteel))* SRmetals

    CHP_WasteToEnergy_EOL_Recycling_ChromiumSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_WasteToEnergy_EOL_ChromiumSteel) - (RecycledContentMetals * CHP_WasteToEnergy_EOL_ChromiumSteel)
    CHP_WasteToEnergy_EOL_Primary_ChromiumSteel = ((RecycledContentMetals * CHP_WasteToEnergy_EOL_ChromiumSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * CHP_WasteToEnergy_EOL_ChromiumSteel))* SRmetals

    # Data for export (informative only, see energy_systems/__init__.py).
    ThermalEnergyProduced_WtE = np.array([TotalQ])

    # Collect every 'CHP_WasteToEnergy_' quantity for the exchange rows.
    # locals() is bound before the comprehension, which has a scope of its own.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith("CHP_WasteToEnergy_")}

    return {
        "activity_data": activity_data,
        "sf": SFWtE,
        "replacements": WtENumberReplacements,
        "bd_names": CHP_WtE_BdName,
        "bd_areas": CHP_WtE_BdArea,
        "thermal_energy": ThermalEnergyProduced_WtE,
    }
