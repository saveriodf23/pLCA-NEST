"""
auxiliaries.py - life-cycle inventory of the district network.

The distribution pipes, valves and substation heat exchanger that connect a
generation plant to the buildings, in three sections.

This system is disabled: plca/config.py lists Auxiliaries in DISABLED_SYSTEMS,
it has no exchange rows in plca/exchange_configs.py, and ten of its inputs (the
network's length, pipe technology, terminal type, users served and
primary-circuit temperatures) have no worksheet yet. compute() therefore raises
NotImplementedError naming them. The code below the guard is kept so that
enabling the system needs only a worksheet, the unpacking of those inputs and
the exchange rows.

Known issues to fix before enabling it: the activity_data filter misses the
valves_* and HeatExchanger_* quantities; the D3 electricity credit is not
divided by config.MJ_PER_KWH; and SF uses ReqSL (an input with no source)
while the replacements use the component lifespans.
"""

import numpy as np


def compute(sc, eol):
    """Per-network quantities for the pipes, valves and substation exchanger.

    Parameters
    ----------
    sc : plca.scenario.Scenario
        Input workbook, already open.
    eol : plca.eol.EolParameters
        End-of-life shares and heating values.

    Raises
    ------
    NotImplementedError
        Always, until the network inputs have a source (see the module
        docstring).
    """
    raise NotImplementedError(
        "Auxiliaries is disabled: the district-network inputs have no source yet. "
        "Missing: " + ", ".join(['Diameter', 'PipeTechnology', 'TerminalTypology', 'TotalLenght', 'TotalEnergyErogated', 'NumberUsersHeat', 'NumberUsersACS', 'SupplyTemperaturePrimaryCircuit', 'ReturnTemperaturePrimaryCircuit', 'ReqSL']) + ". "
        "Add a worksheet for the network and unpack them here, then remove "
        "'Auxiliaries' from config.DISABLED_SYSTEMS and add its exchange rows."
    )

    # --- scenario and end-of-life parameters (unreachable while disabled) ------
    RSP = sc.rsp                                    # reference study period [years]
    generatorsConfig = sc.generators_config         # read by the else branch below

    IncinerationPEHD = eol["IncinerationPEHD"]
    IncinerationPP = eol["IncinerationPP"]
    IncinerationPUfoam = eol["IncinerationPUfoam"]
    LandfillBrass = eol["LandfillBrass"]
    LandfillMetals = eol["LandfillMetals"]
    LandfillMetals2 = eol["LandfillMetals2"]
    LandfillMineralWool = eol["LandfillMineralWool"]
    LandfillPEHD = eol["LandfillPEHD"]
    LandfillPP = eol["LandfillPP"]
    LandfillPUfoam = eol["LandfillPUfoam"]
    RecyclingMetals = eol["RecyclingMetals"]
    RecyclingMetals2 = eol["RecyclingMetals2"]
    RecyclingPEHD = eol["RecyclingPEHD"]
    RecyclingEfficiencyMetals = eol["RecyclingEfficiencyMetals"]
    RecyclingEfficiencyPlastics = eol["RecyclingEfficiencyPlastics"]
    RecycledContentMetals = eol["RecycledContentMetals"]
    RecycledContentPlastic = eol["RecycledContentPlastic"]
    SRmetals = eol["SRmetals"]
    SRinert = eol["SRinert"]
    LHVHDPE = eol["LHVHDPE"]
    LHVPEfoam = eol["LHVPEfoam"]
    LHVPP = eol["LHVPP"]
    LHVPUfoam = eol["LHVPUfoam"]
    Xincheat = eol["Xincheat"]
    Xincele = eol["Xincele"]

    LifespanPipes = 30 #years

    # --- Section 2.1: choosing the pipe diameter -------------------------------
    # If the user asked for 'Default', size the network by total cost: for each
    # nominal diameter DN, price the pipe itself (a quadratic cost curve,
    # annuitised at `income`) and the pumping energy over a year, then take the
    # DN where their sum is least. Otherwise read the diameter from the
    # generatorsConfig sheet.
    #
    # Units: averageEnergyErogated [kWh/year per user], volumeflowrate [l/s]
    # (4.18 is the specific heat of water in kJ/kg.K), PipePrice [EUR], Efd
    # [kWh/year] with 0.60 the pump efficiency and 10 m an assumed head,
    # EnergyCost [EUR] at 0.12 EUR/kWh.
    # input data parameters
    if Diameter == 'Default':
        averageEnergyErogated = TotalEnergyErogated  / (NumberUsersHeat + NumberUsersACS)
        volumeflowrate = ((averageEnergyErogated * 1000) /(8760 * 4.18 * (SupplyTemperaturePrimaryCircuit - ReturnTemperaturePrimaryCircuit))) * 3600 # l/s 4.18 is the water cp in kj/kg°C
        a = 0.000652
        b = 0.231994
        c = 264.234
        income = (1/50) * 0.05 + 0.04
        DN = np.array([80, 100, 150, 200, 250, 300, 350, 400, 450, 500, 600])
        PipePrice = (((a * DN**2 + b * DN + c) / 1.5) * TotalLenght) * income #[euro]
        Yfd = TotalLenght * ((10.675 * (averageEnergyErogated / 1000)**11.852) * ((DN/1000)**14.871))
        Efd = ((9.81 * averageEnergyErogated / 1000)/ 0.60) * (10 + Yfd) * 8760 #0.60 rendimento pompa e 10 valore di prevalenza arbitrario
        EnergyCost = Efd * 0.12 #0.12 is the energy cost in EUR/kWh
        TotalCost = EnergyCost + PipePrice
        # Link every DN to each total cost
        DN_TotalCost = list(zip(DN, TotalCost))

        # minimum index of total costs
        min_index = np.argmin(TotalCost)

        # correponding DN
        DNmin = DN[min_index]
        Diameter = DNmin

    else:
        DNmin = generatorsConfig.loc[generatorsConfig['Information'] == '(Automatic cell)', 'Data'].values[0]
    if PipeTechnology == 'Steel - rockwool - stainless steel':
        pipe_steel = ((0.005 * (DNmin / 225)** 2) * 3.14) * TotalLenght * 7580  #((0.00002 * DNmin + 0.0012)**2 * TotalLenght * 3.14) * 7580
        pipe_stonewool = ((0.07 * (DNmin / 225)** 2) * 3.14) * TotalLenght * 30 # ((0.0002 * DNmin + 0.0165)**2 * TotalLenght * 3.14) * 30
        pipe_stainlessSteel = ((0.002 * (DNmin / 225)** 2) * 3.14) * TotalLenght * 7580
        pipe_PUfoam = 0
        pipe_PEfoam = 0
        pipe_PEHD1 = 0
        pipe_PEHD2 = 0
        pipe_PP = 0

        mass = pipe_steel + pipe_stonewool + pipe_stainlessSteel + pipe_PUfoam + pipe_PEfoam + pipe_PEHD1 + pipe_PEHD2 + pipe_PP

    elif PipeTechnology == 'Steel - PU foam - PEHD':
        pipe_steel = ((0.004 * (DNmin / 225)** 2) * 3.14) * TotalLenght * 7850
        pipe_PUfoam = ((0.082 * (DNmin / 225)** 2) * 3.14) * TotalLenght * 35
        pipe_PEHD1 = ((0.004 * (DNmin / 225)** 2) * 3.14) * TotalLenght * 25
        pipe_stonewool = 0
        pipe_stainlessSteel = 0
        pipe_PEfoam = 0
        pipe_PEHD2 = 0
        pipe_PP = 0

        mass = pipe_steel + pipe_stonewool + pipe_stainlessSteel + pipe_PUfoam + pipe_PEfoam + pipe_PEHD1 + pipe_PEHD2 + pipe_PP

    elif PipeTechnology == 'PE - PEfoam - PEHD':
        pipe_PEHD1 = ((0.0296 * (DNmin / 220.4)** 2) * 3.14) * TotalLenght * 960
        pipe_PEfoam = ((0.1105 * (DNmin / 220.4)** 2) * 3.14) * TotalLenght * 910
        pipe_PEHD2 = ((0.008 * (DNmin / 220.4)** 2) * 3.14) * TotalLenght * 950
        pipe_steel = 0
        pipe_stainlessSteel = 0
        pipe_stonewool = 0
        pipe_PP = 0
        pipe_PUfoam = 0

        mass = pipe_steel + pipe_stonewool + pipe_stainlessSteel + pipe_PUfoam + pipe_PEfoam + pipe_PEHD1 + pipe_PEHD2 + pipe_PP

    elif PipeTechnology == 'PEHD - PU foam - PEHD':
        pipe_PEHD1 = ((0.0297 * (DNmin / 220.3)** 2) * 3.14) * TotalLenght * 950
        pipe_PUfoam = ((0.0971 * (DNmin / 220.3)** 2) * 3.14) * TotalLenght * 35
        pipe_PEHD2 = ((0.0079 * (DNmin / 220.3)** 2) * 3.14) * TotalLenght * 950
        pipe_steel = 0
        pipe_stainlessSteel = 0
        pipe_stonewool = 0
        pipe_PP = 0
        pipe_PEfoam = 0
        mass = pipe_steel + pipe_stonewool + pipe_stainlessSteel + pipe_PUfoam + pipe_PEfoam + pipe_PEHD1 + pipe_PEHD2 + pipe_PP

    elif PipeTechnology == 'PP - PU foam - PVC':
        pipe_PP = ((0.030 * (DNmin / 220)** 2) * 3.14) * TotalLenght * 950
        pipe_PUfoam = ((0.093 * (DNmin / 220)** 2) * 3.14) * TotalLenght * 35
        pipe_PEHD1 = ((0.0095 * (DNmin / 220)** 2) * 3.14) * TotalLenght * 950
        pipe_steel = 0
        pipe_stainlessSteel = 0
        pipe_stonewool = 0
        pipe_PEHD2 = 0
        pipe_PEfoam = 0
        mass = pipe_steel + pipe_stonewool + pipe_stainlessSteel + pipe_PUfoam + pipe_PEfoam + pipe_PEHD1 + pipe_PEHD2 + pipe_PP

    else:
        print("Index out of range")
    pipe_steel = np.array([pipe_steel])
    pipe_stonewool = np.array([pipe_stonewool])
    pipe_stainlessSteel = np.array([pipe_stainlessSteel])
    pipe_PUfoam = np.array([pipe_PUfoam])
    pipe_PEfoam = np.array([pipe_PEfoam])
    pipe_PEHD1 = np.array([pipe_PEHD1])
    pipe_PEHD2 = np.array([pipe_PEHD2])
    pipe_PP = np.array([pipe_PP])
    mass = np.array([mass])
    pipe_Truk_16_32 = ((10000)*(mass)/1000)
    pipe_Light_Truk = (100 * (mass)/1000)
    if PipeTechnology == 'Steel - rockwool - stainless steel':
        pipe_excavation = ((653 * 10) / 100) * TotalLenght
        pipe_refillingGravel = ((192000 * 10) / 100) * TotalLenght
        pipe_refillingSand = ((366000 * 10) / 100) * TotalLenght
        pipe_asphalt = ((221 * 10) / 100) * TotalLenght

    elif PipeTechnology == 'Steel - PU foam - PEHD':
        pipe_excavation = ((630 * 10) / 100) * TotalLenght
        pipe_refillingGravel = ((185000 * 10) / 100) * TotalLenght
        pipe_refillingSand = ((353000 * 10) / 100) * TotalLenght
        pipe_asphalt = ((216 * 10) / 100) * TotalLenght

    elif PipeTechnology == 'PE - PEfoam - PEHD':
        pipe_excavation = ((735 * 10) / 100) * TotalLenght
        pipe_refillingGravel = ((218000 * 10) / 100) * TotalLenght
        pipe_refillingSand = ((415000 * 10) / 100) * TotalLenght
        pipe_asphalt = ((237 * 10) / 100) * TotalLenght


    elif PipeTechnology == 'PEHD - PU foam - PEHD':
        pipe_excavation = ((707 * 10) / 100) * TotalLenght
        pipe_refillingGravel = ((209000 * 10) / 100) * TotalLenght
        pipe_refillingSand = ((398000 * 10) / 100) * TotalLenght
        pipe_asphalt = ((232 * 10) / 100) * TotalLenght

    elif PipeTechnology == 'PP - PU foam - PVC':
        pipe_excavation = ((702 * 10) / 100) * TotalLenght
        pipe_refillingGravel = ((208000 * 10) / 100) * TotalLenght
        pipe_refillingSand = ((395000 * 10) / 100) * TotalLenght
        pipe_asphalt = ((231 * 10) / 100) * TotalLenght

    else:
        print("Index out of range")

    pipe_excavation = np.array([pipe_excavation])
    pipe_refillingGravel = np.array([pipe_refillingGravel])
    pipe_refillingSand = np.array([pipe_refillingSand])
    pipe_asphalt = np.array([pipe_asphalt])
    pipe_Light_Truk_B2 = 50 * (LifespanPipes/2) * 0.01 * (mass/1000)

    VolumeFlowRate = volumeflowrate / 1000

    pipe_electricity = 0.02 * VolumeFlowRate#kWh
    pipe_sodiumPowder = 0.5 * VolumeFlowRate #kg
    pipe_regenerationWater = 0.5 * VolumeFlowRate #m3
    pipe_resineIon = 0.00011 * VolumeFlowRate #kg
    pipe_effluent = pipe_regenerationWater
    pipe_saltTruk_16_32 =  ((10000)*(pipe_sodiumPowder)/1000)
    pipe_saltLight_Truk =  ((10000)*(pipe_sodiumPowder)/1000)
    pipe_EOL_resine_inc = pipe_resineIon
    PipesNumberReplacements = (np.maximum(np.divide(RSP, LifespanPipes) - 1, 0))
    SFPipes = (RSP / ReqSL)  # Scaling factor
    pipe_leakage = 0.02 * ((averageEnergyErogated * 1000) /(8760 * 4.18 * (SupplyTemperaturePrimaryCircuit - ReturnTemperaturePrimaryCircuit))) * 3600
    pipe_leakage = np.array([pipe_leakage])
    pipe_electricity = 0.05
    pipe_Transport_to_treatment_plant = (50 * (mass/1000))
    pipe_EOL_steel = pipe_steel
    pipe_EOL_stonewool = pipe_stonewool
    pipe_EOL_stainlessSteel = pipe_stainlessSteel
    pipe_EOL_PUfoam = pipe_PUfoam
    pipe_EOL_PEHD1 = pipe_PEHD1
    pipe_EOL_PEHD2 = pipe_PEHD2
    pipe_EOL_PEfoam = pipe_PEfoam
    pipe_EOL_PP = pipe_PP
    pipe_EOL_landfill_steel = pipe_EOL_steel * LandfillMetals
    pipe_EOL_landfill_stonewool = pipe_EOL_stonewool * LandfillMineralWool
    pipe_EOL_landfill_StainlessSteel = pipe_EOL_stainlessSteel * LandfillMetals2
    pipe_EOL_inc_PUfoam = pipe_EOL_PUfoam * IncinerationPUfoam
    pipe_EOL_landfill_PUfoam = pipe_EOL_PUfoam * LandfillPUfoam
    pipe_EOL_inc_PEHD1 = pipe_EOL_PEHD1 * IncinerationPEHD
    pipe_EOL_landfill_PEHD1 = pipe_EOL_PEHD1 * LandfillPEHD
    pipe_EOL_inc_PEfoam = pipe_EOL_PEfoam * IncinerationPEHD
    pipe_EOL_landfill_PEfoam = pipe_EOL_PEfoam * LandfillPEHD
    pipe_EOL_inc_PEHD2 = pipe_EOL_PEHD2 * IncinerationPEHD
    pipe_EOL_landfill_PEHD2 = pipe_EOL_PEHD2 * LandfillPEHD
    pipe_EOL_inc_PP = pipe_EOL_PP * IncinerationPP
    pipe_EOL_landfill_PP = pipe_EOL_PP * LandfillPP
    pipe_EOL_recycling_steel = (RecyclingMetals * RecyclingEfficiencyMetals * pipe_EOL_steel) - (RecycledContentMetals * pipe_EOL_steel)
    pipe_EOL_primary_steel = ((RecycledContentMetals * pipe_EOL_steel) - (RecyclingMetals * RecyclingEfficiencyMetals * pipe_EOL_steel))* SRmetals

    pipe_EOL_recycling_StainlessSteel = (RecyclingMetals2 * RecyclingEfficiencyMetals * pipe_EOL_stainlessSteel) - (RecycledContentMetals * pipe_EOL_stainlessSteel)
    pipe_EOL_primary_StainlessSteel = ((RecycledContentMetals * pipe_EOL_stainlessSteel) - (RecyclingMetals2 * RecyclingEfficiencyMetals * pipe_EOL_stainlessSteel))* SRmetals

    pipe_EOL_recycling_PEHD1 = (RecyclingPEHD * RecyclingEfficiencyPlastics * pipe_EOL_PEHD1) - (RecycledContentPlastic * pipe_EOL_PEHD1)
    pipe_EOL_primary_PEHD1 = ((RecycledContentPlastic * pipe_EOL_PEHD1) - (RecyclingPEHD * RecyclingEfficiencyPlastics * pipe_EOL_PEHD1))* SRinert

    pipe_EOL_recycling_PEfoam = (RecyclingPEHD * RecyclingEfficiencyPlastics * pipe_EOL_PEfoam) - (RecycledContentPlastic * pipe_EOL_PEfoam)
    pipe_EOL_primary_PEfoam = ((RecycledContentPlastic * pipe_EOL_PEfoam) - (RecyclingPEHD * RecyclingEfficiencyPlastics * pipe_EOL_PEfoam))* SRinert

    pipe_EOL_recycling_PEHD2 = (RecyclingPEHD * RecyclingEfficiencyPlastics * pipe_EOL_PEHD2) - (RecycledContentPlastic * pipe_EOL_PEHD2)
    pipe_EOL_primary_PEHD2 = ((RecycledContentPlastic * pipe_EOL_PEHD2) - (RecyclingPEHD * RecyclingEfficiencyPlastics * pipe_EOL_PEHD2))* SRinert
    pipe_EOL_energyrecoveryheat_PUfoam = (- pipe_EOL_inc_PUfoam * LHVPUfoam) * Xincheat
    pipe_EOL_energyrecoveryele_PUfoam = (- pipe_EOL_inc_PUfoam * LHVPUfoam) * Xincele

    pipe_EOL_energyrecoveryheat_PEHD1 = (- pipe_EOL_inc_PEHD1 * LHVHDPE) * Xincheat
    pipe_EOL_energyrecoveryele_PEHD1 = (- pipe_EOL_inc_PEHD1 * LHVHDPE) * Xincele

    pipe_EOL_energyrecoveryheat_PEfoam = (- pipe_EOL_inc_PEfoam * LHVPEfoam) * Xincheat
    pipe_EOL_energyrecoveryele_PEfoam = (- pipe_EOL_inc_PEfoam * LHVPEfoam) * Xincele

    pipe_EOL_energyrecoveryheat_PEHD2 = (- pipe_EOL_inc_PEHD2 * LHVHDPE) * Xincheat
    pipe_EOL_energyrecoveryele_PEHD2 = (- pipe_EOL_inc_PEHD2 * LHVHDPE) * Xincele

    pipe_EOL_energyrecoveryheat_PP = (- pipe_EOL_inc_PP * LHVPP) * Xincheat
    pipe_EOL_energyrecoveryele_PP = (- pipe_EOL_inc_PP * LHVPP) * Xincele
    LifespanValves = 15 #years
    averageEnergyErogated = TotalEnergyErogated  / (NumberUsersHeat + NumberUsersACS)
    volumeflowrateValve = (((averageEnergyErogated * 1000) /(1000 * 4.18 * (SupplyTemperaturePrimaryCircuit - ReturnTemperaturePrimaryCircuit)))) * 3600 # l/s 4.18 water cp in kj/kg°C
    DiameterValve = np.sqrt(4 * (volumeflowrateValve / 1000) / 3.14 * 2)
    NumberValves = 2 + ((NumberUsersHeat + NumberUsersACS) * 3) #motorized valve included

    mass = (64 * (DiameterValve / 100) ) * NumberValves #the overall mass of all the valves in the circuit
    valves_brass = mass
    valves_brass = np.array([valves_brass])
    mass = np.array([mass])
    valves_Truk_16_32 = ((500 + 200)*(mass)/1000)
    valves_Light_Truk = (50*(mass)/1000)
    valves_Light_Truk_B2 = 50 * (LifespanValves/2) * 0.01 * (mass/1000)
    ValvesNumberReplacements = (np.maximum(np.divide(RSP, LifespanValves) - 1, 0))
    SFValves = (RSP / ReqSL)  # Scaling factor
    valves_Transport_to_treatment_plant = 50 * (mass/1000)
    valves_EOL_brass = valves_brass
    valves_EOL_landfill_brass = valves_EOL_brass * LandfillBrass
    valves_EOL_recycling_brass = (RecyclingMetals * RecyclingEfficiencyMetals * valves_EOL_brass) - (RecycledContentMetals * valves_EOL_brass)
    valves_EOL_primary_brass = ((RecycledContentMetals * valves_EOL_brass) - (RecyclingMetals * RecyclingEfficiencyMetals * valves_EOL_brass))* SRmetals
    LifespanHeatExchanger = 15
    averageEnergyErogated = TotalEnergyErogated  / (NumberUsersHeat + NumberUsersACS)
    massflowrate = 1000 * (((averageEnergyErogated * 1000) /(1000 * 4.18 * (SupplyTemperaturePrimaryCircuit - ReturnTemperaturePrimaryCircuit)))) * 3600 # l/s 4.18 is the water cp in kj/kg°C
    Lifespan = LifespanHeatExchanger

    if TerminalTypology == 'High temperature terminals':
        SupplyTemperatureBuilding = 65 #°C
        ReturnTemperatureBuilding = SupplyTemperatureBuilding - 10
    elif TerminalTypology == 'Average temperature terminals':
        SupplyTemperatureBuilding = 45 #°C
        ReturnTemperatureBuilding = SupplyTemperatureBuilding - 10
    elif TerminalTypology == 'Low temperature terminals':
        SupplyTemperatureBuilding = 30 #°C
        ReturnTemperatureBuilding = SupplyTemperatureBuilding - 5
    else:
        print("Index out of range")

    # DIMENSIONING OF THE HEAT EXCHANGER IN THE SUBSTATION (LMTD method since there are the 4 temperatures)
    deltaT1 = ReturnTemperaturePrimaryCircuit - ReturnTemperatureBuilding
    deltaT2 = SupplyTemperaturePrimaryCircuit - SupplyTemperatureBuilding

    LMTD = (deltaT1 - deltaT2) / np.log(deltaT1 / deltaT2)
    P =  (SupplyTemperatureBuilding - ReturnTemperatureBuilding) / (SupplyTemperaturePrimaryCircuit - ReturnTemperaturePrimaryCircuit)
    F = (np.sqrt(1 + P**2) - 1) / P #correction Factor
    U = 485 #Primary data
    a = 0.2
    b = 1.65
    ExchangeArea = averageEnergyErogated / U * LMTD * F
    mass = (a * b * ExchangeArea * 7860) / (2 * (a + b))
    HeatExchanger_stainlessSteel = mass
    HeatExchanger_stainlessSteel = np.array([HeatExchanger_stainlessSteel])
    mass = np.array([mass])
    HeatExchanger_Truk_16_32 = ((500 + 200)*(mass)/1000)
    HeatExchanger_Light_Truk = (50*(mass)/1000)
    HeatExchanger_Light_Truk_B2 = 50 * (Lifespan/2) * 0.01 * (mass/1000)
    HeatExchangerNumberReplacements = (np.maximum(np.divide(RSP, LifespanHeatExchanger) - 1, 0))
    SFHeatExchanger = (RSP / ReqSL)  # Scaling factor
    HeatExchanger_Transport_to_treatment_plant = 50 * (mass/1000)
    HeatExchanger_EOL_stainlessSteel = HeatExchanger_stainlessSteel
    HeatExchanger_EOL_landfill_stainlessSteel = HeatExchanger_EOL_stainlessSteel * LandfillMetals2
    HeatExchanger_EOL_recycling_stainlessSteel = (RecyclingMetals * RecyclingEfficiencyMetals * HeatExchanger_EOL_stainlessSteel) - (RecycledContentMetals * HeatExchanger_EOL_stainlessSteel)
    HeatExchanger_EOL_primary_stainlessSteel = ((RecycledContentMetals * HeatExchanger_EOL_stainlessSteel) - (RecyclingMetals * RecyclingEfficiencyMetals * HeatExchanger_EOL_stainlessSteel))* SRmetals

    # Collect the quantities for the exchange rows. The prefixes are provisional:
    # when the system is wired up, this filter must match the names used in
    # exchange_configs.py.
    loc = locals()
    activity_data = {name: value for name, value in loc.items()
                     if name.startswith(("pipe_", "Pipe_", "valve_", "Valve_",
                                         "HRX_", "Auxiliaries_"))}

    return {
        "activity_data": activity_data,
        "sf": SFPipes,
        "replacements": PipesNumberReplacements,
        "bd_names": None,       # the network is not per-building: it is one
        "bd_areas": None,       # object serving the whole neighbourhood
    }
