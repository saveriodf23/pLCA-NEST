"""
scenario_db.py - the Brightway database the neighbourhood model is written into.

This is the foreground: every (system, module, building) activity built by
lca_model.py is written here, with exchanges pointing into the background
databases opened by background.py. It is rebuilt empty on every run.
"""

import bw2data as bd

from .project import ask


def create_scenario_db(name=None, overwrite=None):
    """Create and register an empty scenario database, and return it.

    An existing database of the same name is deleted first (after asking),
    so a re-run starts from a clean tree.

    Parameters
    ----------
    name : str, optional
        Database name; prompted for when not given.
    overwrite : bool, optional
        Answers 'delete the existing database?' in advance: True deletes,
        False refuses, None (default) asks.

    Returns
    -------
    bw2data.Database

    Raises
    ------
    ValueError
        If the name is empty or deletion is refused.
    """
    db_name = ask("Enter the name of the database in which you want to store the "
                  "model of your neighbourhood scenario: ", name)
    if not db_name:
        raise ValueError("Scenario database name cannot be empty.")

    if db_name in bd.databases:
        # Reusing it would collide with existing activity codes, so it must be
        # emptied; deletion cannot be undone, hence the question.
        print(f"WARNING: database '{db_name}' already exists and must be emptied "
              f"before it can be reused.")
        if overwrite is None:
            overwrite = ask(f"Delete '{db_name}' and start from an empty database? "
                            f"(y/n): ").lower() == "y"
        if not overwrite:
            raise ValueError(f"database '{db_name}' left untouched - run again with "
                             f"a name that is not already in use.")
        del bd.databases[db_name]
        print(f"Deleted '{db_name}'.")
    else:
        print(f"{db_name} is not present in the project")

    print(f"Creating and registering database '{db_name}' for the neighbourhood "
          f"scenario model...")
    scenario_db = bd.Database(db_name)
    scenario_db.register()      # a database must be registered before it can be written to
    return scenario_db
