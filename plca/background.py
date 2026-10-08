"""
background.py - the background database: ecoinvent and its premise-generated
prospective copy.

The foreground - every energy-system activity this tool builds - is a thin
layer of exchanges pointing into a background database that supplies all the
upstream production. Three steps, in order:

  1. import_ecoinvent()       import an ecoinvent release, unless that version
                              and system model is already in the project.
  2. build_premise_database() run premise to project that release to an IAM
                              scenario (model / pathway / year), unless a
                              matching database already exists.
  3. open_background()        return the two databases the run uses: ei
                              (technosphere) and bio (biosphere).

Steps 1 and 2 are one-off per project and can take several minutes; re-running
them on a prepared project is a quick no-op. Credentials (the ecoinvent password and the
premise decryption key) are asked for at run time and never stored.
"""

import bw2data as bd
import bw2io as bi

from .project import ask, ask_secret


def import_ecoinvent(version=None, system_model=None, username=None, password=None):
    """Import an ecoinvent release into the current project, if not there yet.

    The tool is built for premise-modified ecoinvent 3.11. For another
    version, first check that every dataset named in ecoinvent_datasets.py
    exists in it (names are matched exactly). Credentials are asked for only
    if an import is needed.

    Parameters
    ----------
    version, system_model, username, password : str, optional
        Asked for interactively when not given.

    Returns
    -------
    str
        The database name, 'ecoinvent-<version>-<system_model>'.
    """
    print("You can use any version of ecoinvent, but make sure that the datasets "
          "listed in ecoinvent_datasets.py are present in the version you choose.\n")
    ei_version = ask("Enter ecoinvent version (e.g., 3.11): ", version)
    ei_model = ask("Enter system model (cutoff / apos / consequential / EN15804): ",
                   system_model)

    db_name = f"ecoinvent-{ei_version}-{ei_model}"
    if db_name in bd.databases:
        print(f"ecoinvent {ei_version}-{ei_model} is already present in the project")
    else:
        ei_username = ask("ecoinvent username: ", username)
        ei_password = ask_secret("ecoinvent password: ", password)
        bi.import_ecoinvent_release(
            version=ei_version,
            system_model=ei_model,       # cutoff / apos / consequential / EN15804
            username=ei_username,
            password=ei_password,
        )
    return db_name


def build_premise_database(source_db=None, source_version=None, model=None,
                           pathway=None, year=None, key=None, biosphere=None):
    """Generate a premise prospective copy of ecoinvent, unless one already exists.

    premise rewrites the background database to represent a future year under
    an IAM scenario (electricity mix, fuel supply chains, ...), which mainly
    affects the operational energy (B6). The first generation for a given
    model and pathway downloads the IAM data and takes a long time.

    Parameters
    ----------
    source_db, source_version, model, pathway, year : str, optional
        Asked for interactively when not given.
    key : str, optional
        premise decryption key; asked for (hidden) when not given.
    biosphere : str, optional
        Name of the biosphere database premise should read. premise defaults
        to 'biosphere3' and prompts if that is not in the project; pass e.g.
        'ecoinvent-3.11-biosphere' to avoid the prompt.

    Returns
    -------
    str or None
        The name of the matching existing database, or None when a new one
        was just generated (premise appends the build date to the name; look
        it up in bd.databases).

    Raises
    ------
    ValueError
        If any input is empty.
    """
    print("### PREMISE CONFIGURATION ###")
    print("Please provide the following details to check for an existing "
          "premise-generated database or to generate a new one.")
    print("If it is the first time you are generating a premise database with these "
          "specific model and pathway, the process may take a while as it needs to "
          "download the necessary IAM data and perform the transformations.\n")
    print("Note: The source database (e.g., ecoinvent-3.11-cutoff) must already be "
          "imported into the Brightway project.\n")

    source_db = ask("Enter source database name for premise transformation "
                    "(e.g., ecoinvent-3.11-cutoff): ", source_db)
    source_version = ask("Enter source ecoinvent version for premise transformation "
                         "(e.g., 3.11): ", source_version)
    model = ask("Enter IAM model (e.g., remind): ", model)
    pathway = ask("Enter pathway (e.g., SSP2-PkBudg1000): ", pathway)
    year_input = ask("Enter year (e.g., 2030): ", year)

    if not all([source_db, source_version, model, pathway, year_input]):
        raise ValueError("One or more inputs are empty. Run again and provide all values.")
    year = int(year_input)

    # --- has this database been generated already? ---------------------------
    # Matched by substring: premise names databases after the scenario and the
    # build date, e.g. 'ecoinvent-3.11-remind-SSP2-PkBudg1000-2030-cutoff
    # 2025-04-17'.
    print("\nChecking existing databases for a match...")
    existing_db_name = ""
    for db in bd.databases:
        if source_version in db and model in db and pathway in db and str(year) in db:
            existing_db_name = db
            break

    if existing_db_name:
        print("SKIPPING premise generation.")
        print(f"Found existing database matching parameters: '{existing_db_name}'")
        return existing_db_name

    print(f"No match found. Starting premise generation for {model} - {pathway} - {year}...")

    # Imported here: premise is slow to import and only needed to generate.
    from premise import NewDatabase

    biosphere_kwarg = {"biosphere_name": biosphere} if biosphere else {}

    ei_fut = NewDatabase(
        scenarios=[{"model": model, "pathway": pathway, "year": year}],
        source_db=source_db,
        source_version=source_version,
        key=ask_secret("premise decryption key: ", key),
        **biosphere_kwarg,
    )
    ei_fut.update()                    # apply the IAM-driven transformations
    ei_fut.write_db_to_brightway()     # write the transformed database into the project
    print("Database creation complete.")
    return None


def open_background(ei_bg=None, bio_bg=None):
    """Open the background databases and return them as (ei, bio).

    ei is the prospective technosphere database every material and energy
    exchange points into; bio is the biosphere database holding the
    elementary flows of the direct emissions. The biosphere must be the one
    premise used as its source, so the flows match the characterisation
    methods.

    Parameters
    ----------
    ei_bg, bio_bg : str, optional
        Database names; asked for interactively when not given.

    Returns
    -------
    tuple of bw2data.Database
        (ei, bio)

    Raises
    ------
    ValueError
        If either database is not in the project.
    """
    ei_bg = ask("Enter the full name of the futurized ecoinvent database to use as "
                "background database (e.g., "
                "ecoinvent-3.11-remind-SSP2-PkBudg1000-2030-cutoff yyyy-mm-dd): ", ei_bg)
    bio_bg = ask("Enter the name of the biosphere database. It must be the same "
                 "biosphere database used as source in the premise transformation "
                 "(e.g., ecoinvent-3.11-biosphere): ", bio_bg)

    # bd.Database(name) does not fail on an unknown name, so check explicitly.
    for name in (ei_bg, bio_bg):
        if name not in bd.databases:
            raise ValueError(f"database {name!r} is not in project "
                             f"{bd.projects.current!r}. Present: {sorted(bd.databases)}")

    return bd.Database(ei_bg), bd.Database(bio_bg)
