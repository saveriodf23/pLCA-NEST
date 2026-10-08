"""
ecoinvent_datasets.py - the background datasets every exchange points at.

Each EF_* is a Brightway node - a dataset in the prospective ecoinvent database
(ei) or an elementary flow in the biosphere database (bio) - looked up by
name, unit and location. The lookup is exact: ei.get() raises if no dataset
matches, so a change of ecoinvent version means re-checking this file (see
background.py). The names in exchange_configs.py are the keys of what load()
returns, so the two files have to agree.

Notes on specific lookups:

  * EF_EnergyvectorHydrogen fetches photovoltaic electricity: hydrogen is
    modelled as electrolytic hydrogen from PV (see boiler.py).
  * EF_Propene fetches 'Propanol' as a proxy: the biosphere has no propene
    flow.
  * EF_Airfun is a desktop-computer power-supply fan; only the electric heat
    pump's fan uses it (see the note at the lookup).
  * EF_RefrigerantGas fetches ABS copolymer while its C3 and C4 rows treat the
    component as R134a, as in the source LCI; open question to the inventory
    authors (see the note at the lookup).
  * EF_Brass is assigned twice, identically. EF_Chromium and EF_Ethyne are
    commented out (no matching flow).
"""


def load(ei, bio):
    """Look up every background dataset once and return them by name.

    Called once per run, before any activity is built; lca_model.py resolves
    each exchange_configs.py row against the result.

    Parameters
    ----------
    ei : bw2data.Database
        The prospective ecoinvent database, from background.open_background().
    bio : bw2data.Database
        The biosphere database, from the same source.

    Returns
    -------
    dict
        {'EF_...': Brightway node}
    """

    # -----------------------------------------------------------------------
    # 2. Modules A1-3
    # A1-3  product stage: raw material supply, transport, manufacturing.
    #       Everything a unit is made of, plus the factory inputs to make it.
    # -----------------------------------------------------------------------
    EF_StainlessSteel = ei.get(name='market for steel, chromium steel 18/8, hot rolled', unit='kilogram', location='GLO')
    EF_Steel = ei.get(name='market for steel, low-alloyed, hot rolled', unit='kilogram', location='GLO')
    EF_Aluminium = ei.get(name='market for aluminium, wrought alloy', unit='kilogram', location='GLO')
    EF_Alumina = ei.get(name='market for aluminium oxide, non-metallurgical', unit='kilogram', location='RoW')
    EF_NBR = ei.get(name='market for acrylonitrile-butadiene-styrene copolymer', unit='kilogram', location='GLO')
    EF_Ferrite = ei.get(name='market for ferrite', unit='kilogram', location='GLO')
    EF_AmmoniaA13 = ei.get(name='market for ammonia, anhydrous, liquid', unit='kilogram', location='RER')
    EF_Elastomer = ei.get(name='market for synthetic rubber', unit='kilogram', location='GLO')
    EF_PVC = ei.get(name='market for polyvinyl chloride, suspension polymerised', unit='kilogram', location='RER')
    # Note: the source LCI charges the gas boiler's "refrigerant gas" as ABS
    # copolymer here and disposes of it as R134a at C3 and C4. Open question
    # to the inventory authors; the three rows must change together.
    EF_RefrigerantGas = ei.get(name='market for acrylonitrile-butadiene-styrene copolymer', unit='kilogram', location='GLO')
    EF_Copper = ei.get(name='market for copper, cathode', unit='kilogram', location='GLO')
    EF_Electronic = ei.get(name='market for electronics, for control units', unit='kilogram', location='GLO')
    EF_Welding = ei.get(name='market for brazing solder, cadmium free', unit='kilogram', location='GLO')
    EF_WaterConsumption = ei.get(name='market for tap water', unit='kilogram', location='Europe without Switzerland')
    EF_WasteWater_Treatment = ei.get(name='market for wastewater from pig iron production', unit='cubic meter', location='Europe without Switzerland')
    EF_Lubricating_Oil = ei.get(name='market for lubricating oil', unit='kilogram', location='RER')
    EF_ElectricityLV_EU = ei.get(name='market group for electricity, low voltage', unit='kilowatt hour', location='Europe without Switzerland')
    EF_ElectricityMV_EU = ei.get(name='market group for electricity, medium voltage', unit='kilowatt hour', location='Europe without Switzerland')
    EF_Heat = ei.get(name='market for heat, district or industrial, natural gas', unit='megajoule', location='Europe without Switzerland')
    EF_HeatOther = ei.get(name='market for heat, district or industrial, other than natural gas', unit='megajoule', location='Europe without Switzerland')
    EF_Hazardous = ei.get(name='market for hazardous waste, for incineration', unit='kilogram', location='Europe without Switzerland')
    EF_DustCollector = ei.get(name='market for dust collector, electrostatic precipitator, for industrial use', unit='unit', location='GLO')
    EF_Furnace = ei.get(name='market for furnace, wood chips, with silo, 5000kW', unit='unit', location='GLO')
    EF_CHP = ei.get(name='market for heat and power co-generation unit, organic Rankine cycle, 200kW electrical', unit='unit', location='GLO')
    EF_Air = ei.get(name='market for air input/output unit, heat and power co-generation unit, 160kW electrical', unit='unit', location='GLO')
    EF_Control = ei.get(name='market for control cabinet, heat and power co-generation unit, 160kW electrical', unit='unit', location='GLO')
    EF_Motor = ei.get(name='market for gas motor, 206kW', unit='unit', location='GLO')
    EF_Insulation = ei.get(name='market for sound insulation, heat and power co-generation unit, 160kW electrical', unit='unit', location='GLO')
    EF_Catalytic = ei.get(name='market for catalytic converter, three-way, 19.1l', unit='unit', location='GLO')
    EF_Electric = ei.get(name='market for electric parts, heat and power co-generation unit, 160kW electrical', unit='unit', location='GLO')
    EF_Generator = ei.get(name='market for generator, 200kW electrical', unit='unit', location='GLO')
    EF_Sanitary = ei.get(name='market for heating and sanitary equipment, heat and power co-generation unit, 160kW electrical', unit='unit', location='GLO')
    EF_SolarCollector = ei.get(name='market for solar collector system, Cu flat plate collector, one-family house, combined system', unit='unit', location='GLO')
    EF_Storage = ei.get(name='market for heat storage, 2000l', unit='unit', location='GLO')
    EF_MineralWool = ei.get(name='market for stone wool, packed', unit='kilogram', location='GLO')
    EF_Polyurethane = ei.get(name='market for polyurethane, rigid foam', unit='kilogram', location='RER')
    EF_Brass = ei.get(name='market for brass', unit='kilogram', location='CH')
    EF_Polyethylene = ei.get(name='market for polyethylene, high density, granulate', unit='kilogram', location='GLO')
    EF_Polypropylene = ei.get(name='market for polypropylene, granulate', unit='kilogram', location='GLO')
    EF_CastIron = ei.get(name='market for cast iron', unit='kilogram', location='GLO')
    EF_Ceramictile = ei.get(name='market for ceramic tile', unit='kilogram', location='GLO')
    # Flat coated glass (the glazed door of small biomass boilers), as in the LCI.
    EF_FlatGlassCoated = ei.get(name='market for flat glass, coated', unit='kilogram', location='RER')
    EF_ConcreteCH = ei.get(name='market for concrete, 25MPa', unit='cubic meter', location='CH')
    EF_ConcreteAT = ei.get(name='market for concrete, 25MPa', unit='cubic meter', location='AT')
    EF_AluminiumCast = ei.get(name='market for aluminium, cast alloy', unit='kilogram', location='GLO')
    EF_Diesel = ei.get(name='market for diesel, burned in building machine', unit='megajoule', location='GLO')
    EF_ReinforcingSteel = ei.get(name='market for reinforcing steel', unit='kilogram', location='GLO')
    # A desktop-computer power-supply fan. Only the electric heat pump's fan
    # (1.9 kg) uses it; the gas absorption heat pump's is charged as stainless
    # steel and the cooling tower's (much heavier) as steel. All three are
    # treated as steel at end of life.
    EF_Airfun = ei.get(name='market for fan, for power supply unit, desktop computer', unit='kilogram', location='GLO')
    EF_RefrigerantA13 = ei.get(name='refrigerant R134a production', unit='kilogram', location='RER')
    EF_Bentonite = ei.get(name='market for bentonite', unit='kilogram', location='GLO')
    EF_Cement = ei.get(name='market for cement, unspecified', unit='kilogram', location='Europe without Switzerland')
    EF_EthyleneGlycol = ei.get(name='market for ethylene glycol', unit='kilogram', location='RER')
    EF_IronSulfate = ei.get(name='market for iron sulfate', unit='kilogram', location='RER')
    EF_Chamotte = ei.get(name='market for clay', unit='kilogram', location='CH')
    EF_Brass = ei.get(name='market for brass', unit='kilogram', location='CH')
    EF_Heatfromoil = ei.get(name='market for heat, district or industrial, other than natural gas', unit='megajoule', location='Europe without Switzerland')
    EF_Gravel = ei.get(name='market for gravel, crushed', unit='kilogram', location='CH')
    EF_Pitch = ei.get(name='market for pitch', unit='kilogram', location='Europe without Switzerland')
    EF_Sand = ei.get(name='market for sand', unit='kilogram', location='CH')
    EF_AlkydPaint = ei.get(name='market for alkyd paint, white, without water, in 60% solution state', unit='kilogram', location='RER')
    EF_SheetRollingAluminium = ei.get(name='market for sheet rolling, aluminium', unit='kilogram', location='GLO')
    EF_SheetRollingSteel = ei.get(name='market for sheet rolling, steel', unit='kilogram', location='GLO')
    EF_Weldingarcaluminium = ei.get(name='market for welding, arc, aluminium', unit='meter', location='GLO')
    EF_Weldingarcsteel = ei.get(name='market for welding, arc, steel', unit='meter', location='GLO')
    EF_WireDrawingCopper = ei.get(name='market for wire drawing, copper', unit='kilogram', location='GLO')
    EF_WaterWater = bio.get(name='Water', categories=('water',))
    EF_WaterAir = bio.get(name='Water', categories=('air',))
    EF_Propane = bio.get(name='Propane', categories=('air',))
    EF_EthanePentafluoro = bio.get(name='Pentafluoroethane', categories=('air',))
    EF_MethaneDifluoro = bio.get(name='Difluoromethane', categories=('air',))

    # -----------------------------------------------------------------------
    # 3. Module A4
    # A4    transport of the finished unit from the factory to the building site.
    # -----------------------------------------------------------------------
    EF_Truck1632 = ei.get(name='market for transport, freight, lorry, 16-32 metric ton, diesel, EURO 5', unit='ton kilometer', location='RER')
    EF_LightTruck = ei.get(name='market for transport, freight, light commercial vehicle, fleet average', unit='ton kilometer', location='Europe without Switzerland')

    # -----------------------------------------------------------------------
    # 4. Module A5
    # A5    installation on site: excavation, backfill, assembly, commissioning.
    # -----------------------------------------------------------------------
    EF_Excavation = ei.get(name='market for transport, freight, lorry, 16-32 metric ton, diesel, EURO 5', unit='ton kilometer', location='RER')
    EF_Refillgravel = ei.get(name='market for gravel, crushed', unit='kilogram', location='CH')
    EF_Refillsand = ei.get(name='market for sand', unit='kilogram', location='CH')
    EF_Asphalt = ei.get(name='mastic asphalt production', unit='kilogram', location='CH')
    EF_Energy = ei.get(name='energy requirement for assembly of heat and power co-generation unit, 160kW electrical', unit='unit', location='RER')
    EF_Construction = ei.get(name='construction work, heat and power co-generation unit, 160kW electrical', unit='unit', location='RER')
    EF_Planning = ei.get(name='planning, heat and power co-generation unit, 160kW electrical', unit='unit', location='RER')
    EF_Startup = ei.get(name='start-up, heat and power co-generation unit, 160kW electrical', unit='unit', location='RER')
    EF_Deepwell = ei.get(name='deep well drilling, for deep geothermal power', unit='meter', location='CH')

    # -----------------------------------------------------------------------
    # 5. Module B1
    # B1    use-stage emissions from the installed product itself
    #       (water treatment consumables, refrigerant leakage).
    # -----------------------------------------------------------------------
    EF_SodiumPowder = ei.get(name='market for sodium chloride, powder', unit='kilogram', location='GLO')
    EF_RegenerationWater = ei.get(name='tap water production, conventional treatment', unit='kilogram', location='Europe without Switzerland')
    EF_ResinCationic = ei.get(name='market for cationic resin', unit='kilogram', location='RER')
    EF_EOL_Resine_Inc = ei.get(name='treatment of spent oxychlor catalyst, hazardous waste incineration', unit='kilogram', location='CH')

    # -----------------------------------------------------------------------
    # 6. Module B2
    # B2    maintenance: service trips, consumables replaced during the RSP.
    # -----------------------------------------------------------------------
    EF_LightTruck = ei.get(name='market for transport, freight, light commercial vehicle, fleet average', unit='ton kilometer', location='Europe without Switzerland')
    EF_Maintenance = ei.get(name='maintenance, heat and power co-generation unit, 160kW electrical', unit='unit', location='RER')
    EF_LubricatingOilB2 = ei.get(name='market for lubricating oil', unit='kilogram', location='RER')
    EF_Well = ei.get(name='deep well drilling, for deep geothermal power', unit='meter', location='CH')
    EF_InjectionMoulding = ei.get(name='market for injection moulding', unit='kilogram', location='GLO')

    # -----------------------------------------------------------------------
    # 7. Module B6
    # B6    operational energy use - the fuels and electricity the system
    #       consumes, and the emissions from burning them. The largest block
    #       here, and the only module not scaled by SF (see config.py).
    # -----------------------------------------------------------------------
    EF_ElectricityLV_IT = ei.get(name='market for electricity, low voltage', unit='kilowatt hour', location='IT')
    EF_ElectricityPV_CH = ei.get(name='electricity production, photovoltaic, at 93 kWp slanted-roof, single-Si, panel, mounted', unit='kilowatt hour', location='CH')
    EF_LPG = ei.get(name='market for liquefied petroleum gas', unit='kilogram', location='Europe without Switzerland')
    EF_Chemical = ei.get(name='market for chemical, organic', unit='kilogram', location='GLO')
    EF_EnergyvectorNG = ei.get(name='market for natural gas, low pressure', unit='cubic meter', location='IT')
    EF_EnergyvectorBiom = ei.get(name='market for biomethane, high pressure', unit='cubic meter', location='CH')
    EF_EnergyvectorHydrogen = ei.get(name='electricity production, photovoltaic, 570kWp open ground installation, multi-Si', unit='kilowatt hour', location='IT')
    EF_Biogas =  ei.get(name='market for biogas', unit='cubic meter', location='CH')
    EF_Chlorine = ei.get(name='market for chlorine, liquid', location='RER', unit='kilogram')
    EF_MineralOilWaste = ei.get(name='market for waste mineral oil', location='Europe without Switzerland', unit='kilogram')
    EF_Municipalsolidwaste = ei.get(name='market for municipal solid waste', location='IT', unit='kilogram')
    EF_NOx = ei.get(name='market for NOx retained, by selective catalytic reduction', location='GLO', unit='kilogram')
    EF_LubricatingOilB6 = ei.get(name='market for lubricating oil', location='RER', unit='kilogram')
    EF_Solidwaste = ei.get(name='market for municipal solid waste', location='IT', unit='kilogram')
    EF_WasteWater = ei.get(name='market for wastewater, average', location='Europe without Switzerland', unit='cubic meter')
    EF_Water = ei.get(name='market for water, decarbonised', location='CH', unit='kilogram')
    EF_WaterIn2 = ei.get(name='market for water, completely softened', location='RER', unit='kilogram')
    EF_Watercoolingtower = ei.get(name='market for residue from cooling tower', location='CH', unit='kilogram')
    EF_Wood = ei.get(name='market for wood chips, from post-consumer wood, measured as dry mass', location='RER', unit='kilogram')
    EF_Woodash = ei.get(name='market for wood ash mixture, pure', location='Europe without Switzerland', unit='kilogram')
    EF_Leakage = ei.get(name='tap water production, underground water with disinfection', location='Europe without Switzerland', unit='kilogram')
    EF_Acenaphthene = bio.get(name='Acenaphthene', categories = ('air',))
    EF_Acetaldehyde = bio.get(name='Acetaldehyde', categories = ('air',))
    EF_AceticAcid = bio.get(name='Acetic acid', categories = ('air',))
    EF_Acetone = bio.get(name='Acetone', categories = ('air',))
    EF_Acrolein = bio.get(name='Acrolein', categories = ('air',))
    EF_Benzaldehyde = bio.get(name='Benzaldehyde', categories = ('air',))
    EF_Benzene = bio.get(name='Benzene', categories = ('air',))
    EF_EthylBenzene = bio.get(name='Ethyl benzene', categories = ('air',))
    EF_Hexachlorobenzene = bio.get(name='Hexachlorobenzene', categories = ('air',))
    EF_Benzoapyrene = bio.get(name='Benzo(a)pyrene', categories = ('air',))
    EF_Beryllium = bio.get(name='Beryllium II', categories = ('air',))
    EF_Bromine = bio.get(name='Bromine', categories = ('air',))
    EF_Butane = bio.get(name='Butane', categories = ('air',))
    EF_CarbonmonoxideNonFossil = bio.get(name='Carbon monoxide, non-fossil', categories = ('air',))
    EF_CarbondioxideNonFossil = bio.get(name='Carbon dioxide, non-fossil', categories = ('air',))
    EF_CarbonmonoxideFossil = bio.get(name='Carbon monoxide, fossil', categories = ('air',))
    EF_CarbondioxideFossil = bio.get(name='Carbon dioxide, fossil', categories = ('air',))
    EF_CobaltB6 = bio.get(name='Cobalt II', categories = ('water',))
    EF_Ammonia = bio.get(name='Ammonia', categories = ('air',))
    EF_Cadmium = bio.get(name='Cadmium', categories = ('natural resource', 'in ground'))
    EF_Calcium = bio.get(name='Calcium', categories = ('natural resource', 'in ground'))
    # Chlorine emitted to air by the ORC (distinct from the purchased chlorine).
    EF_Chlorineair = bio.get(name='Chlorine', categories=('air',))
    #EF_Chromium = bio.get(name='Chromium', categories=('air',)) assente
    EF_ChromiumVI = bio.get(name='Chromium VI', categories=('air',))
    EF_CopperIon = bio.get(name='Copper ion', categories=('air',))
    EF_DinitrogenMonoxide = bio.get(name='Dinitrogen monoxide', categories=('air',))
    EF_Dioxin = bio.get(name='Dioxins, measured as 2,3,7,8-tetrachlorodibenzo-p-dioxin', categories=('air',))
    EF_Ethane = bio.get(name='Ethane', categories=('air',))
    #EF_Ethyne = bio.get(name='Ethyne', categories=('air',))
    EF_Fluorine = bio.get(name='Fluorine', categories=('air',))
    EF_Formaldehyde = bio.get(name='Formaldehyde', categories=('air',))
    EF_Hexane = bio.get(name='Hexane', categories=('air',))
    EF_HydrocarbonsUnsaturated = bio.get(name='Hydrocarbons, aliphatic, unsaturated', categories=('air',))
    EF_HydrocarbonsAlkanes = bio.get(name='Hydrocarbons, aliphatic, alkanes, unspecified', categories=('air',))
    # Hydrogen chloride is called 'Hydrochloric acid' in the biosphere.
    EF_HydrogenChloride = bio.get(name='Hydrochloric acid', categories=('air',))
    EF_HydrogenFluoride = bio.get(name='Hydrogen fluoride', categories=('air',))
    EF_LeadB6 = bio.get(name='Lead II', categories=('air',))
    EF_Magnesium = bio.get(name='Magnesium', categories=('air',))
    EF_Manganese = bio.get(name='Manganese II', categories=('air',))
    EF_Mercury = bio.get(name='Mercury II', categories=('air',))
    EF_MethaneBiogenic = bio.get(name='Methane, non-fossil', categories=('air',))
    EF_MethaneFossil = bio.get(name='Methane, fossil', categories=('air',))
    EF_EthanepentafluoroB6 = bio.get(name='Pentafluoroethane', categories=('air',))
    EF_MethanedifluoroB6 = bio.get(name='Difluoromethane', categories=('air',))
    EF_Mxylene = bio.get(name='m-Xylene', categories=('air',))
    EF_NickelB6 = bio.get(name='Nickel II', categories=('air',))
    EF_Nitrate = bio.get(name='Nitrate', categories=('air',))
    EF_Nitrite = bio.get(name='Nitrite', categories=('water',))
    EF_NitrogenH = bio.get(name='Nitrogen', categories=('air',))
    EF_NitrogenOxides = bio.get(name='Nitrogen oxides', categories=('air',))
    EF_NMVOC = bio.get(name='NMVOC, non-methane volatile organic compounds', categories=('air',))
    EF_NOXH = bio.get(name='Nitrogen oxides', categories=('air',))
    EF_OxygenH = bio.get(name='Oxygen', categories=('air',))
    EF_PAH = bio.get(name='PAH, polycyclic aromatic hydrocarbons', categories=('air',))
    EF_Particulates025 = bio.get(name='Particulate Matter, < 2.5 um', categories=('air',))
    EF_Particulates100 = bio.get(name='Particulate Matter, > 10 um', categories=('air',))
    EF_Pentane = bio.get(name='Pentane', categories=('air',))
    EF_Pentachlorophenol = bio.get(name='Pentachlorophenol', categories=('air',))
    EF_Phosphorus = bio.get(name='Phosphorus', categories=('air',))
    EF_Potassium = bio.get(name='Potassium I', categories=('air',))
    EF_PropaneB6 = bio.get(name='Propane', categories=('air',))
    EF_Propanal = bio.get(name='Propanal', categories=('air',))
    # Proxy: the biosphere has no propene flow, so the nearest three-carbon air
    # emission (propanol) is used. The quantity is small (fuel-oil boiler only).
    EF_Propene = bio.get(name='Propanol', categories=('air',))
    EF_PropionicAcid = bio.get(name='Propionic acid', categories=('air',))
    EF_Selenium = bio.get(name='Selenium IV', categories=('air',))
    EF_Sodium = bio.get(name='Sodium I', categories=('air',))
    EF_Sulfate = bio.get(name='Sulfate', categories=('air',))
    EF_Sulfite = bio.get(name='Sulfite', categories=('water',))
    EF_SulfurDioxide = bio.get(name='Sulfur dioxide', categories=('air',))
    EF_Toluene = bio.get(name='Toluene', categories=('air',))
    EF_WaterB6 = bio.get(name='Water', categories=('water',))
    EF_WaterairB6 = bio.get(name='Water', categories=('air',))
    EF_WatercondensateH = bio.get(name='Water', categories=('water',))
    EF_WatervaporH = bio.get(name='Water', categories=('air',))
    EF_Zinc = bio.get(name='Zinc II', categories=('air',))
    EF_Stimulation = ei.get(name='stimulation of deep well, for geothermal power', location='CH', unit='cubic meter')
    EF_SolidWasteTreatment = ei.get(name='market for residues, MSWI[F], municipal solid waste', location='CH', unit='kilogram')
    EF_Wind = ei.get(name='electricity production, wind, 1-3MW turbine, onshore', location = 'IT', unit = 'kilowatt hour')
    EF_Sun = ei.get(name='electricity production, photovoltaic, 570kWp open ground installation, multi-Si', location = 'IT', unit = 'kilowatt hour')
    EF_Hydro = ei.get(name='electricity production, hydro, pumped storage', location = 'IT', unit = 'kilowatt hour')

    # -----------------------------------------------------------------------
    # 8. Module C2
    # C2    transport of the discarded unit to the treatment plant.
    # -----------------------------------------------------------------------
    EF_Transport_To_Treatment_Plant = ei.get(name='market for municipal waste collection service by 21 metric ton lorry', unit='ton kilometer',location='GLO')


    # -----------------------------------------------------------------------
    # 9. Module C3
    # C3    waste processing: sorting and collection for recycling.
    # -----------------------------------------------------------------------
    EF_EOL_Metal = ei.get(name='treatment of metal scrap, mixed, for recycling, unsorted, sorting', unit='kilogram', location='Europe without Switzerland', product='iron scrap, sorted, pressed')
    EF_EOL_Aluminium = ei.get(name='treatment of aluminium scrap, post-consumer, by collecting, sorting, cleaning, pressing', unit='kilogram', location='RER')
    EF_EOL_Elastomer = ei.get(name='collection of polystyrene scrap, post-consumer', unit='kilogram', location='CH')
    EF_EOL_PVC = ei.get(name='treatment of waste polyvinylchloride product, collection for final disposal', unit='kilogram', location='Europe without Switzerland')
    # See the note at EF_RefrigerantGas (A1-3).
    EF_EOL_RefrigerantGas = ei.get(name='treatment of used refrigerant R134a, reclamation', unit='kilogram', location='GLO', product = 'used refrigerant R134a')
    EF_EOL_Inert = ei.get(name='market for inert waste, for final disposal', unit='kilogram', location='CH')
    EF_EOL_Electronics = ei.get(name='treatment of electronics scrap from control units', unit='kilogram', location='RER')
    EF_EOL_Plastic = ei.get(name='treatment of waste polyethylene/polypropylene product, collection for final disposal', unit='kilogram', location='Europe without Switzerland')
    EF_EOL_AlkydPaint = ei.get(name='treatment of waste paint on metal, sorting plant', unit='kilogram', location='CH')
    EF_EOL_Concrete = ei.get(name='treatment of waste concrete, not reinforced, sorting plant', unit='kilogram', location='Europe without Switzerland')
    EF_EOL_Cement = ei.get(name='treatment of waste cement in concrete and mortar, collection for final disposal', unit='kilogram', location='Europe without Switzerland')
    EF_EOL_ClayBrick = ei.get(name='treatment of waste brick, sorting plant', unit='kilogram', location='Europe without Switzerland')
    EF_EOL_StoneWool = ei.get(name='treatment of waste mineral wool, collection for final disposal', unit='kilogram', location='Europe without Switzerland')
    EF_EOL_Corrugatedboxboard = ei.get(name='treatment of waste paper, unsorted, sorting', unit='kilogram', location='Europe without Switzerland')
    EF_EOL_PUfoam = ei.get(name='treatment of waste polyurethane foam, collection for final disposal', unit='kilogram', location='CH') #check
    EF_EOL_PaperBoard = ei.get(name='treatment of waste paper, unsorted, sorting', unit='kilogram', location='Europe without Switzerland')

    # -----------------------------------------------------------------------
    # 10. Module C4
    # C4    final disposal: landfill and incineration.
    # -----------------------------------------------------------------------
    EF_EOL_Landfill_Metal = ei.get(name='treatment of waste steel, inert material landfill', location='Europe without Switzerland', unit='kilogram')
    EF_EOL_Landfill_Aluminium = ei.get(name='treatment of waste steel, inert material landfill', location='Europe without Switzerland', unit='kilogram')
    EF_EOL_Inc_Elastomer = ei.get(name='treatment of waste plastic, mixture, municipal incineration FAE', location='CH', unit='kilogram')
    EF_EOL_Landfill_Plastic = ei.get(name='treatment of waste plastic, mixture, sanitary landfill', location='CH', unit='kilogram')
    EF_EOL_Inc_Plastic = ei.get(name='treatment of waste plastic, mixture, municipal incineration FAE', location='CH', unit='kilogram')
    # See the note at EF_RefrigerantGas (A1-3).
    EF_EOL_Landfill_RefrigerantGas = ei.get(name='treatment of used refrigerant R134a, final disposal', location='GLO', unit='kilogram')
    EF_EOL_Inc_Electronic = ei.get(name='treatment of waste plastic, consumer electronics, municipal incineration FAE', location='CH', unit='kilogram')
    EF_EOL_Landfill_Electronic = ei.get(name='treatment of waste plastic, consumer electronics, sanitary landfill, wet infiltration class (500mm)', location='GLO', unit='kilogram')
    EF_EOL_Inc_LubricatingOil = ei.get(name='treatment of waste mineral oil, hazardous waste incineration, with energy recovery', location='Europe without Switzerland', unit='kilogram')
    EF_EOL_Inc_HazardousWaste = ei.get(name='treatment of hazardous waste, hazardous waste incineration, with energy recovery', location='Europe without Switzerland', unit='kilogram')
    EF_EOL_Landfill_Inert = ei.get(name='treatment of inert waste, inert material landfill', location='CH', unit='kilogram')
    EF_EOL_Inc_Glasswoolmat = ei.get(name='treatment of waste glass, municipal incineration FAE', location='CH', unit='kilogram')
    EF_EOL_Inc_PEHD = ei.get(name='treatment of waste polyethylene, municipal incineration FAE', location='CH', unit='kilogram')
    EF_EOL_Landfill_PEHD = ei.get(name='treatment of waste polyethylene, sanitary landfill', location='CH', unit='kilogram')
    EF_EOL_Inc_AlkydPaint = ei.get(name='treatment of waste paint, hazardous waste incineration, with energy recovery', location='Europe without Switzerland', unit='kilogram')
    EF_EOL_Landfill_Concrete = ei.get(name='treatment of waste concrete, inert material landfill', location='Europe without Switzerland', unit='kilogram')
    EF_EOL_Landfill_StoneWool = ei.get(name='treatment of waste mineral wool, inert material landfill', location='Europe without Switzerland', unit='kilogram')
    EF_EOL_Landfill_Glass = ei.get(name='treatment of waste glass, sanitary landfill', location='GLO', unit='kilogram')
    EF_EOL_Inc_PaperBoard = ei.get(name='treatment of waste paperboard, municipal incineration FAE', location='CH', unit='kilogram')
    EF_EOL_Landfill_PaperBoard = ei.get(name='treatment of waste paperboard, sanitary landfill', location='CH', unit='kilogram')
    EF_EOL_Inc_PP = ei.get(name='treatment of waste polypropylene, municipal incineration FAE', location='CH', unit='kilogram')
    EF_EOL_Landfill_PP = ei.get(name='treatment of waste polypropylene, sanitary landfill', location='CH', unit='kilogram')
    EF_EOL_Inc_Resine = ei.get(name='treatment of spent oxychlor catalyst, hazardous waste incineration', location='CH', unit='kilogram')

    # -----------------------------------------------------------------------
    # 11. Module D1 (related to the export of secondary materials)
    # D1    benefits beyond the system boundary from exported secondary
    #       materials. Each pair is a recycling route and the primary
    #       production it displaces - the credit is the difference.
    # -----------------------------------------------------------------------
    EF_Recycling_Steel = ei.get(name='treatment of waste reinforcement steel, recycling',
                                location='CH', unit='kilogram')
    EF_Primary_Steel = ei.get(name='pig iron production', location='RER', unit='kilogram')
    EF_Primary_StainlessSteel = ei.get(name='steel production, chromium steel 18/8, hot rolled',
                                       location='RER', unit='kilogram')

    EF_Recycling_Aluminium = ei.get(name='treatment of aluminium scrap, post-consumer, prepared for recycling, at remelter',
                                    location='RER', unit='kilogram')
    EF_Primary_Aluminium = ei.get(name='aluminium production, primary, liquid, prebake',
                                  location='IAI Area, EU27 & EFTA', unit='kilogram')

    EF_Recycling_Copper = ei.get(name='treatment of copper scrap by electrolytic refining', location='RER', unit='kilogram')
    EF_Primary_Copper = ei.get(name='copper production, cathode, solvent extraction and electrowinning process',
                               location='GLO', unit='kilogram', product = 'copper, cathode')

    EF_Primary_CastIron = ei.get(name='pig iron production', location='RER', unit='kilogram')

    EF_Recycling_PEHD = ei.get(name='polyethylene, high density, granulate, recycled to generic market for polyethylene, high density, granulate', location='RoW', unit='kilogram')
    EF_Primary_PEHD = ei.get(name='polyethylene production, high density, granulate', location='RER', unit='kilogram')

    EF_Recycling_ClayBrick = ei.get(name='treatment of waste brick, recycling', location='CH', unit='kilogram')
    EF_Primary_ClayBrick = ei.get(name='clay brick production, extruded', location='RER', unit='kilogram')

    EF_Recycling_Concrete = ei.get(name='treatment of waste concrete, not reinforced, recycling', location='Europe without Switzerland', unit='kilogram')
    EF_Primary_Concrete = ei.get(name='concrete production, 50MPa, with cement, Portland', location='RoW', unit='cubic meter')

    EF_Primary_Chromium =  ei.get(name='chromite ore concentrate production', location='RoW', unit='kilogram')
    EF_Primary_Cobalt =  ei.get(name='cobalt production', location='GLO', unit='kilogram', product = 'cobalt')
    EF_Primary_Nickel =  ei.get(name='ferronickel production', location='GLO', unit='kilogram')

    EF_Recycling_Cement = ei.get(name='treatment of waste concrete, not reinforced, recycling', location='Europe without Switzerland', unit='kilogram')
    EF_Recycling_Iron = ei.get(name='sorting and pressing of iron scrap', location='RER', unit='kilogram')
    EF_Primary_Lead = ei.get(name='primary lead production from concentrate', location='GLO', unit='kilogram', product = 'lead')
    EF_Primary_Platinum = ei.get(name='platinum group metal, mine and concentration operations', location='ZA', unit='kilogram')
    EF_Primary_Zinc = ei.get(name='zinc oxide production', location='RER', unit='kilogram')
    EF_Recycling_Cardboard = ei.get(name='market for waste paper, sorted', location='GLO', unit='kilogram')
    EF_Primary_Cardboard = ei.get(name='cellulose fibre production', location='CH', unit='kilogram')
    EF_Primary_Palladium = ei.get(name='palladium to generic market for metal catalyst for catalytic converter', location='GLO', unit='kilogram')
    EF_Primary_Rhodium = ei.get(name='rhodium to generic market for metal catalyst for catalytic converter', location='GLO', unit='kilogram')

    # -----------------------------------------------------------------------
    # 12. Module D3 (related to the export of energy as a result of waste incineration)
    # D3    benefits beyond the system boundary from energy recovered by
    #       incinerating the discarded unit.
    # -----------------------------------------------------------------------
    EF_Heat_EnergyRecovery = ei.get(name='market for heat, district or industrial, natural gas', location='Europe without Switzerland', unit='megajoule')
    EF_Electricity_EnergyRecovery = ei.get(name='market for electricity, high voltage', location='IT', unit='kilowatt hour')

    # Collect every 'EF_' name. locals() is bound before the comprehension,
    # which has a scope of its own.
    loc = locals()
    return {name: node for name, node in loc.items() if name.startswith("EF_")}
