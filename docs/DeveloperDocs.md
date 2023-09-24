# Jets of Time: Developer Notes

This document is intended for potential developers/testers of Jets of Time code base.

## Overview

Jets of Time Randomizer is mostly written in python (python3.8+). Currently, both a
command-line interface (CLI, `sourcefiles/randomizer.py`) and tkinter graphical
interface (TK GUI, `sourcefiles/randomizergui.py`) are provided. These are frequently
tested by developers on several Linux distrobutions as well as Windows.

Additionally, a [separate web UI (ctjot_web_generator)](https://github.com/Anguirel86/ctjot_web_generator)
is the primary means of end-users for generating randomizer seeds (e.g. at
[beta.ctjot.com](https://beta.ctjot.com)). That repo uses this repo as a git submodule.
That repo provides a local `docker` development flow which should work on systems with `docker`.

Intended development flow typically involves:

* Forking this repo
* Making changes locally in a python3 virtualenv
* Running tests locally and manually testing randomizer CLI, TK GUI, and/or local version of web UI
* Pushing commits to your own branch on your fork
* Opening a Pull Request (PR) against this repo from your fork's branch
* Ideally adding details, context, and manual test results to the PR to explain and demo changes
* Marking the Pull Request as ready for review

## Running Tests

There are several Github Actions workflows defined under `.github/workflows` which run on PRs/pushes.
These can run on your fork in your github account. These include `flake8` and `pytest`, which
can be run locally in a python3 virtualenv.

It is recommended to create a python 3.8+ virtualenv (python 3.11 is recommended) for development
per [python docs](https://docs.python.org/3/library/venv.html). Then `pip` can be used to install
requirements and test dependencies:

```bash
pip install -r sourcefiles/tests/requirements.txt
```

(This file references the root `requiremwents.txt` which itself constrains dependencies via `constraints.txt`
per [`pip` documentation](https://pip.pypa.io/en/stable/user_guide/#constraints-files)).

### Flake8

`flake8` is a very common linting tool for python, which can be run:

```bash
flake8 .
```

### Pytest

A number of unit and other automated tests have been developed for testing randomizer code.

They can be run via:

```bash
pytest sourcefiles/tests
```

Additionally, slower, much more extensive automated testing of the `randomizer.py` CLI can be done
if you have a copy of the vanilla Chrono Trigger (US) rom. Store the path to the rom in the `CTROM`
environment variable (e.g. with `export CTROM="ct.sfc"`) and then the ROM tests can be run:

```bash
pytest sourcefiles/tests --run-ctrom
```

These tests actually generate several seeds so can take several minutes depending on your system.

### Mypy

Some developers also type-check files in this repo with `mypy`. This is not mandated on PRs at this time
but can be optionally done as a fast means of ensuring code quality and finding bugs, outside of automated
or manual testing (especially edge-cases). The `pyproject.toml` has `mypy` configuration, and a version
is constrained in `constraints.txt`, but `mypy` is not currently installed via test requirements.

A compatible version of `mypy` can be installed in your virtualenv via:

```bash
pip install -c constraints.txt mypy
```

If `mypy` is installed in the virtualenv, it can be run via:

```bash
mypy sourcefiles
```
