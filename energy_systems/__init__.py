"""Life-cycle inventories of the 22 energy technologies, one module each.

Every module exposes the same function::

    compute(sc, eol) -> dict

where `sc` is a plca.scenario.Scenario (the input workbook, already open) and
`eol` a plca.eol.EolParameters. The returned dict contains:

    activity_data  {name: per-building array} - the quantities the exchanges use
    sf             scaling factor RSP / Lifespan, per building
    replacements   number of replacements within the RSP, per building
    bd_names       building names, in the order the arrays are indexed
    bd_areas       zone net floor areas [m2], for the 1/area functional unit

Most modules also return `thermal_energy`, which is currently not used
downstream. Its definition is not consistent across modules (some give the
energy over the study period, others over one year), so treat it as
informative only.

Two systems depart from that shape:

  appliances.py  returns sf = None and replacements = None. It has one module,
                 B6, which is never scaled by SF, and no equipment to replace.
  geothermal.py  returns sf and replacements as dicts keyed by registry system
                 name: the 50-year deep well and the 15-year heat exchanger are
                 scaled and replaced separately, then summed into the parent
                 `Geothermal`. `replacements` has only the two parts - the
                 parent's B4 is their sum.

Callers should therefore test for None and for dict, not assume an array.

Which module each config.SYSTEMS entry uses is recorded in plca/config.py.

Common conventions in every module:

- Quantities are per-building arrays, indexed like the technology's worksheet.
- Variable names starting with the technology prefix (e.g. 'Boiler_') are the
  ones the exchange rows in plca/exchange_configs.py look up; each quantity is
  in the unit of the dataset it is wired to.
- NumberReplacements = max(RSP / Lifespan - 1, 0) (pro-rated) and
  SF = RSP / Lifespan.
- Module D1 credits follow EN 15804: recovered secondary material minus the
  recycled content already in the product, times the substitution ratio for
  the displaced primary production.
- Module D3 credits are mass incinerated x lower heating value x recovery
  efficiency, negative, as heat [MJ] and electricity [kWh].
"""
