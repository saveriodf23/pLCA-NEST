# Derived from LCA4DHC (Libraries.ipynb) - Copyright 2026 Kevin Autelitano and
# Jacopo Famiglietti, licensed under the Apache License 2.0
# (https://github.com/KevinAutelitano/LCA4DHC - Citation:
# https://doi.org/10.5281/zenodo.18302949).
# Modified for pLCA-NEST: ported from a Jupyter notebook to a Python module;
# input validation added.

"""
eol.py - end-of-life parameters, loaded once from EndOfLifeInputParameters.xlsx.

These 64 values describe what happens to each material when a unit is scrapped:
how much is landfilled, incinerated or recycled, how efficient that recycling
is, how much recycled content the material already had, and how much energy is
recovered from what is burned. They are the same for every technology, so they
are read once and passed to each energy-system module.

Values are looked up by their exact 'Parameter' string in the workbook - note
the double space in 'Share of metals  (e.g low-alloyed steel) sent to
landfill', which is present in the file.
"""

import pandas as pd

SHEET = "EndOfLifeInputParameters"

# variable name -> the exact 'Parameter' cell it is read from.
PARAMETERS = {
    # --- share of each material sent to landfill -----------------------------
    "LandfillMetals2": "Share of special metals (e.g. stainless steel, chromium steel) sent to landfill at end of life",
    "LandfillMetals": "Share of metals  (e.g low-alloyed steel) sent to landfill at end of life",
    "LandfillElastomer": "Share of elastomers sent to landfill at end of life",
    "LandfillPVC": "Share of PVC sent to landfill at end of life",
    "LandfillPEHD": "Share of high-density polyethylene (HDPE) sent to landfill at end of life",
    "LandfillRefrigerant": "Share of refrigerant gases sent to landfill at end of life",
    "LandfillElectronics": "Share of electronic waste sent to landfill at end of life",
    "LandfillClaybrick": "Share of clay bricks sent to landfill at end of life",
    "LandfillConcrete": "Share of concrete sent to landfill at end of life",
    "LandfillGlass": "Share of glass sent to landfill at end of life",
    "LandfillMineralWool": "Share of mineral wool sent to landfill at end of life",
    "LandfillBrass": "Share of brass sent to landfill at end of life",
    "LandfillCardboard": "Share of cardboard sent to landfill at end of life",
    "LandfillInert": "Share of inert materials sent to landfill at end of life",
    "LandfillPUfoam": "Share of polyurethane foam sent to landfill at end of life",
    "LandfillPP": "Share of polypropylene (PP) sent to landfill at end of life",

    # --- share of each material sent to incineration -------------------------
    "IncinerationElastomer": "Share of elastomers sent to incineration at end of life",
    "IncinerationPVC": "Share of PVC sent to incineration at end of life",
    "IncinerationElectronics": "Share of electronic waste sent to incineration at end of life",
    "IncinerationLubricatingOil": "Share of lubricating oil sent to incineration at end of life",
    "IncinerationHazardous": "Share of hazardous waste sent to incineration at end of life",
    "IncinerationPEHD": "Share of high-density polyethylene (HDPE) sent to incineration at end of life",
    "IncinerationPEfoam": "Share of polyethylene foam sent to incineration at end of life",
    "IncinerationPP": "Share of polypropylene (PP) sent to incineration at end of life",
    "IncinerationEPS": "Share of expanded polystyrene (EPS) sent to incineration at end of life",
    "IncinerationCardboard": "Share of cardboard sent to incineration at end of life",
    "IncinerationPUfoam": "Share of polyurethane foam sent to incineration at end of life",

    # --- share of each material sent to recycling ----------------------------
    "RecyclingMetals2": "Share of special metals (e.g. stainless steel, chromium steel) sent to recycling at end of life",
    "RecyclingMetals": "Share of metals (e.g low-alloyed steel) sent to recycling at end of life",
    "RecyclingPEHD": "Share of high-density polyethylene (HDPE) sent to recycling at end of life",
    "RecyclingConcrete": "Share of concrete sent to recycling at end of life",
    "RecyclingClaybrick": "Share of clay bricks sent to recycling at end of life",
    "RecyclingCardboard": "Share of cardboard sent to recycling at end of life",

    # --- how much usable material a recycling process actually yields --------
    "RecyclingEfficiencyMetals": "Recycling efficiency of metals",
    "RecyclingEfficiencyPlastics": "Recycling efficiency of plastics",
    "RecyclingEfficiencyConcrete": "Recycling efficiency of concrete",
    "RecyclingEfficiencyGlass": "Recycling efficiency of glass",
    "RecyclingEfficiencyClaybrick": "Recycling efficiency of clay bricks",
    "RecyclingEfficiencyMineralWool": "Recycling efficiency of mineral wool",
    "RecyclingEfficiencyCardboard": "Recycling efficiency of cardboard",

    # --- recycled content already embodied in the virgin material ------------
    # Module D1 credits only the NET secondary material: what comes out at end of
    # life minus what went in as recycled content.
    "RecycledContentMetals": "Recycled content of steel (fraction of total steel mass)",
    "RecycledContentPlastic": "Recycled content of plastics (fraction of total plastic mass)",
    "RecycledContentClaybrick": "Recycled content of clay bricks",
    "RecycledContentConcrete": "Recycled content of concrete",
    "RecycledContentCardboard": "Recycled content of cardboard",
    "RecycledContentMineralWool": "Recycled content of mineral wool",
    "RecycledContentGlass": "Recycled content of glass",

    # --- how much primary material one unit of secondary material displaces --
    "SRmetals": "Material substitution ratio for metals",
    "SRinert": "Material substitution ratio for inert materials",
    "SRclaybrick": "Material substitution ratio for lightweight bricks",

    # --- lower heating values [MJ/kg], for the D3 energy-recovery credit -----
    "LHVElastomer": "Lower heating value of elastomers",
    "LHVElectronics": "Lower heating value of electronic waste",
    "LHVHazardous": "Lower heating value of hazardous waste",
    "LHVHDPE": "Lower heating value of high-density polyethylene (HDPE)",
    "LHVPEfoam": "Lower heating value of polyethylene foam",
    "LHVPP": "Lower heating value of polypropylene (PP)",
    "LHVPVC": "Lower heating value of PVC",
    "LHVEPS": "Lower heating value of expanded polystyrene (EPS)",
    "LHVCardboard": "Lower heating value of cardboard",
    "LHVPUfoam": "Lower heating value of polyurethane foam",
    "LHVglass": "Lower heating value of glass wool",
    "LHVFoamGlass": "Lower heating value of foam glass",

    # --- fraction of the heat released on incineration that is recovered -----
    "Xincheat": "Thermal energy recovery efficiency",
    "Xincele": "Electrical energy recovery efficiency",
}


class EolParameters:
    """The end-of-life parameters, read once from the workbook.

    Values are accessible as attributes or by key::

        eol.LandfillMetals      eol["LandfillMetals"]

    Parameters
    ----------
    path : str
        Path to EndOfLifeInputParameters.xlsx.

    Raises
    ------
    KeyError
        If any parameter in PARAMETERS is missing from the workbook.
    """

    def __init__(self, path):
        self.path = path
        table = pd.read_excel(path, sheet_name=SHEET)

        missing = []
        self._values = {}
        for name, parameter in PARAMETERS.items():
            found = table.loc[table["Parameter"] == parameter, "value"]
            if found.empty:
                missing.append((name, parameter))
            else:
                self._values[name] = float(found.values[0])

        # Fail here, naming the parameter, rather than letting a KeyError or a
        # NaN surface much later inside an inventory formula.
        if missing:
            lines = "\n".join(f"    {n}: {p!r}" for n, p in missing)
            raise KeyError(
                f"{len(missing)} end-of-life parameter(s) not found in {path}:\n{lines}"
            )

    def __getitem__(self, name):
        return self._values[name]

    def __getattr__(self, name):
        # only called when normal attribute lookup fails
        try:
            return self.__dict__["_values"][name]
        except KeyError:
            raise AttributeError(f"no end-of-life parameter named {name!r}") from None

    def __contains__(self, name):
        return name in self._values

    def __len__(self):
        return len(self._values)

    def as_dict(self):
        """A plain copy, for unpacking into an inventory function."""
        return dict(self._values)

    def __repr__(self):
        return f"EolParameters({len(self._values)} values from {self.path})"
