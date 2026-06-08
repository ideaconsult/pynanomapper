# pynanomapper

A Python library providing **template blueprint schema, data entry workflows, Excel and NeXus conversions, ontology annotation, and REST API access** for the eNanoMapper/AMBIT ecosystem — supporting experimental safety data for chemicals, nanomaterials, polymers, microplastics, and UVCB substances.

pynanomapper builds on the [pyambit](https://github.com/ideaconsult/pyambit) data model and is a required dependency of [templates-api](https://github.com/ideaconsult/templates-api), the backend powering [Template Designer](https://enanomapper.adma.ai/templates).

## Package structure

### `datamodel.templates` — Template blueprint and conversion workflows

The core of the library. Implements the Template Designer blueprint schema and all data conversion pipelines:

- **`blueprint.py`** — Parses JSON blueprint definitions and generates styled, semantically annotated Excel templates
  from blueprint JSON. Extracts and structures method metadata (protocol, provenance, endpoints, units, sample
  preparation), generates nmparser configuration, and handles Template Designer blueprint embedding.

- **`template_designer.py`** — SurveyJS definition for Template Designer blueprint creation.

- **`template_parser.py`** / **`tdparser.py`** — Excel template parsing: reads filled-in Template Designer Excel files, extracts the hidden JSON blueprint from the `TemplateDesigner` sheet, and converts data entries into structured eNanoMapper records.

- **`excel_to_nexus.py`** — Excel → NeXus conversion: converts Template Designer Excel files to NeXus (`.nxs`) format via [pyambit](https://github.com/ideaconsult/pyambit). Parses the embedded blueprint, converts to pyambit `Substances`/`ProtocolApplication`, and writes NeXus output using pyambit's nexus_writer. Supports flat and hierarchical NeXus organisation.

- **`data_entry_survey.py`** — Survey/data entry support for template-based data collection workflows.

- **`template_config.py`** — Configuration for template rendering and validation.

### `annotation.py` — Ontology annotation

Dictionary-based annotation of experimental endpoints and parameters against ontology terms (ENM ontology, BioPortal). Maps free-text parameter names to controlled vocabulary URIs, supporting semantic enrichment of experimental records.

### API and service clients

- **`client_ambit.py`** — Client for the original AMBIT REST API ([api.ideaconsult.net/portal](https://api.ideaconsult.net/portal/#!/)): structured access to substances, studies, endpoints, and experimental results using the full eNanoMapper data model. Based on the OpenTox API architecture published in 2011.

- **`client_solr.py`** — Client for the Solr search layer that indexes the federated eNanoMapper instances: full-text and faceted search across the consolidated dataset. Complements the AMBIT API for discovery and filtering across large collections of substances and studies.

The modules above are top-level modules under `src/pynanomapper/`.

The `clients/` package contains additional service integrations:

- **`h5service.py`** / **`h5converter.py`** — HDF5/NeXus service integration: read and write NeXus files via HSDS (HDF5 Dynamic Data Service).

- **`service_charisma.py`** — Integration with the CHARISMA/ramanchada spectral data service ([spectra.adma.ai](https://spectra.adma.ai)).

- **`service_import.py`** — Data import utilities for batch loading into eNanoMapper.

- **`authservice.py`** — Authentication handling for eNanoMapper API access.

- **`datamodel_simple.py`** — Simplified data model representations for lightweight use cases.

Some service integrations require optional packages or external deployments that are not needed by the core template and
conversion workflows.

### `units.py`

Unit handling and conversion for experimental measurements.

### `datamodel/nexus_image.py`

NeXus image data support for experimental data containing imaging outputs.

## Installation

```bash
pip install pynanomapper
```

## Usage and examples

See the [notebooks-ambit repository](https://github.com/ideaconsult/notebooks-ambit/tree/master/enanomapper) for worked examples covering substance search, study retrieval, template generation, Excel parsing, and NeXus conversion.

API documentation: [api.ideaconsult.net/portal](https://api.ideaconsult.net/portal/#!/)

## Live deployment

The eNanoMapper deployment at [enanomapper.adma.ai](https://enanomapper.adma.ai) hosts experimental safety data compiled across 15+ years and 30+ EU Horizon projects, spanning nanosafety, advanced materials, microplastics, and regulatory toxicology. The dataset exceeds the scope described in [Jeliazkova et al., Nature Nanotechnology 2021](https://doi.org/10.1038/s41565-021-00911-6).

[Template Designer](https://enanomapper.adma.ai/templates) provides a web interface for collaborative template blueprint creation, powered by this library via [templates-api](https://github.com/ideaconsult/templates-api).

## Ecosystem

pynanomapper is a dependency of:
- [templates-api](https://github.com/ideaconsult/templates-api) — Template Designer backend; uses pynanomapper for blueprint schema, Excel generation, NeXus conversion, and API access

Related libraries:
- [pyambit](https://github.com/ideaconsult/pyambit) — eNanoMapper/AMBIT data model and NeXus writer; used by pynanomapper as the underlying data representation layer
- [AOPMapper](https://github.com/ideaconsult/aopmapper) — mechanistic interpretation via Adverse Outcome Pathways, live at [aop.adma.ai](https://aop.adma.ai)
- [QUBounds](https://github.com/ideaconsult/qubounds) — conformal prediction for safety assessment models

## Background

The eNanoMapper/AMBIT platform was published as a distributed REST API in 2011 ([doi:10.1186/1758-2946-3-18](https://doi.org/10.1186/1758-2946-3-18)), originally designed for REACH substance data including multicomponent UVCB substances from ECHA IUCLID dossiers. The data model was subsequently extended to nanomaterials and advanced materials. pynanomapper implements the template and conversion workflows that make this ecosystem accessible for structured experimental data entry and export.

## Funding

Developed across EU Horizon 2020 and Horizon Europe projects including eNanoMapper (604134), RiskGONE (814425), PINK (862444), HARMLESS (953183), CUSP (964766), MOMENTUM (953256), and the Network of Safety Clusters (NSC).

## Citation

If you use pynanomapper in your research, please cite the relevant work from the eNanoMapper ecosystem:

- eNanoMapper data model and dataset: Jeliazkova N. et al. (2021). The eNanoMapper database for nanomaterial safety information. *Nature Nanotechnology*. [doi:10.1038/s41565-021-00911-6](https://doi.org/10.1038/s41565-021-00911-6)
- AMBIT REST API: Jeliazkova N. & Jeliazkov V. (2011). AMBIT RESTful web services: an implementation of the OpenTox application programming interface. *Journal of Cheminformatics*, 3, 18. [doi:10.1186/1758-2946-3-18](https://doi.org/10.1186/1758-2946-3-18)
- Template Wizard methodology: Nymark P. et al. (2024). *Nature Protocols*. [doi:10.1038/s41596-024-00993-1](https://doi.org/10.1038/s41596-024-00993-1)
- HTS FAIRification case study using this library: [doi:10.1186/s13321-025-01001-8](https://doi.org/10.1186/s13321-025-01001-8)

## License

MIT
