survey_js = {
    "triggers": [
        {
            "type": "setvalue",
            "expression": "{confirm_statuschange} contains 'FINALIZED'",
            "setToName": "template_status",
            "setValue": "FINALIZED",
        },
        {
            "type": "setvalue",
            "expression": "!({confirm_statuschange} contains 'FINALIZED')",
            "setToName": "template_status",
            "setValue": "DRAFT",
        },
    ],
    "showPreviewBeforeComplete": "showAnsweredQuestions",
    "title": "Template Designer",
    "description": "Designing data entry templates for eNanoMapper",
    "logoPosition": "right",
    "pages": [
        {
            "name": "page_role",
            "elements": [
                {
                    "type": "text",
                    "name": "template_name",
                    "visible": True,
                    "title": "Template name",
                    "description": (
                        "Pick an unique name that reflect your experiment"
                        " and help you and others to find it later."
                    ),
                    "isRequired": True,
                },
                {
                    "type": "text",
                    "name": "template_acknowledgment",
                    "visible": True,
                    "startWithNewLine": False,
                    "title": "Template Acknowledgment",
                    "description": "Acknowledge a project, your lab, etc.",
                    "isRequired": True,
                },
                {
                    "type": "text",
                    "name": "template_author",
                    "visible": True,
                    "startWithNewLine": True,
                    "title": "Template Author",
                    "description": (
                        "The author of this template blueprint."
                        " Not necessary the person who perform the experiment."
                    ),
                    "isRequired": True,
                },
                {
                    "startWithNewLine": True,
                    "type": "checkbox",
                    "name": "user_role",
                    "title": "I am a ...",
                    "colCount": 1,
                    "choices": [
                        {
                            "value": "role_lab",
                            "text": " Lab researcher",
                        },
                        {
                            "value": "role_datamgr",
                            "text": "Data manager",
                        },
                    ],
                    "minSelectedChoices": 1,
                },
            ],
            "title": "Please enter the template name",
            "description": (
                "You are designing a template blueprint to report your experiment."
                " And you would like other researchers to find it and reuse it."
                "Some questions will be marked as required or not,"
                " based on the role specified."
            ),
            "navigationTitle": "Welcome",
            "navigationDescription": "Template name and acknowledgment",
        },
        {
            "name": "page1",
            "elements": [
                {
                    "type": "panel",
                    "name": "panel_method",
                    "elements": [
                        {
                            "type": "text",
                            "name": "METHOD",
                            "startWithNewLine": True,
                            "title": "Method",
                            "description": "Short name or acronym for test/assay",
                            "isRequired": True,
                        },
                        {
                            "type": "dropdown",
                            "name": "SOP",
                            "startWithNewLine": False,
                            "title": "Specify the type of protocol for the test",
                            "description": (
                                "Standard Operating Procedure (SOP) "
                                "or research protocol"
                            ),
                            "isRequired": True,
                            "choices": [
                                {
                                    "value": "protocol_sop",
                                    "text": "Standard Operating Procedure (SOP)",
                                },
                                {
                                    "value": "protocol_sopmodified",
                                    "text": "Modified SOP",
                                },
                                {
                                    "value": "protocol_research",
                                    "text": "Research protocol",
                                },
                            ],
                            "defaultValue": "protocol_sop",
                        },
                        {
                            "type": "text",
                            "name": "EXPERIMENT",
                            "title": "{SOP}",
                            "description": "Full name of the protocol for the test",
                            "startWithNewLine": True,
                            "isRequired": True,
                        },
                        {
                            "type": "comment",
                            "name": "EXPERIMENT_PROTOCOL",
                            "title": "{SOP} description",
                            "description": (
                                "Description of the test/assay and/or link to document"
                            ),
                            "startWithNewLine": True,
                            "visibleIf": (
                                "({SOP} contains '_research') "
                                "or ({SOP} contains 'modified')"
                            ),
                            "requiredIf": (
                                "({SOP} contains '_research') "
                                "or ({SOP} contains 'modified')"
                            ),
                        },
                        {
                            "type": "matrixdynamic",
                            "name": "conditions",
                            "title": "Experimental factors, replicates",
                            "description": (
                                "Add one row per each experimental factor"
                                " (e.g. concentration, time), replicates, etc."
                                " Remove the irrelevant rows."
                                "Don't forget to specify the type."
                                "The rows can be reorderd by drag and drop."
                            ),
                            "_requiredIf": "{user_role} contains 'role_datamgr'",
                            "defaultValue": [
                                {
                                    "conditon_name": "Concentration",
                                    "condition_unit": "mg/mol",
                                    "condition_type": "c_concentration",
                                },
                                {
                                    "conditon_name": "Time",
                                    "condition_unit": "h",
                                    "condition_type": "c_time",
                                },
                                {
                                    "conditon_name": "Replicate",
                                    "condition_type": "c_replicate",
                                },
                            ],
                            "columns": [
                                {
                                    "name": "conditon_name",
                                    "title": "Name",
                                },
                                {
                                    "name": "condition_unit",
                                    "title": "Unit",
                                },
                                {
                                    "name": "condition_type",
                                    "title": "Type",
                                    "cellType": "dropdown",
                                    "choices": [
                                        {
                                            "value": "c_concentration",
                                            "text": "Concentration",
                                        },
                                        {
                                            "value": "c_time",
                                            "text": "Time",
                                        },
                                        {
                                            "value": "c_replicate",
                                            "text": "Replicate",
                                        },
                                        {
                                            "value": "c_replicate_tech",
                                            "text": "Technical replicate",
                                        },
                                        {
                                            "value": "c_replicate_bio",
                                            "text": "Biological replicate",
                                        },
                                        {
                                            "value": "c_experiment",
                                            "text": "Experiment",
                                        },
                                        {
                                            "value": "c_other",
                                            "text": "Other",
                                        },
                                    ],
                                    "defaultValue": "c_replicate_tech",
                                },
                            ],
                            "cellType": "text",
                            "rowCount": 0,
                            "confirmDelete": True,
                            "allowRowsDragAndDrop": True,
                            "addRowText": "Add experimental factor",
                        },
                        {
                            "startWithNewLine": True,
                            "type": "checkbox",
                            "name": "controls",
                            "title": (
                                "Please specify if/what type of controls will be used"
                            ),
                            "description": (
                                "The actual controls will be specified in the template."
                            ),
                            "colCount": 5,
                            "choices": [
                                {
                                    "value": "c_control_negative",
                                    "text": "Negative controls",
                                },
                                {
                                    "value": "c_control_positive",
                                    "text": "Positive controls",
                                },
                                {
                                    "value": "c_control_interference",
                                    "text": "Interference controls",
                                },
                                {
                                    "value": "c_control_blank",
                                    "text": "Blank controls",
                                },
                                {
                                    "value": "c_control_other",
                                    "text": "Other type of controls",
                                },
                            ],
                        },
                    ],
                },
                {
                    "type": "panel",
                    "name": "panel_sop",
                    "elements": [],
                },
                {
                    "type": "panel",
                    "name": "panel_experiment",
                    "elements": [
                        {
                            "type": "html",
                            "name": "help_categories",
                            "titleLocation": "hidden",
                            "html": (
                                "Please select the closest categories for your study."
                                "The dropdown lists follows "
                                "<a href='https://www.oecd.org/ehs/templates/'"
                                " target=_blank>"
                                "OECD Harmonized Templates</a> nomenclature,"
                                " extended with ontology entries."
                            ),
                            "readOnly": True,
                        },
                        {
                            "type": "dropdown",
                            "name": "PROTOCOL_TOP_CATEGORY",
                            "title": "Study type",
                            "defaultValue": "P-CHEM",
                            "isRequired": True,
                            "choices": [
                                {
                                    "value": "P-CHEM",
                                    "text": "Physico-chemical characterisation",
                                },
                                {
                                    "value": "ECOTOX",
                                    "text": "Ecotoxicity studies",
                                },
                                {
                                    "value": "ENV FATE",
                                    "text": "Environmental fate",
                                },
                                {
                                    "value": "TOX",
                                    "text": "Toxicity studies",
                                },
                                {
                                    "value": "EXPOSURE",
                                    "text": "Exposure",
                                },
                            ],
                            "placeholder": "P-CHEM",
                        },
                        {
                            "type": "dropdown",
                            "name": "PROTOCOL_CATEGORY_CODE",
                            "startWithNewLine": False,
                            "title": "Type or class of experimental test",
                            "requiredIf": "{user_role} contains 'role_datamgr'",
                            "choices": [
                                {
                                    "value": "GI_GENERAL_INFORM_SECTION",
                                    "text": "4.1.Appearance",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_MELTING_SECTION",
                                    "text": "4.2.Melting point / freezing point",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_BOILING_SECTION",
                                    "text": "4.3.Boiling point",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_DENSITY_SECTION",
                                    "text": "4.4.Density",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_GRANULOMETRY_SECTION",
                                    "text": (
                                        "4.5.Particle size distribution (Granulometry)"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_VAPOUR_SECTION",
                                    "text": "4.6.Vapour pressure",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "SURFACE_TENSION_SECTION",
                                    "text": "4.10.Surface tension",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_PARTITION_SECTION",
                                    "text": "4.7.Partition coefficient",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_WATER_SOL_SECTION",
                                    "text": "4.8.Water solubility",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_SOL_ORGANIC_SECTION",
                                    "text": "4.9.Solubility in organic solvents",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_NON_SATURATED_PH_SECTION",
                                    "text": "4.20.pH",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_DISSOCIATION_SECTION",
                                    "text": "4.21.Dissociation constant",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_VISCOSITY_SECTION",
                                    "text": "4.22.Viscosity",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PC_UNKNOWN_SECTION",
                                    "text": "4.99.Physico chemical properties (other)",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "TO_PHOTOTRANS_AIR_SECTION",
                                    "text": "5.1.1.Phototransformation in Air",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "TO_PHOTOTRANS_SOIL_SECTION",
                                    "text": "5.1.2.Phototransformation in soil",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "TO_HYDROLYSIS_SECTION",
                                    "text": "5.1.2.Hydrolysis",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "TO_BIODEG_WATER_SCREEN_SECTION",
                                    "text": (
                                        "5.2.1.Biodegradation in water"
                                        " - screening tests"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "TO_BIODEG_WATER_SIM_SECTION",
                                    "text": (
                                        "5.2.2.Biodegradation in water"
                                        " and sediment: simulation tests"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "EN_STABILITY_IN_SOIL_SECTION",
                                    "text": "5.2.3.Biodegradation in Soil",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "EN_BIOACCUMULATION_SECTION",
                                    "text": "5.3.1.Bioaccumulation: aquatic / sediment",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "EN_BIOACCU_TERR_SECTION",
                                    "text": "5.3.2.Bioaccumulation: terrestrial",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "EN_ADSORPTION_SECTION",
                                    "text": "5.4.1.Adsorption / Desorption",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "EN_HENRY_LAW_SECTION",
                                    "text": "5.4.2.Henry's Law constant",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ENV FATE'",
                                },
                                {
                                    "value": "TO_ACUTE_ORAL_SECTION",
                                    "text": "7.2.1.Acute toxicity - oral",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_ACUTE_INHAL_SECTION",
                                    "text": "7.2.2.Acute toxicity - inhalation",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_ACUTE_DERMAL_SECTION",
                                    "text": "7.2.3.Acute toxicity - dermal",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_ACUTE_PULMONARY_INSTILLATION_SECTION",
                                    "text": (
                                        "7.2.9. Acute and sub-chronic"
                                        " toxicity - pulmonary instillation"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_SKIN_IRRITATION_SECTION",
                                    "text": "7.3.1.Skin irritation / Corrosion",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_EYE_IRRITATION_SECTION",
                                    "text": "7.3.2.Eye irritation",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_SENSITIZATION_SECTION",
                                    "text": "7.4.1.Skin sensitisation",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_SENSITIZATION_INSILICO_SECTION",
                                    "text": "7.4.1.Skin sensitisation (in silico)",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_SENSITIZATION_INVITRO_SECTION",
                                    "text": "7.4.1.Skin sensitisation (in vitro)",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_SENSITIZATION_INCHEMICO_SECTION",
                                    "text": "7.4.1.Skin sensitisation (in chemico)",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_SENSITIZATION_HUMANDB_SECTION",
                                    "text": "7.4.1.Skin sensitisation (human)",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_SENSITIZATION_LLNA_SECTION",
                                    "text": "7.4.1.Skin sensitisation (LLNA)",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_REPEATED_ORAL_SECTION",
                                    "text": "7.5.1.Repeated dose toxicity - oral",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_REPEATED_INHAL_SECTION",
                                    "text": "7.5.2.Repeated dose toxicity - inhalation",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_REPEATED_DERMAL_SECTION",
                                    "text": "7.5.3.Repeated dose toxicity - dermal",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_GENETIC_IN_VITRO_SECTION",
                                    "text": "7.6.1.Genetic toxicity in vitro",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_GENETIC_IN_VIVO_SECTION",
                                    "text": "7.6.2.Genetic toxicity in vivo",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_CARCINOGENICITY_SECTION",
                                    "text": "7.7.Carcinogenicity",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_REPRODUCTION_SECTION",
                                    "text": "7.8.1.Toxicity to reproduction",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TO_DEVELOPMENTAL_SECTION",
                                    "text": (
                                        "7.8.2.Developmental toxicity / teratogenicity"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "EC_FISHTOX_SECTION",
                                    "text": "6.1.1.Short-term toxicity to fish",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_CHRONFISHTOX_SECTION",
                                    "text": "6.1.2.Long-term toxicity to fish",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_DAPHNIATOX_SECTION",
                                    "text": (
                                        "6.1.3.Short-term toxicity to"
                                        " aquatic invertebrates"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_CHRONDAPHNIATOX_SECTION",
                                    "text": (
                                        "6.1.4.Long-term toxicity to"
                                        " aquatic invertebrates"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_ALGAETOX_SECTION",
                                    "text": (
                                        "6.1.5.Toxicity to aquatic algae"
                                        " and cyanobacteria"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_BACTOX_SECTION",
                                    "text": "6.1.7.Toxicity to microorganisms",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_SEDIMENTDWELLINGTOX_SECTION",
                                    "text": "6.2.Sediment toxicity",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_SOILDWELLINGTOX_SECTION",
                                    "text": "6.3.1.Toxicity to soil macroorganisms",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_HONEYBEESTOX_SECTION",
                                    "text": "6.3.2.Toxicity to terrestrial arthropods",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_PLANTTOX_SECTION",
                                    "text": "6.3.3.Toxicity to terrestrial plants",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "EC_SOIL_MICRO_TOX_SECTION",
                                    "text": "6.3.4.Toxicity to soil microorganisms",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'ECOTOX'",
                                },
                                {
                                    "value": "PC_THERMAL_STABILITY_SECTION",
                                    "text": "4.19.Stability (thermal)",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "RADICAL_FORMATION_POTENTIAL_SECTION",
                                    "text": "4.28.12.Radical formation potential",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "AGGLOMERATION_AGGREGATION_SECTION",
                                    "text": (
                                        "4.24.Nanomaterial agglomeration/aggregation"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "CRYSTALLINE_PHASE_SECTION",
                                    "text": "4.25.Nanomaterial crystalline phase",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "CRYSTALLITE_AND_GRAIN_SIZE_SECTION",
                                    "text": (
                                        "4.26.Nanomaterial crystallite and grain size"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "ASPECT_RATIO_SHAPE_SECTION",
                                    "text": "4.27.Nanomaterial aspect ratio/shape",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "SPECIFIC_SURFACE_AREA_SECTION",
                                    "text": "4.28.Nanomaterial specific surface area",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "ZETA_POTENTIAL_SECTION",
                                    "text": "4.29.Nanomaterial zeta potential",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "SURFACE_CHEMISTRY_SECTION",
                                    "text": "4.30.Nanomaterial surface chemistry",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "DUSTINESS_SECTION",
                                    "text": "4.31.Nanomaterial dustiness",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "POROSITY_SECTION",
                                    "text": "4.32.Nanomaterial porosity",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "POUR_DENSITY_SECTION",
                                    "text": "4.33.Nanomaterial pour density",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "PHOTOCATALYTIC_ACTIVITY_SECTION",
                                    "text": "4.34.Nanomaterial photocatalytic activity",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "CATALYTIC_ACTIVITY_SECTION",
                                    "text": "4.36.Nanomaterial catalytic activity",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "UNKNOWN_TOXICITY_SECTION",
                                    "text": "BAO_0002189.Toxicity (other)",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "RISKASSESSMENT_SECTION",
                                    "text": "MESH_D018570.Risk assessment",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "SUPPORTING_INFO_SECTION",
                                    "text": "7.999.9.Supporting information",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "TRANSCRIPTOMICS_SECTION",
                                    "text": "OBI_0000424.Transcriptomics",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "PROTEOMICS_SECTION",
                                    "text": "8.100.Proteomics",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "ENM_0000068_SECTION",
                                    "text": "ENM_0000068.Cell Viability",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "ENM_0000037_SECTION",
                                    "text": "ENM_0000037.Oxidative Stress",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "ENM_0000044_SECTION",
                                    "text": "ENM_0000044.Barrier integrity",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "NPO_1339_SECTION",
                                    "text": "NPO_1339.Immunotoxicity",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'TOX'",
                                },
                                {
                                    "value": "IMPURITY_SECTION",
                                    "text": (
                                        "_.Elemental composition and chemical purity"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "ANALYTICAL_METHODS_SECTION",
                                    "text": "CHMO_0001075.Analytical Methods",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'P-CHEM'",
                                },
                                {
                                    "value": "OMICS_SECTION",
                                    "text": "_.Omics",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'OMICS'",
                                },
                                {
                                    "value": "EXPOSURE_SECTION",
                                    "text": "3.5.0.Use and exposure information",
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'EXPOSURE'",
                                },
                                {
                                    "value": "EXPOSURE_MANUFACTURE_SECTION",
                                    "text": (
                                        "3.5.1.Use and exposure information."
                                        " Manufacture"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'EXPOSURE'",
                                },
                                {
                                    "value": "EXPOSURE_FORMULATION_REPACKAGING_SECTION",
                                    "text": (
                                        "3.5.2.Use and exposure information."
                                        " Formulation or re-packing"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'EXPOSURE'",
                                },
                                {
                                    "value": "EXPOSURE_INDUSTRIAL_SITES_SECTION",
                                    "text": (
                                        "3.5.3.Use and exposure information."
                                        " Uses at industrial sites"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'EXPOSURE'",
                                },
                                {
                                    "value": "EXPOSURE_PROFESSIONAL_WORKERS_SECTION",
                                    "text": (
                                        "3.5.4.Use and exposure information."
                                        " Widespread use by industrial workers"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'EXPOSURE'",
                                },
                                {
                                    "value": "EXPOSURE_CONSUMER_USE_SECTION",
                                    "text": (
                                        "3.5.5.Use and exposure information."
                                        " Consumer use"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'EXPOSURE'",
                                },
                                {
                                    "value": "EXPOSURE_SERVICE_LIFE_SECTION",
                                    "text": (
                                        "3.5.6.Use and exposure information."
                                        " Service Life"
                                    ),
                                    "visibleIf": "{PROTOCOL_TOP_CATEGORY} = 'EXPOSURE'",
                                },
                            ],
                        },
                        {
                            "type": "html",
                            "name": "comment_fair_learn",
                            "title": " ",
                            "hideNumber": True,
                            "titleLocation": "hidden",
                            "html": (
                                "<div class='alert alert-primary'>"
                                "You will be redirected to "
                                "<a href='https://enanomapper.adma.ai/fair/'"
                                " target='fair'>The visual guide to FAIR"
                                " principles (with eNanoMapper)</a>. "
                                "The guide consists of a dedicated page for "
                                "each of FAIR criteria and sub criteria, and"
                                "examples, interpretations and links to"
                                " possible implementations in addition "
                                "to the definitions.</div>"
                            ),
                            "readOnly": True,
                            "visibleIf": "{q_start} = 'fair_learn'",
                        },
                    ],
                    "titleLocation": "hidden",
                },
            ],
            "title": "[{template_name}]: Please describe the experimental method",
            "description": (
                "You will design a 'blueprint' of a data entry"
                " template to report result for the method described."
            ),
            "navigationTitle": "1. Method",
            "navigationDescription": "description",
        },
        {
            "name": "page_results",
            "elements": [
                {
                    "type": "panel",
                    "name": "panel_results",
                    "elements": [
                        {
                            "type": "comment",
                            "name": "RESULTS",
                            "title": "Results description",
                            "description": (
                                "Describe the results in free text "
                                ", including data analysis"
                            ),
                            "requiredIf": "{user_role} contains 'role_lab'",
                        },
                        {
                            "type": "checkbox",
                            "name": "data_sheets",
                            "startWithNewLine": False,
                            "title": (
                                "Include the following sheets "
                                "in the generated template:"
                            ),
                            "description": "",
                            "choices": [
                                {
                                    "value": "data_raw",
                                    "text": "Raw data",
                                },
                                {
                                    "value": "data_processed",
                                    "text": "Processed data",
                                },
                                {
                                    "value": "data_platelayout",
                                    "text": "Plate layout",
                                },
                                {
                                    "value": "data_calibration",
                                    "text": "Calibration curve",
                                },
                            ],
                            "hasOther": True,
                            "othertext": "Other (please specify)",
                            "defaultvalue": ["data_raw", "data_processed"],
                        },
                        {
                            "type": "dropdown",
                            "name": "plate_format",
                            "startWithNewLine": False,
                            "visibleIf": "{data_sheets} contains 'data_platelayout'",
                            "title": "Plate Layout Type",
                            "defaultvalue": "96",
                            "choices": [
                                {"value": "96", "text": "96-Well"},
                                {"value": "384", "text": "384-Well"},
                            ],
                        },
                        {
                            "type": "html",
                            "name": "help_data_sheets_other",
                            "titleLocation": "hidden",
                            "startWithNewLine": False,
                            "visibleIf": "{data_sheets} contains 'other'",
                            "html": (
                                "Please note that the 'Other' option is for "
                                "information purposes only, no data sheet"
                                " will be generated!"
                            ),
                            "readOnly": True,
                        },
                        {
                            "type": "html",
                            "name": "help_data_sheets",
                            "titleLocation": "hidden",
                            "startWithNewLine": False,
                            "visibleIf": (
                                "{data_sheets} contains 'data_raw' "
                                "or {data_sheets} contains 'data_processed'"
                            ),
                            "html": (
                                "Please define in the tables below the columns"
                                " that represents your results. Columns for "
                                "samples and experimental factors will be "
                                "automatically added. If your data is in "
                                "separate files you may use the 'Pointer to file' type."
                            ),
                            "readOnly": True,
                        },
                        {
                            "type": "matrixdynamic",
                            "name": "calibration_report",
                            "visibleIf": "{data_sheets} contains 'data_calibration'",
                            "title": "Calibration (standard) curve",
                            "addRowText": "Add empty row",
                            "description": (
                                "Please provide information of the parameters"
                                " reported as unprocessed data (e.g. Absorbance"
                                ", AU). Use the + button to specify which"
                                " factors are varied. If your data is in "
                                "separate files you may use the "
                                "'Pointer to file' type."
                            ),
                            "requiredIf": "{data_sheets} contains 'data_calibration'",
                            "showCommentArea": True,
                            "columns": [
                                {
                                    "name": "calibration_entry",
                                    "title": "Name",
                                    "isRequired": True,
                                },
                                {
                                    "name": "calibration_aggregate",
                                    "title": "Mark if aggregated",
                                    "cellType": "dropdown",
                                    "isRequired": False,
                                    "defaultValue": "RAW_DATA",
                                    "choices": [
                                        {
                                            "value": "RAW_DATA",
                                            "text": "Raw data",
                                        },
                                        {
                                            "value": "MEAN",
                                            "text": "Mean",
                                        },
                                        {
                                            "value": "MEDIAN",
                                            "text": "Median",
                                        },
                                        {
                                            "value": "MODE",
                                            "text": "Mode",
                                        },
                                        {
                                            "value": "AGGREGATED",
                                            "text": "Aggregated",
                                        },
                                        {
                                            "value": "NORMALIZED",
                                            "text": "Normalized",
                                        },
                                        {
                                            "value": "",
                                            "text": "Other",
                                        },
                                    ],
                                },
                                {
                                    "name": "calibration_unit",
                                    "title": "Unit",
                                },
                                {
                                    "name": "calibration_entry_uncertainty",
                                    "title": "Uncertainty",
                                    "cellType": "dropdown",
                                    "isRequired": False,
                                    "choices": [
                                        {
                                            "value": "none",
                                            "text": "",
                                        },
                                        {
                                            "value": "SD",
                                            "text": "Standard Deviation",
                                        },
                                    ],
                                },
                                {
                                    "name": "calibration_entry_type",
                                    "title": "Type",
                                    "cellType": "dropdown",
                                    "isRequired": True,
                                    "defaultValue": "value_num",
                                    "choices": [
                                        {
                                            "value": "value_sample",
                                            "text": "sample",
                                        },                                        
                                        {
                                            "value": "value_num",
                                            "text": "numeric",
                                        },
                                        {
                                            "value": "value_spectrum",
                                            "text": "spectrum",
                                        },
                                        {
                                            "value": "value_timeseries",
                                            "text": "time series",
                                        },
                                        {
                                            "value": "value_image",
                                            "text": "image",
                                        },
                                        {
                                            "value": "value_1darray",
                                            "text": "1D array",
                                        },
                                        {
                                            "value": "value_2darray",
                                            "text": "2D array",
                                        },
                                        {
                                            "value": "value_text",
                                            "text": "text",
                                        },
                                        {
                                            "value": "value_file",
                                            "text": "Pointer to a file",
                                        }
                                    ],
                                },
                            ],
                            "detailElements": [
                                {
                                    "type": "checkbox",
                                    "name": "calibration_conditions",
                                    "title": (
                                        "Please select the experimental factors (these are defined in the Method page)"
                                    ),
                                    "choicesFromQuestion": "conditions",
                                    "_visibleIf": "{conditions.rowCount} > 0",
                                    "minSelectedChoices": 0,
                                },
                            ],
                            "detailPanelMode": "underRowSingle",
                            "cellType": "text",
                            "rowCount": 1,
                            "allowRowsDragAndDrop": True,
                        },
                        {
                            "type": "matrixdynamic",
                            "name": "raw_data_report",
                            "visibleIf": "{data_sheets} contains 'data_raw'",
                            "title": "Unprocessed (Raw data) reporting",
                            "addRowtext": "Add empty row",
                            "description": (
                                "Please provide information of the parameters"
                                " reported as unprocessed data (e.g. Absorbance, AU)."
                                " Use the + button to specify which factors are varied."
                                " If your data is in separate files you "
                                "may use the 'Pointer to file' type."
                            ),
                            "requiredIf": "{data_sheets} contains 'data_raw'",
                            "showCommentArea": True,
                            "columns": [
                                {
                                    "name": "raw_endpoint",
                                    "title": "Name",
                                    "isRequired": True,
                                },
                                {
                                    "name": "raw_aggregate",
                                    "title": "Mark if aggregated",
                                    "cellType": "dropdown",
                                    "isRequired": False,
                                    "defaultvalue": "RAW_DATA",
                                    "choices": [
                                        {
                                            "value": "RAW_DATA",
                                            "text": "Raw data",
                                        },
                                        {
                                            "value": "MEAN",
                                            "text": "Mean",
                                        },
                                        {
                                            "value": "MEDIAN",
                                            "text": "Median",
                                        },
                                        {
                                            "value": "MODE",
                                            "text": "Mode",
                                        },
                                        {
                                            "value": "AGGREGATED",
                                            "text": "Aggregated",
                                        },
                                        {
                                            "value": "NORMALIZED",
                                            "text": "Normalized",
                                        },
                                        {
                                            "value": "",
                                            "text": "Other",
                                        },
                                    ],
                                },
                                {
                                    "name": "raw_unit",
                                    "title": "Unit",
                                },
                                {
                                    "name": "raw_endpoint_uncertainty",
                                    "title": "Uncertainty",
                                    "cellType": "dropdown",
                                    "isRequired": False,
                                    "choices": [
                                        {
                                            "value": "none",
                                            "text": "",
                                        },
                                        {
                                            "value": "SD",
                                            "text": "Standard Deviation",
                                        },
                                    ],
                                },
                                {
                                    "name": "raw_type",
                                    "title": "Type",
                                    "cellType": "dropdown",
                                    "isRequired": True,
                                    "defaultvalue": "value_num",
                                    "choices": [
                                        {
                                            "value": "value_num",
                                            "text": "numeric",
                                        },
                                        {
                                            "value": "value_spectrum",
                                            "text": "spectrum",
                                        },
                                        {
                                            "value": "value_timeseries",
                                            "text": "time series",
                                        },
                                        {
                                            "value": "value_image",
                                            "text": "image",
                                        },
                                        {
                                            "value": "value_1darray",
                                            "text": "1D array",
                                        },
                                        {
                                            "value": "value_2darray",
                                            "text": "2D array",
                                        },
                                        {
                                            "value": "value_text",
                                            "text": "text",
                                        },
                                        {
                                            "value": "value_file",
                                            "text": "Pointer to a file",
                                        },
                                        {
                                            "value": "value_database",
                                            "text": (
                                                "Link to a database entry (e.g. GEO)"
                                            ),
                                        },
                                    ],
                                },
                            ],
                            "detailElements": [
                                {
                                    "type": "checkbox",
                                    "name": "raw_conditions",
                                    "title": (
                                        "Please select the experimental factors"
                                        " (these are defined in the Method page)"
                                    ),
                                    "choicesFromQuestion": "conditions",
                                    "_visibleIf": "{conditions.rowCount} > 0",
                                    "minSelectedChoices": 0,
                                },
                            ],
                            "detailPanelMode": "underRowSingle",
                            "cellType": "text",
                            "rowCount": 1,
                            "allowRowsDragAndDrop": True,
                        },
                        {
                            "type": "matrixdynamic",
                            "name": "question3",
                            "addRowtext": "Add empty row",
                            "title": "Results reporting",
                            "visibleIf": "{data_sheets} contains 'data_processed'",
                            "description": (
                                "Please provide information of the endpoints"
                                " or descriptors reported as experimental results"
                                " e.g. Cell viability , %. "
                                "If your data is in separate files you may use"
                                " the 'Pointer to file' type."
                            ),
                            "requiredIf": "{data_sheets} contains 'data_processed'",
                            "showCommentArea": True,
                            "columns": [
                                {
                                    "name": "result_name",
                                    "title": "Name",
                                    "isRequired": True,
                                },
                                {
                                    "name": "result_aggregate",
                                    "title": "Mark if aggregated",
                                    "cellType": "dropdown",
                                    "isRequired": False,
                                    "defaultvalue": "",
                                    "choices": [
                                        {
                                            "value": "MEAN",
                                            "text": "Mean",
                                        },
                                        {
                                            "value": "MEDIAN",
                                            "text": "Median",
                                        },
                                        {
                                            "value": "MODE",
                                            "text": "Mode",
                                        },
                                        {
                                            "value": "PEAK",
                                            "text": "Peak",
                                        },
                                        {
                                            "value": "MAX",
                                            "text": "Max",
                                        },
                                        {
                                            "value": "MIN",
                                            "text": "Min",
                                        },
                                        {
                                            "value": "D25",
                                            "text": "D25",
                                        },
                                        {
                                            "value": "D90",
                                            "text": "D90",
                                        },
                                        {
                                            "value": "AGGREGATED",
                                            "text": "Aggregated",
                                        },
                                        {
                                            "value": "NORMALIZED",
                                            "text": "Normalized",
                                        },
                                        {
                                            "value": "NORMALIZED_TO_CONTROL",
                                            "text": "Normalized to control",
                                        },
                                        {
                                            "value": "RELATIVE_TO_CONTROL",
                                            "text": "Relative to control",
                                        },
                                        {
                                            "value": "FOLD_CHANGE",
                                            "text": "Fold change",
                                        },
                                        {
                                            "value": "HIGHEST_DOSE",
                                            "text": "Highest dose",
                                        },
                                        {
                                            "value": "Z-AVERAGE",
                                            "text": "Z-AVERAGE",
                                        },
                                        {
                                            "value": "INTENSITY-WEIGHTED",
                                            "text": "INTENSITY-WEIGHTED",
                                        },
                                        {
                                            "value": "NUMBER-BASED",
                                            "text": "NUMBER-BASED",
                                        },
                                        {
                                            "value": "TOTAL",
                                            "text": "TOTAL",
                                        },
                                        {
                                            "value": "GEOMETRIC_MEAN",
                                            "text": "Geometric mean",
                                        },
                                        {
                                            "value": "OTHER",
                                            "text": "Other",
                                        },
                                    ],
                                },
                                {
                                    "name": "result_unit",
                                    "title": "Unit",
                                },
                                {
                                    "name": "result_endpoint_uncertainty",
                                    "title": "Uncertainty",
                                    "cellType": "dropdown",
                                    "isRequired": False,
                                    "defaultvalue": "",
                                    "choices": [
                                        {
                                            "value": "",
                                            "text": "None",
                                        },
                                        {
                                            "value": "SD",
                                            "text": "Standard Deviation",
                                        },
                                    ],
                                },
                                {
                                    "name": "result_type",
                                    "title": "Type",
                                    "cellType": "dropdown",
                                    "isRequired": True,
                                    "defaultvalue": "value_num",
                                    "choices": [
                                        {
                                            "value": "value_num",
                                            "text": "numeric",
                                        },
                                        {
                                            "value": "value_spectrum",
                                            "text": "spectrum",
                                        },
                                        {
                                            "value": "value_timeseries",
                                            "text": "time series",
                                        },
                                        {
                                            "value": "value_image",
                                            "text": " image",
                                        },
                                        {
                                            "value": "value_1darray",
                                            "text": "1D array",
                                        },
                                        {
                                            "value": "value_2darray",
                                            "text": "2D array",
                                        },
                                        {
                                            "value": "value_text",
                                            "text": "text",
                                        },
                                        {
                                            "value": "value_num",
                                            "text": "numeric",
                                        },
                                        {
                                            "value": "value_spectrum",
                                            "text": "spectrum",
                                        },
                                        {
                                            "value": "value_timeseries",
                                            "text": "time series",
                                        },
                                        {
                                            "value": "value_image",
                                            "text": "image",
                                        },
                                        {
                                            "value": "value_1darray",
                                            "text": "1D array",
                                        },
                                        {
                                            "value": "value_2darray",
                                            "text": "2D array",
                                        },
                                        {
                                            "value": "value_file",
                                            "text": "Pointer to a file",
                                        },
                                        {
                                            "value": "value_database",
                                            "text": (
                                                "Link to a database entry (e.g. GEO)"
                                            ),
                                        },
                                    ],
                                },
                            ],
                            "detailElements": [
                                {
                                    "type": "checkbox",
                                    "name": "results_conditions",
                                    "title": (
                                        "Please select the experimental factors"
                                        " (these are defined in the Method page)"
                                    ),
                                    "choicesFromQuestion": "conditions",
                                    "_visibleIf": "{conditions.rowCount} > 0",
                                    "minSelectedChoices": 0,
                                },
                            ],
                            "detailPanelMode": "underRowSingle",
                            "cellType": "text",
                            "rowCount": 1,
                            "minRowCount": 1,
                            "confirmDelete": True,
                            "allowRowsDragAndDrop": True,
                        },
                    ],
                    "startWithNewLine": False,
                },
            ],
            "title": "[{template_name}]: Results",
            "navigationTitle": "2. Results",
            "description": (
                "Please describe the results expected from method [{METHOD}]"
            ),
        },
        {
            "name": "page_methodparams",
            "elements": [
                {
                    "type": "matrixdynamic",
                    "name": "METADATA_PARAMETERS",
                    "title": "[{METHOD}] Define method parameters",
                    "titleLocation": "top",
                    "isRequired": True,
                    "showCommentArea": True,
                    "columns": [
                        {
                            "name": "param_name",
                            "title": "Param name",
                            "cellType": "text",
                            "isRequired": True,
                            "isUnique": True,
                        },
                        {
                            "name": "param_unit",
                            "title": "Unit",
                        },
                        {
                            "name": "param_group",
                            "title": "Group",
                            "cellType": "dropdown",
                            "choices": [
                                "INSTRUMENT",
                                "MEASUREMENT CONDITIONS",
                                "ENVIRONMENT",
                                "MEDIUM",
                                "SPECIES",
                                "CELL LINE DETAILS",
                                "CULTURE CONDITIONS",
                                "MONITORING",
                                "CALIBRATION",
                                {
                                    "value": "OTHER_METADATA",
                                    "text": "OTHER METADATA",
                                },
                                "RESULT_ANALYSIS",
                            ],
                        },
                        {
                            "name": "param_type",
                            "title": "Type",
                            "cellType": "dropdown",
                            "choices": [
                                {
                                    "value": "value_num",
                                    "text": "numeric",
                                },
                                {
                                    "value": "value_text",
                                    "text": "text",
                                },
                                {
                                    "value": "value_boolean",
                                    "text": "yes/no",
                                },
                            ],
                        },
                    ],
                    "detailElements": [
                        {
                            "type": "text",
                            "name": "param_hint",
                            "title": "Hint, description",
                        },
                        {
                            "type": "text",
                            "name": "param_subgroup",
                            "title": "Subgroup (if any)",
                        },
                    ],
                    "detailPanelMode": "underRowSingle",
                    "cellType": "text",
                    "rowCount": 1,
                    "minRowCount": 1,
                    "confirmDelete": True,
                    "addRowtext": "Add parameter",
                    "detailPanelShowOnAdding": True,
                    "allowRowsDragAndDrop": True,
                },
            ],
            "navigationTitle": "3. Method parameters",
            "navigationDescription": "Method and instrument parameters",
            "title": "[{template_name}]: Method parameters",
            "description": "Please describe all relevant [{METHOD}] parameters",
        },
        {
            "name": "page_sampleinfo",
            "elements": [
                {
                    "type": "matrixdynamic",
                    "name": "METADATA_SAMPLE_INFO",
                    "title": "[{METHOD}] Samples/Materials description",
                    "titleLocation": "top",
                    "isRequired": True,
                    "showCommentArea": False,
                    "columns": [
                        {
                            "name": "param_sample_name",
                            "title": "Parameter name",
                            "cellType": "text",
                            "isRequired": True,
                            "isUnique": True,
                        },
                        {
                            "name": "param_sample_group",
                            "title": "Group",
                            "cellType": "dropdown",
                            "choices": [
                                {
                                    "value": "ID",
                                    "text": "Identifier",
                                },
                                {
                                    "value": "NAME",
                                    "text": "Name",
                                },
                                {
                                    "value": "CASRN",
                                    "text": "CAS RN",
                                },
                                {
                                    "value": "BATCH",
                                    "text": "Batch",
                                },
                                {
                                    "value": "SUPPLIER",
                                    "text": "Supplier",
                                },
                                {
                                    "value": "SUPPLIER identifier",
                                    "text": "Supplier identifier",
                                },
                                {
                                    "value": "OTHER_METADATA",
                                    "text": "Other",
                                },
                            ],
                        },
                    ],
                    "defaultvalue": [
                        {
                            "param_sample_name": "Material ID",
                            "param_sample_group": "ID",
                        },
                        {
                            "param_sample_name": "Material name",
                            "param_sample_group": "NAME",
                        },
                        {
                            "param_sample_name": "Material supplier",
                            "param_sample_group": "SUPPLIER",
                        },
                    ],
                    "detailPanelMode": "underRowSingle",
                    "cellType": "text",
                    "rowCount": 3,
                    "minRowCount": 3,
                    "confirmDelete": True,
                    "addRowtext": "Add material identifier",
                    "detailPanelShowOnAdding": True,
                    "allowRowsDragAndDrop": True,
                },
            ],
            "navigationTitle": "4. Sample",
            "navigationDescription": "Sample description",
            "title": "[{template_name}]: Sample details",
            "description": "Parameters to desribe the materials tested by [{METHOD}]",
        },
        {
            "name": "page_sampleprep",
            "elements": [
                {
                    "type": "matrixdynamic",
                    "name": "METADATA_SAMPLE_PREP",
                    "title": "[{METHOD}] Sample preparation description",
                    "titleLocation": "top",
                    "isRequired": True,
                    "showCommentArea": True,
                    "columns": [
                        {
                            "name": "param_sampleprep_name",
                            "title": "Param name",
                            "cellType": "text",
                            "isRequired": True,
                            "isUnique": True,
                        },
                        {
                            "name": "param_sampleprep_unit",
                            "title": "Unit",
                        },
                        {
                            "name": "param_sampleprep_group",
                            "title": "Group",
                            "cellType": "dropdown",
                            "isRequired": True,
                            "choices": [
                                {
                                    "value": "DISPERSION",
                                    "text": "Dispersion",
                                },
                                {
                                    "value": "INCUBATION",
                                    "text": "Incubation",
                                },
                                {
                                    "value": "ALI_EXPOSURE",
                                    "text": "Air-liquid interface exposure",
                                },
                                {
                                    "value": "OTHER_SAMPLEPREP",
                                    "text": "Other",
                                },
                            ],
                        },
                        {
                            "name": "param_type",
                            "title": "Type",
                            "cellType": "dropdown",
                            "choices": [
                                {
                                    "value": "value_num",
                                    "text": "numeric",
                                },
                                {
                                    "value": "value_text",
                                    "text": "text",
                                },
                                {
                                    "value": "value_comment",
                                    "text": "long_text",
                                },
                                {
                                    "value": "value_boolean",
                                    "text": "yes/no",
                                },
                                {
                                    "value": "value_date",
                                    "text": "date",
                                },
                            ],
                        },
                    ],
                    "detailElements": [
                        {
                            "type": "text",
                            "name": "param_sampleprep_hint",
                            "title": "Hint, description",
                        },
                        {
                            "type": "text",
                            "name": "param_sampleprep_subgroup",
                            "title": "Subgroup (if any)",
                        },
                    ],
                    "detailPanelMode": "underRowSingle",
                    "cellType": "text",
                    "rowCount": 1,
                    "minRowCount": 1,
                    "confirmDelete": True,
                    "addRowtext": "Add parameter",
                    "detailPanelShowOnAdding": True,
                    "allowRowsDragAndDrop": True,
                },
            ],
            "title": "[{template_name}]: Sample preparation",
            "description": "Details of sample preparation to be tested by [{METHOD}]",
            "navigationTitle": "5. Sample preparation",
            "navigationDescription": "Sample preparation",
        },
        {
            "name": "page_provenance",
            "title": "[{template_name}]: Who and when did the experiment",
            "description": (
                "Predefined fields for reference.\n"
                " You may enter default values."
                " The user can change the values in the template"
            ),
            "navigationTitle": "6. Provenance",
            "navigationDescription": "Predefined fields describing provenance",
            "elements": [
                {
                    "type": "text",
                    "name": "provenance_project",
                    "startWithNewLine": False,
                    "visible": True,
                    "readOnly": False,
                    "title": "Project",
                },
                {
                    "type": "text",
                    "name": "provenance_workpackage",
                    "startWithNewLine": False,
                    "visible": True,
                    "readOnly": False,
                    "title": "Work package",
                },
                {
                    "type": "text",
                    "name": "provenance_provider",
                    "startWithNewLine": True,
                    "visible": True,
                    "readOnly": True,
                    "title": "Partner/test facility",
                },
                {
                    "type": "text",
                    "name": "provenance_contact",
                    "startWithNewLine": False,
                    "visible": True,
                    "readOnly": True,
                    "title": "Lead Scientist & contact for test",
                },
                {
                    "type": "text",
                    "name": "provenance_operator",
                    "startWithNewLine": False,
                    "visible": True,
                    "readOnly": True,
                    "title": "Assay/Test work conducted by",
                },
                {
                    "type": "text",
                    "inputType": "date",
                    "name": "provenance_startdate",
                    "startWithNewLine": True,
                    "visible": True,
                    "readOnly": True,
                    "title": "Test start date",
                },
                {
                    "type": "text",
                    "inputType": "date",
                    "name": "provenance_enddate",
                    "startWithNewLine": False,
                    "visible": True,
                    "readOnly": True,
                    "title": "Test end date",
                },
            ],
        },
        {
            "name": "page_formats",
            "elements": [
                {
                    "type": "radiogroup",
                    "name": "template_layout",
                    "visible": True,
                    "title": "Template layout",
                    "defaultvalue": "{preferred_layout}",
                    "startWithNewLine": True,
                    "choices": [
                        {
                            "value": "dose_response",
                            "text": "Dose response",
                        },
                        {
                            "value": "pchem",
                            "text": "Physchem characterisaiton",
                        },
                    ],
                    "colCount": 1,
                },
                {
                    "type": "html",
                    "name": "help_layout_dose_response",
                    "titleLocation": "hidden",
                    "visibleIf": "{template_layout} == 'dose_response'",
                    "html": (
                        "This layout is appropriate when there are a number"
                        " of experimental factors, e.g. concentration, time,"
                        " as well as a single set of parameters like "
                        "instrument, medium, temperature, cell type."
                    ),
                    "readOnly": True,
                },
                {
                    "type": "html",
                    "name": "help_layout_pchem",
                    "titleLocation": "hidden",
                    "visibleIf": "{template_layout} == 'pchem'",
                    "html": (
                        "This layout is appropriate when there are no"
                        " experimental factors (but there could be multiple"
                        " set of parameters like instrument, medium, temperature)."
                    ),
                    "readOnly": True,
                },
            ],
            "title": "[{template_name}]: Template layout",
            "description": "Select from several supported layouts",
            "navigationTitle": "7. Layout",
            "navigationDescription": "Select the most appropriate Excel layout",
        },
        {
            "name": "page_preview",
            "elements": [
                {
                    "type": "checkbox",
                    "name": "confirm_statuschange",
                    "title": "Please confirm",
                    "description": (
                        "A finalized blueprint will become readonly."
                        " You will be able to generate Excel templates,"
                        " share the blueprint and make copies of the blueprint."
                    ),
                    "visibleIf": "{user_role} contains 'role_datamgr'",
                    "choices": [
                        {
                            "value": "FINALIZED",
                            "text": (
                                "I agree to finalize the"
                                " ['{template_name}'] template blueprint"
                            ),
                        },
                    ],
                },
                {
                    "type": "text",
                    "inputType": "date",
                    "name": "template_date",
                    "description": "Please select the date",
                    "startWithNewLine": False,
                    "visible": True,
                    "readOnly": False,
                    "title": "Template finalized at",
                    "requiredIf": "{confirm_statuschange} contains 'FINALIZED'",
                    "visibleIf": "{confirm_statuschange} contains 'FINALIZED'",
                    "defaultValueExpression": "today()",
                },
                {
                    "type": "text",
                    "name": "template_author_orcid",
                    "visible": True,
                    "startWithNewLine": True,
                    "title": "Template Author ORCID",
                    "description": (
                        "ORCID is optional for draft blueprints but required"
                        " to finalize the blueprint."
                    ),
                    "requiredIf": "{confirm_statuschange} contains 'FINALIZED'",
                    "validators": [
                        {
                            "type": "expression",
                            "expression": "isValidOrcid({template_author_orcid})",
                            "text": "Please enter a valid ORCID.",
                        },
                    ],
                },
                {
                    "type": "text",
                    "valueName": "METHOD",
                    "visibleIf": "{confirm_statuschange} contains 'FINALIZED'",
                    "startWithNewLine": True,
                    "title": "METHOD",
                    "isRequired": True,
                },
                {
                    "type": "text",
                    "valueName": "EXPERIMENT",
                    "visibleIf": "{confirm_statuschange} contains 'FINALIZED'",
                    "startWithNewLine": False,
                    "title": "{SOP}",
                    "isRequired": True,
                },
                {
                    "type": "radiogroup",
                    "name": "template_status",
                    "readOnly": True,
                    "isRequired": True,
                    "_tmp": "{user_role} contains 'role_lab'",
                    "visible": True,
                    "title": "Template status",
                    "defaultvalue": "DRAFT",
                    "startWithNewLine": True,
                    "choices": [
                        {
                            "value": "DRAFT",
                            "text": "Draft",
                        },
                        {
                            "value": "FINALIZED",
                            "text": "Finalized",
                        },
                    ],
                    "colCount": 1,
                },
                {
                    "type": "text",
                    "name": "template_uuid",
                    "startWithNewLine": False,
                    "visible": False,
                    "readOnly": False,
                    "title": "Internal identifier",
                },
                {
                    "type": "text",
                    "name": "parent_uuid",
                    "startWithNewLine": False,
                    "visible": False,
                    "readOnly": True,
                    "title": "Internal identifier of the copied template (if any)",
                },
            ],
            "title": "[{template_name}]: Preview/Finalize",
            "description": (
                "A finalized blueprint will become readonly. "
                "You will be able to generate Excel templates,"
                " share the blueprint and make copies of the blueprint."
            ),
            "navigationTitle": "8. Preview/Finalize",
            "navigationDescription": "Predefined fields describing provenance",
        },
    ],
    "showPrevButton": True,
    "showQuestionNumbers": "off",
    "showTOC": True,
    "goNextPageAutomatic": False,
    "widthMode": "responsive",
    "fitToContainer": True,
    "headerView": "advanced",
    "calculatedValues": [
        {
            "name": "preferred_layout",
            "expression": "iif({PROTOCOL_TOP_CATEGORY}='TOX','dose_response','pchem')",
        },
    ],
}
