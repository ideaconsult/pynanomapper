# AGENTS.md

Guidance for AI agents working on `pynanomapper`. This file describes the current repository state and should be
updated whenever tooling, docs, or workflows change.

## Project Overview

`pynanomapper` is a Python library for the eNanoMapper/AMBIT ecosystem. It provides Template Designer blueprint
handling, Excel template generation and parsing, Excel-to-NeXus conversion through `pyambit`, ontology annotation
helpers, and clients for AMBIT/Solr plus related services.

The package is published with Poetry from `src/pynanomapper`. It depends on `pyambit` for the AMBIT/eNanoMapper data
model and NeXus writer.

## Current Documentation Caveats

- PR 72 expands `README.md` and adds `ROADMAP.md`; those files are useful context but currently contain a few
  mismatches with the checked-out code.
- Current `README.md` and `ROADMAP.md` mention `claude_excel_gen.py`, but that file is not present. Current Excel
  template generation is primarily in `src/pynanomapper/datamodel/templates/blueprint.py`.
- `client_ambit.py` and `client_solr.py` are top-level modules under `src/pynanomapper/`, not files inside
  `src/pynanomapper/clients/`.
- There is currently no `CONTRIBUTING.md` in this repository and no `.pre-commit-config.yaml`.
- The `CONTRIBUTING.md` of https://github.com/ideaconsult/pyambit is useful for style and process ideas, but do not
  copy tool claims into this repo unless the matching config exists here.

## Repository Layout

- `src/pynanomapper/datamodel/templates/blueprint.py`: blueprint-to-Excel generation, nmparser config generation,
  template customization helpers, hidden blueprint embedding.
- `src/pynanomapper/datamodel/templates/template_designer.py`: SurveyJS definition for Template Designer blueprint
  creation.
- `src/pynanomapper/datamodel/templates/template_parser.py`: parser for filled Template Designer Excel files into
  `pyambit` data model objects.
- `src/pynanomapper/datamodel/templates/excel_to_nexus.py`: public helpers for Excel-to-NeXus,
  Excel-to-`ProtocolApplication`, and Excel-to-`Substances` conversion.
- `src/pynanomapper/datamodel/templates/data_entry_survey.py`: SurveyJS data-entry survey generation from a blueprint.
- `src/pynanomapper/datamodel/templates/tdparser.py`: parser for pchem-style template layouts and spectral data files.
- `src/pynanomapper/client_ambit.py`: AMBIT REST resource classes.
- `src/pynanomapper/client_solr.py`: Solr query, facet, study document, material, and indexing helpers.
- `src/pynanomapper/annotation.py`: dictionary-backed ontology annotation helpers.
- `src/pynanomapper/units.py`: unit conversion helpers built on `measurement`.
- `src/pynanomapper/clients/`: service integrations for auth, HSDS/HDF5, CHARISMA/ramanchada, imports, and a
  simplified data model.
- `tests/`: pytest tests and fixtures for imports, blueprint-to-Excel generation, data-entry survey generation, and
  Excel-to-NeXus conversion.
- `.github/workflows/ci.yml`: authoritative CI test workflow.
- `.github/workflows/publish.yml`: release-to-PyPI workflow.

## Environment And Tooling

- Packaging and dependency management use Poetry.
- CI uses Poetry `2.1.3`.
- Supported Python versions in CI are `3.10`, `3.11`, `3.12`, and `3.13`.
- `pyproject.toml` declares `python = ">=3.10,<3.14"`.
- `.python-version` lists `3.13`, `3.12`, `3.11`, and `3.10`.
- `.editorconfig` sets UTF-8, LF endings, final newline, trimming trailing whitespace, 4-space indentation, and
  120-character max line length for Markdown and Python.
- `.yamllint.yml` extends the default rules and sets YAML line length to 120.
- There is no active formatter, linter, coverage, or pre-commit workflow in this repo at the time of writing.

## Common Commands

Install dependencies like CI:

```sh
poetry install --no-interaction
```

Run tests like CI:

```sh
poetry run pytest
```

Build package distributions, as in the publish workflow:

```sh
poetry build --no-interaction
```

Run a focused test file during development:

```sh
poetry run pytest tests/test_blueprint.py
```

## Testing Notes

- `pyproject.toml` configures pytest with `pythonpath = ["src"]`, `addopts = "-ra -q"`, and test paths `tests` plus
  `integration`.
- There is currently no `integration/` directory in this checkout.
- Some tests generate files under `tests/resources/`, such as Excel templates, `.nxs` files, and `.json.nmparser`
  files. Always inspect `git status --short` after running tests.
- `tests/test_excel_to_nexus.py::test_excel_to_nexus_default_output` may leave a generated `.nxs` file beside the input
  fixture because cleanup is commented out.
- Base CI only runs `poetry run pytest`; it does not run optional service-client smoke tests requiring external services
  or undeclared dependencies.

## Dependency Caveats

- `pyproject.toml` contains the base package dependencies needed by CI and core tests.
- Several service modules import packages that are not declared in `pyproject.toml`, including `h5pyd`,
  `python-keycloak`, `ramanchada2`, `matplotlib`, `numcompress`, and OpenCV (`cv2`).
- Do not assume every module in `src/pynanomapper/clients/` is importable from a clean base install.
- Prefer targeted imports in tests and examples. Avoid broad package import checks that pull optional service modules
  unless optional dependencies are added first.

## Development Guidance

- Make the smallest correct change. Avoid broad cleanup or formatting churn unless requested.
- Preserve current public module paths. `src/pynanomapper/__init__.py` is empty and does not re-export APIs.
- Be careful with generated binary fixtures (`.xlsx`, `.nxs`) and package artifacts under `dist/`; do not modify or
  remove them unless the task requires it.
- If documentation and implementation disagree, verify against source code, tests, `pyproject.toml`, and GitHub Actions
  before editing.
- External service behavior may depend on AMBIT, Solr, HSDS, Keycloak, or CHARISMA deployments. Prefer unit-level tests
  and fixtures unless the user explicitly asks for live integration checks.

## Release And CI Notes

- The default branch used by workflows is `master`.
- CI runs on pushes and pull requests targeting `master`, plus manual dispatch.
- The publish workflow runs on published GitHub releases, installs with Poetry, runs pytest, builds with Poetry, uploads
  artifacts, and publishes to PyPI through trusted publishing.
- Dependabot is configured for weekly GitHub Actions and Python dependency checks.
