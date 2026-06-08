# pynanomapper

A Python library implementing the **eNanoMapper/AMBIT common data model** for experimental safety data — providing substance representations, experimental schema definitions, data conversions, and REST API access for chemicals, nanomaterials, polymers, microplastics, and UVCB substances.

pynanomapper is the core library of the **nAMBIT ecosystem**: open software for mechanistic, explainable, and uncertainty-aware safety assessment. It is a dependency of [templates-api](https://github.com/ideaconsult/templates-api), the backend powering [Template Designer](https://enanomapper.adma.ai/templates).

## What it does

**Data model and schema:**
- Implements the eNanoMapper/AMBIT common data model for substances and experiments — a unified, ontology-aligned representation covering well-defined chemicals (SMILES), nanomaterials, polymers, multicomponent UVCB substances, and advanced materials
- Defines and validates template blueprint schemas for structured experimental data capture
- Powers the template co-creation workflow in [Template Designer](https://enanomapper.adma.ai/templates)

**Conversions:**
- Template blueprint → Excel (machine-readable, semantically annotated)
- Template blueprint → NeXus format (via [pyambit](https://github.com/ideaconsult/pyambit)), enabling interoperability with FAIRmat and materials science AI pipelines
- Experimental data → pandas DataFrame, ISA-Tab, and other formats

**API access:**
- Query the eNanoMapper REST API ([api.ideaconsult.net/portal](https://api.ideaconsult.net/portal/#!/)) for substances, studies, endpoints, and experimental results
- Retrieve ontology-annotated experimental toxicology data: physicochemical characterisation, in vitro assays, dose-response data, provenance metadata

## Installation

```bash
pip install pynanomapper
```

## Usage and examples

See the [notebooks-ambit repository](https://github.com/ideaconsult/notebooks-ambit/tree/master/enanomapper) for worked examples covering substance search, study retrieval, template generation, and data export.

API documentation: [api.ideaconsult.net/portal](https://api.ideaconsult.net/portal/#!/)

## Live deployment

The eNanoMapper deployment at [enanomapper.adma.ai](https://enanomapper.adma.ai) hosts experimental safety data compiled across 15+ years and 30+ EU Horizon projects, spanning nanosafety, advanced materials, microplastics, and regulatory toxicology. The dataset exceeds the scope described in [Jeliazkova et al., Nature Nanotechnology 2021](https://doi.org/10.1038/s41565-021-00911-6).

Template Designer at [enanomapper.adma.ai/templates](https://enanomapper.adma.ai/templates) provides a web interface for collaborative template blueprint creation, powered by this library via [templates-api](https://github.com/ideaconsult/templates-api).

## Ecosystem

pynanomapper is a dependency of:
- [templates-api](https://github.com/ideaconsult/templates-api) — Template Designer backend; uses pynanomapper for blueprint schema, Excel generation, and NeXus conversion
- Other nAMBIT ecosystem components consuming eNanoMapper data

Related libraries:
- [pyambit](https://github.com/ideaconsult/pyambit) — NeXus conversion layer (J. Cheminformatics 2025, [doi:10.1186/s13321-025-01001-8](https://doi.org/10.1186/s13321-025-01001-8))
- [AOPMapper](https://github.com/ideaconsult/aopmapper) — mechanistic interpretation via Adverse Outcome Pathways, live at [aop.adma.ai](https://aop.adma.ai)
- [QUBounds](https://github.com/ideaconsult/qubounds) — conformal prediction for safety assessment models

## Background

The eNanoMapper/AMBIT platform was published as a distributed REST API in 2011 ([doi:10.1186/1758-2946-3-18](https://doi.org/10.1186/1758-2946-3-18)), originally designed for REACH substance data including multicomponent UVCB substances from ECHA IUCLID dossiers. The data model naturally extended to nanomaterials and advanced materials across the eNanoMapper EU project and successive programmes. pynanomapper is the Python implementation of this data model and its associated conversion workflows.

## Funding

Developed across EU Horizon 2020 and Horizon Europe projects including eNanoMapper (604134), RiskGONE (814425), PINK (862444), HARMLESS (953183), CUSP (964766), MOMENTUM (953256)

## Citation



## License

MIT