"""
project.py - choose the Brightway project and make it the current one.

Also holds the two prompt helpers used by background.py and scenario_db.py:
every run-time question is asked the same way and can be answered in advance
by passing the value in, which allows unattended runs.
"""

import getpass

import bw2data as bd


def ask(question, value=None):
    """Ask a question and return the answer, stripped of whitespace.

    Passing `value` skips the prompt and uses that answer (echoed to the
    output).
    """
    if value is not None and str(value).strip():
        answer = str(value).strip()
        print(f"{question}{answer}")      # echo, so the output still reads like a typed session
        return answer
    return input(question).strip()


def ask_secret(question, value=None):
    """Ask for a credential without echoing it.

    Same contract as ask(), but the input is hidden and never printed or
    stored.
    """
    if value is not None and str(value).strip():
        return str(value).strip()
    return getpass.getpass(question).strip()


def setup_project(name=None):
    """Select the Brightway project for this run, creating it if new.

    If the project exists, the user is offered to start a new project under
    another name instead.

    Parameters
    ----------
    name : str, optional
        Project name; skips the prompts when given.

    Returns
    -------
    str
        The name of the project made current.
    """
    project_name = ask("Enter the Brightway project name: ", name)
    if not project_name:
        raise ValueError("Project name cannot be empty.")

    # Do not use bd.projects.set_current() to test for existence: on a project
    # written by an older Brightway it runs a schema migration.
    if project_name in bd.projects and name is None:
        print(f"Project '{project_name}' already exists.")
        choice = ask(f"Project '{project_name}' already exists. Do you want to use "
                     f"another name and start a new project? (y/n): ").lower()
        if choice == "y":
            print(f"Existing projects: {sorted(bd.projects)}")
            project_name = ask("Enter a new project name: ")
            if not project_name:
                raise ValueError("Project name cannot be empty.")
            print(f"New project name set to: {project_name}")
        else:
            print(f"Using existing project: {project_name}")

    # Setting the current project creates it if it does not exist yet.
    bd.projects.set_current(project_name)
    print(f"Current project set to: {bd.projects.current}")
    return project_name
