# pynanomapper Roadmap

This roadmap describes planned development for pynanomapper in the context of the broader nAMBIT ecosystem. The library currently provides template blueprint schema, Excel/NeXus conversion workflows, ontology annotation, and AMBIT/Solr API clients.

## Current state (v2.3.0)

- Template blueprint schema and JSON parsing (`datamodel.templates.blueprint`)
- Excel template generation from blueprints (`datamodel.templates.blueprint`)
- Excel → NeXus conversion via pyambit (`datamodel.templates.excel_to_nexus`)
- Template Designer SurveyJS definition and Excel parser support (`template_designer.py`, `template_parser.py`)
- Ontology annotation for endpoints and parameters (`annotation.py`)
- AMBIT REST API client (`client_ambit.py`)
- Solr search layer client (`client_solr.py`)
- HSDS/HDF5 service integration (`clients.h5service`, `clients.h5converter`)
- CHARISMA/ramanchada spectral service client (`clients.service_charisma`)
- CI/CD via GitHub Actions; 3 maintainers

## Near-term (v2.4 — v2.5)

- **pyambit dependency update**: align with latest pyambit releases (currently pinned at `^0.0.2`); track data model and NeXus writer improvements
- **Improved blueprint validation**: schema validation for template blueprints before Excel generation and NeXus conversion
- **Expanded ontology annotation**: broader endpoint and parameter coverage; improved BioPortal and ENM ontology lookup
- **Async API clients**: non-blocking AMBIT and Solr clients for large-scale data retrieval workflows
- **Test coverage expansion**: integration tests for Excel→NeXus round-trips; blueprint parsing edge cases

## Medium-term (pending funding)

- **MCP server**: expose pynanomapper as a [Model Context Protocol](https://modelcontextprotocol.io) server, making eNanoMapper data and template workflows callable by AI agents as deterministic scientific functions:
  - `search_substance(query, filters)` — substance lookup via AMBIT and Solr
  - `get_studies(substance_uri, endpoint)` — experimental evidence retrieval
  - `generate_template(blueprint_id)` — Excel template generation from blueprint
  - `excel_to_nexus(file)` — convert submitted Excel to NeXus
  - `annotate_endpoint(text)` — ontology annotation for free-text parameters

- **AI-assisted blueprint generation**: integration with pdf2template workflows — receive an SOP or protocol description and generate a template blueprint draft; leverages the existing blueprint schema as the structured output target

- **AOP-annotated templates**: integration with [AOPMapper](https://github.com/ideaconsult/aopmapper) to suggest relevant AOP Key Events for endpoints defined in a template blueprint, enriching templates with mechanistic context at creation time

- **Semantic query layer**: ontology-aware querying — retrieve all studies for a given AOP Key Event, or all nanomaterials above a given size threshold, combining eNanoMapper structured access with AOP semantic reasoning

- **Expanded format export**: SEND export from filled-in templates; IUCLID-compatible XML output for regulatory submission workflows

## Contributing

Issues and pull requests welcome at [github.com/ideaconsult/pynanomapper](https://github.com/ideaconsult/pynanomapper). For major features please open an issue first to discuss scope and approach.

Maintainers: Nina Jeliazkova, Luchesar Iliev, Vedrin Jeliazkov (Ideaconsult Ltd.)
