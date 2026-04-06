"""
data_entry_survey.py
====================
Generates a SurveyJS survey definition that lets a researcher enter *values*
for a specific blueprint produced by template_designer.py.

Usage
-----
    from data_entry_survey import blueprint_to_data_entry_survey
    import json

    with open("my_blueprint.json") as f:
        bp = json.load(f)

    survey = blueprint_to_data_entry_survey(bp)

    # Use survey in your front-end as the SurveyJS model JSON.
    print(json.dumps(survey, indent=2))

Survey structure (pages)
------------------------
Page 0 – Experiment identity
    • Read-only display of blueprint metadata (method, SOP, study type, author).
    • Provenance fields (operator, facility, project, dates).

Page 1 – Sample / Material
    • One question per METADATA_SAMPLE_INFO parameter (type = text).

Page 2 – Sample preparation
    • One question per METADATA_SAMPLE_PREP parameter, grouped by param_sampleprep_group.
    • Input type driven by param_type (numeric → text with inputType number, boolean → radiogroup, date → text inputType date, long_text → comment).

Page 3 – Method / Instrument parameters
    • One question per METADATA_PARAMETERS entry, grouped by param_group.
    • Same type mapping as above.

Page 4 – Experimental conditions / factors
    • One matrixdynamic row per condition defined in blueprint["conditions"].
    • Columns: condition label (read-only), value, unit (pre-filled, read-only).

Page 5 – Results  (present only when data_sheets contains 'data_processed')
    • matrixdynamic with one row per result endpoint defined in question3.
    • Columns: endpoint name (read-only), value (numeric text), unit (pre-filled), uncertainty value.

Page 6 – Raw data  (present only when data_sheets contains 'data_raw')
    • matrixdynamic with one row per raw endpoint defined in raw_data_report.

Page 7 – Calibration  (present only when data_sheets contains 'data_calibration')
    • matrixdynamic with one row per calibration entry.

All blueprint-defined names / labels are rendered as read-only display titles so
the researcher knows exactly what to fill in, and the question names follow the
convention  <section>__<param_name_slug>  to allow straightforward round-tripping.
"""

import re
import json
from copy import deepcopy
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    """Convert a human-readable label to a safe SurveyJS question name."""
    return re.sub(r"[^A-Za-z0-9_]", "_", str(text).strip()).lower()


def _param_type_to_question(name: str, title: str, param_type: str,
                             unit: str = "", hint: str = "",
                             required: bool = False,
                             start_new_line: bool = True) -> Dict:
    """
    Map blueprint param_type → a SurveyJS question element.

    param_type values used in template_designer:
        value_num     → text (inputType: number)
        value_text    → text
        value_boolean → radiogroup (Yes / No)
        value_date    → text (inputType: date)
        value_comment → comment (long text)
    """
    base = {
        "name": name,
        "title": title,
        "startWithNewLine": start_new_line,
        "isRequired": required,
    }
    if hint:
        base["description"] = hint
    if unit:
        base["description"] = (base.get("description", "") + f"  [unit: {unit}]").strip()

    if param_type in ("value_num", "numeric"):
        base["type"] = "text"
        base["inputType"] = "number"
    elif param_type in ("value_boolean", "yes/no"):
        base["type"] = "radiogroup"
        base["choices"] = [{"value": "yes", "text": "Yes"},
                            {"value": "no",  "text": "No"}]
        base["colCount"] = 2
    elif param_type in ("value_date", "date"):
        base["type"] = "text"
        base["inputType"] = "date"
    elif param_type in ("value_comment", "long_text"):
        base["type"] = "comment"
    else:
        # value_text, free text, unknown → plain text input
        base["type"] = "text"

    return base


def _panel(name: str, title: str, elements: List[Dict],
           description: str = "") -> Dict:
    p = {
        "type": "panel",
        "name": name,
        "title": title,
        "elements": elements,
        "state": "expanded",
    }
    if description:
        p["description"] = description
    return p


def _readonly_html(name: str, html: str) -> Dict:
    return {
        "type": "html",
        "name": name,
        "titleLocation": "hidden",
        "html": html,
        "readOnly": True,
    }


def _info_badge(label: str, value: Any) -> str:
    v = value if value else "<em>not specified</em>"
    return (f"<div style='margin:4px 0'>"
            f"<b>{label}:</b> <span style='color:#333'>{v}</span></div>")


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def _page_identity(bp: Dict) -> Dict:
    """Page 0 – read-only summary of the blueprint + provenance inputs."""
    method       = bp.get("METHOD", "")
    experiment   = bp.get("EXPERIMENT", "")
    sop          = bp.get("SOP", "")
    top_cat      = bp.get("PROTOCOL_TOP_CATEGORY", "")
    cat_code     = bp.get("PROTOCOL_CATEGORY_CODE", "")
    template_name = bp.get("template_name", "")
    author       = bp.get("template_author", "")
    ack          = bp.get("template_acknowledgment", "")

    summary_html = (
        "<div class='alert alert-info' style='font-size:0.9em;padding:10px'>"
        "<b>Blueprint summary</b><br>"
        + _info_badge("Template", template_name)
        + _info_badge("Method (acronym)", method)
        + _info_badge("Protocol", experiment)
        + _info_badge("Protocol type", sop)
        + _info_badge("Study type", top_cat)
        + _info_badge("Category code", cat_code)
        + _info_badge("Blueprint author", author)
        + _info_badge("Acknowledgment", ack)
        + "</div>"
    )

    elements = [
        _readonly_html("de_blueprint_summary", summary_html),
        # ----- editable provenance -----
        {
            "type": "text",
            "name": "de_provenance_operator",
            "title": "Operator / person conducting the experiment",
            "isRequired": True,
            "startWithNewLine": True,
            "defaultValue": bp.get("provenance_operator", ""),
        },
        {
            "type": "text",
            "name": "de_provenance_provider",
            "title": "Partner / test facility",
            "startWithNewLine": False,
            "defaultValue": bp.get("provenance_provider", ""),
        },
        {
            "type": "text",
            "name": "de_provenance_contact",
            "title": "Lead scientist & contact",
            "startWithNewLine": True,
            "defaultValue": bp.get("provenance_contact", ""),
        },
        {
            "type": "text",
            "name": "de_provenance_project",
            "title": "Project",
            "startWithNewLine": False,
            "defaultValue": bp.get("provenance_project", ""),
        },
        {
            "type": "text",
            "name": "de_provenance_workpackage",
            "title": "Work package",
            "startWithNewLine": False,
            "defaultValue": bp.get("provenance_workpackage", ""),
        },
        {
            "type": "text",
            "inputType": "date",
            "name": "de_provenance_startdate",
            "title": "Test start date",
            "isRequired": True,
            "startWithNewLine": True,
            "defaultValueExpression": "today()",
        },
        {
            "type": "text",
            "inputType": "date",
            "name": "de_provenance_enddate",
            "title": "Test end date",
            "startWithNewLine": False,
        },
    ]

    return {
        "name": "de_page_identity",
        "title": f"[{template_name}] Experiment identity & provenance",
        "description": "Confirm who performed the experiment and when.",
        "navigationTitle": "Identity",
        "navigationDescription": "Operator, facility, dates",
        "elements": elements,
    }


def _page_sample(bp: Dict) -> Optional[Dict]:
    """Page 1 – sample / material identifiers."""
    sample_info = bp.get("METADATA_SAMPLE_INFO", [])
    if not sample_info:
        return None

    elements = []
    for i, param in enumerate(sample_info):
        name  = param.get("param_sample_name", f"sample_param_{i}")
        group = param.get("param_sample_group", "")
        q = {
            "type": "text",
            "name": f"de_sample__{_slug(name)}",
            "title": name,
            "description": f"Group: {group}" if group else "",
            "startWithNewLine": True,
            "isRequired": i == 0,   # require at least the first identifier
        }
        elements.append(q)

    return {
        "name": "de_page_sample",
        "title": f"[{bp.get('METHOD','')}] Sample / Material details",
        "description": "Fill in the identifiers for the material(s) tested.",
        "navigationTitle": "Sample",
        "navigationDescription": "Material identifiers",
        "elements": elements,
    }


def _page_sample_prep(bp: Dict) -> Optional[Dict]:
    """Page 2 – sample preparation parameters."""
    sample_prep = bp.get("METADATA_SAMPLE_PREP", [])
    if not sample_prep:
        return None

    # Group by param_sampleprep_group
    groups: Dict[str, List] = {}
    for param in sample_prep:
        grp = param.get("param_sampleprep_group", "OTHER_SAMPLEPREP")
        groups.setdefault(grp, []).append(param)

    GROUP_LABELS = {
        "DISPERSION": "Dispersion",
        "INCUBATION": "Incubation",
        "ALI_EXPOSURE": "Air-liquid interface exposure",
        "OTHER_SAMPLEPREP": "Other sample preparation",
    }

    panels = []
    for grp, params in groups.items():
        panel_elements = []
        for i, param in enumerate(params):
            name      = param.get("param_sampleprep_name", f"sp_{i}")
            unit      = param.get("param_sampleprep_unit", "")
            hint      = param.get("param_sampleprep_hint", "")
            ptype     = param.get("param_type", "value_text")
            subgroup  = param.get("param_sampleprep_subgroup", "")
            full_hint = hint
            if subgroup:
                full_hint = (f"{hint}  Subgroup: {subgroup}").strip()
            q = _param_type_to_question(
                name=f"de_sampleprep__{_slug(name)}",
                title=name,
                param_type=ptype,
                unit=unit,
                hint=full_hint,
                start_new_line=(i % 2 == 0),
            )
            panel_elements.append(q)

        panels.append(_panel(
            name=f"de_sampleprep_panel_{_slug(grp)}",
            title=GROUP_LABELS.get(grp, grp),
            elements=panel_elements,
        ))

    return {
        "name": "de_page_sampleprep",
        "title": f"[{bp.get('METHOD','')}] Sample preparation",
        "description": "Enter sample preparation parameters.",
        "navigationTitle": "Sample prep",
        "navigationDescription": "Sample preparation parameters",
        "elements": panels,
    }


def _page_method_params(bp: Dict) -> Optional[Dict]:
    """Page 3 – method / instrument parameters."""
    method_params = bp.get("METADATA_PARAMETERS", [])
    if not method_params:
        return None

    # Group by param_group
    groups: Dict[str, List] = {}
    for param in method_params:
        grp = param.get("param_group", "OTHER_METADATA")
        groups.setdefault(grp, []).append(param)

    panels = []
    for grp, params in groups.items():
        panel_elements = []
        for i, param in enumerate(params):
            name     = param.get("param_name", f"p_{i}")
            unit     = param.get("param_unit", "")
            hint     = param.get("param_hint", "")
            subgroup = param.get("param_subgroup", "")
            ptype    = param.get("param_type", "value_text")
            full_hint = hint
            if subgroup:
                full_hint = (f"{hint}  Subgroup: {subgroup}").strip()
            q = _param_type_to_question(
                name=f"de_params__{_slug(name)}",
                title=name,
                param_type=ptype,
                unit=unit,
                hint=full_hint,
                start_new_line=(i % 2 == 0),
            )
            panel_elements.append(q)

        panels.append(_panel(
            name=f"de_params_panel_{_slug(grp)}",
            title=str(grp),
            elements=panel_elements,
        ))

    return {
        "name": "de_page_methodparams",
        "title": f"[{bp.get('METHOD','')}] Method parameters",
        "description": "Enter instrument and measurement parameters.",
        "navigationTitle": "Method params",
        "navigationDescription": "Instrument & measurement parameters",
        "elements": panels,
    }


def _page_conditions(bp: Dict) -> Optional[Dict]:
    """Page 4 – experimental factors / conditions (one sub-panel per condition)."""
    conditions = bp.get("conditions", [])
    if not conditions:
        return None

    CONDITION_TYPE_LABELS = {
        "c_concentration":  "Concentration",
        "c_time":           "Time point",
        "c_replicate":      "Replicate",
        "c_replicate_tech": "Technical replicate",
        "c_replicate_bio":  "Biological replicate",
        "c_experiment":     "Experiment identifier",
        "c_other":          "Other condition",
    }

    elements: List[Dict] = []
    for cond in conditions:
        cname  = cond.get("conditon_name", "Condition")
        cunit  = cond.get("condition_unit", "")
        ctype  = cond.get("condition_type", "c_other")
        clabel = CONDITION_TYPE_LABELS.get(ctype, ctype)

        is_replicate = ctype.startswith("c_replicate")

        if is_replicate:
            # Replicate → integer
            q = {
                "type": "text",
                "inputType": "number",
                "name": f"de_condition__{_slug(cname)}",
                "title": cname,
                "description": clabel,
                "startWithNewLine": True,
            }
        else:
            # Concentration, time etc. → text with unit hint + series entry
            q = {
                "type": "matrixdynamic",
                "name": f"de_condition__{_slug(cname)}",
                "title": f"{cname} series",
                "description": (
                    f"Type: {clabel}. "
                    f"Enter one row per {cname} level tested."
                    + (f"  Unit: {cunit}" if cunit else "")
                ),
                "startWithNewLine": True,
                "rowCount": 3,
                "minRowCount": 1,
                "confirmDelete": True,
                "addRowText": f"Add {cname} level",
                "columns": [
                    {
                        "name": "cond_label",
                        "title": "Label / ID",
                        "cellType": "text",
                        "isRequired": True,
                    },
                    {
                        "name": "cond_value",
                        "title": f"Value{(' (' + cunit + ')') if cunit else ''}",
                        "cellType": "text",
                    },
                ],
            }
        elements.append(q)

    return {
        "name": "de_page_conditions",
        "title": f"[{bp.get('METHOD','')}] Experimental factors",
        "description": "Enter the levels / values for each experimental condition.",
        "navigationTitle": "Conditions",
        "navigationDescription": "Experimental factors & replicates",
        "elements": elements,
    }


def _endpoint_matrix(matrix_name: str, matrix_title: str, matrix_desc: str,
                     endpoints: List[Dict],
                     endpoint_name_key: str,
                     endpoint_unit_key: str,
                     endpoint_aggregate_key: str,
                     endpoint_uncertainty_key: str,
                     conditions: List[Dict]) -> Dict:
    """
    Build a matrixdynamic where:
      - Each row = one measurement (one replicate / one data point).
      - Columns = conditions  +  endpoint values (one column per endpoint).
      - Pre-populated defaultValue rows to guide the user.
    """
    # Build condition columns
    condition_cols: List[Dict] = []
    for cond in conditions:
        cname = cond.get("conditon_name", "cond")
        cunit = cond.get("condition_unit", "")
        condition_cols.append({
            "name": f"cond__{_slug(cname)}",
            "title": f"{cname}{(' (' + cunit + ')') if cunit else ''}",
            "cellType": "text",
        })

    # Build endpoint value columns
    endpoint_cols: List[Dict] = []
    for ep in endpoints:
        ep_name = ep.get(endpoint_name_key, "value")
        ep_unit = ep.get(endpoint_unit_key, "")
        ep_agg  = ep.get(endpoint_aggregate_key, "")
        ep_err  = ep.get(endpoint_uncertainty_key, "")
        col_title = ep_name
        if ep_unit:
            col_title += f" ({ep_unit})"
        if ep_agg and ep_agg not in ("RAW_DATA", "", "OTHER"):
            col_title += f" [{ep_agg}]"
        endpoint_cols.append({
            "name": f"ep__{_slug(ep_name)}",
            "title": col_title,
            "cellType": "text",
        })
        if ep_err and ep_err not in ("none", ""):
            endpoint_cols.append({
                "name": f"ep__{_slug(ep_name)}__err",
                "title": f"{ep_name} ± ({ep_err})",
                "cellType": "text",
            })

    all_columns = condition_cols + endpoint_cols

    return {
        "type": "matrixdynamic",
        "name": matrix_name,
        "title": matrix_title,
        "description": matrix_desc,
        "rowCount": 3,
        "minRowCount": 1,
        "confirmDelete": True,
        "addRowText": "Add measurement row",
        "allowRowsDragAndDrop": True,
        "showCommentArea": True,
        "columns": all_columns,
    }


def _page_results(bp: Dict) -> Optional[Dict]:
    """Page 5 – processed results."""
    data_sheets = bp.get("data_sheets", ["data_processed"])
    if "data_processed" not in data_sheets:
        return None
    endpoints = bp.get("question3", [])
    if not endpoints:
        return None
    conditions = bp.get("conditions", [])

    matrix = _endpoint_matrix(
        matrix_name="de_results",
        matrix_title="Processed results",
        matrix_desc=(
            "Enter one row per measurement / replicate. "
            "Condition columns help identify which treatment the row belongs to."
        ),
        endpoints=endpoints,
        endpoint_name_key="result_name",
        endpoint_unit_key="result_unit",
        endpoint_aggregate_key="result_aggregate",
        endpoint_uncertainty_key="result_endpoint_uncertainty",
        conditions=conditions,
    )

    return {
        "name": "de_page_results",
        "title": f"[{bp.get('METHOD','')}] Results",
        "description": "Enter processed / aggregated result values.",
        "navigationTitle": "Results",
        "navigationDescription": "Processed result values",
        "elements": [matrix],
    }


def _page_raw_data(bp: Dict) -> Optional[Dict]:
    """Page 6 – raw (unprocessed) data."""
    data_sheets = bp.get("data_sheets", [])
    if "data_raw" not in data_sheets:
        return None
    endpoints = bp.get("raw_data_report", [])
    if not endpoints:
        return None
    conditions = bp.get("conditions", [])

    matrix = _endpoint_matrix(
        matrix_name="de_raw_data",
        matrix_title="Raw (unprocessed) data",
        matrix_desc=(
            "Enter one row per measurement. "
            "Each row represents a single raw observation."
        ),
        endpoints=endpoints,
        endpoint_name_key="raw_endpoint",
        endpoint_unit_key="raw_unit",
        endpoint_aggregate_key="raw_aggregate",
        endpoint_uncertainty_key="raw_endpoint_uncertainty",
        conditions=conditions,
    )

    return {
        "name": "de_page_raw",
        "title": f"[{bp.get('METHOD','')}] Raw data",
        "description": "Enter unprocessed (raw) measurement values.",
        "navigationTitle": "Raw data",
        "navigationDescription": "Unprocessed measurement data",
        "elements": [matrix],
    }


def _page_calibration(bp: Dict) -> Optional[Dict]:
    """Page 7 – calibration curve data."""
    data_sheets = bp.get("data_sheets", [])
    if "data_calibration" not in data_sheets:
        return None
    endpoints = bp.get("calibration_report", [])
    if not endpoints:
        return None

    # Calibration uses its own varied factors (not the same as conditions)
    # We expose them as simple text columns alongside the calibration values.
    columns = [
        {
            "name": "cal_standard_label",
            "title": "Standard / level ID",
            "cellType": "text",
            "isRequired": True,
        },
    ]
    for ep in endpoints:
        ep_name = ep.get("calibration_entry", "value")
        ep_unit = ep.get("calibration_unit", "")
        col_title = ep_name + (f" ({ep_unit})" if ep_unit else "")
        columns.append({
            "name": f"cal__{_slug(ep_name)}",
            "title": col_title,
            "cellType": "text",
        })
        err = ep.get("calibration_entry_uncertainty", "none")
        if err and err != "none":
            columns.append({
                "name": f"cal__{_slug(ep_name)}__err",
                "title": f"{ep_name} ± ({err})",
                "cellType": "text",
            })

    matrix = {
        "type": "matrixdynamic",
        "name": "de_calibration",
        "title": "Calibration (standard) curve data",
        "description": "Enter one row per calibration standard level.",
        "rowCount": 5,
        "minRowCount": 2,
        "confirmDelete": True,
        "addRowText": "Add standard level",
        "allowRowsDragAndDrop": True,
        "columns": columns,
    }

    return {
        "name": "de_page_calibration",
        "title": f"[{bp.get('METHOD','')}] Calibration curve",
        "description": "Enter calibration standard values.",
        "navigationTitle": "Calibration",
        "navigationDescription": "Calibration curve data",
        "elements": [matrix],
    }


def _page_submission(bp: Dict) -> Dict:
    """Last page – submission notes."""
    return {
        "name": "de_page_submit",
        "title": "Submit data entry",
        "description": (
            "Review your entries before submitting. "
            "You can go back and correct any page."
        ),
        "navigationTitle": "Submit",
        "navigationDescription": "Review and submit",
        "elements": [
            {
                "type": "comment",
                "name": "de_notes",
                "title": "Additional notes / comments",
                "description": (
                    "Any remarks about this experiment run, "
                    "deviations from protocol, QC issues, etc."
                ),
            },
            {
                "type": "text",
                "name": "de_experiment_id",
                "title": "Experiment / run identifier",
                "description": "Internal lab notebook ID or LIMS reference for this run.",
                "isRequired": True,
            },
        ],
    }


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def blueprint_to_data_entry_survey(bp: Dict) -> Dict:
    """
    Convert a blueprint JSON (as produced / stored by template_designer.py)
    into a SurveyJS survey definition for *data entry*.

    Parameters
    ----------
    bp : dict
        The parsed JSON of a finalised (or draft) blueprint.

    Returns
    -------
    dict
        A SurveyJS-compatible survey definition.
    """
    method        = bp.get("METHOD", "experiment")
    template_name = bp.get("template_name", method)

    pages = []

    # Always present
    pages.append(_page_identity(bp))

    p = _page_sample(bp)
    if p:
        pages.append(p)

    p = _page_sample_prep(bp)
    if p:
        pages.append(p)

    p = _page_method_params(bp)
    if p:
        pages.append(p)

    p = _page_conditions(bp)
    if p:
        pages.append(p)

    p = _page_results(bp)
    if p:
        pages.append(p)

    p = _page_raw_data(bp)
    if p:
        pages.append(p)

    p = _page_calibration(bp)
    if p:
        pages.append(p)

    pages.append(_page_submission(bp))

    survey = {
        "title": f"Data entry – {template_name}",
        "description": (
            f"Enter experimental results for method: {method}. "
            f"This form was generated from blueprint '{template_name}'."
        ),
        "logoPosition": "right",
        "showPreviewBeforeComplete": "showAnsweredQuestions",
        "showPrevButton": True,
        "showQuestionNumbers": "off",
        "showTOC": True,
        "goNextPageAutomatic": False,
        "widthMode": "responsive",
        "fitToContainer": True,
        "headerView": "advanced",
        # Store blueprint provenance in a hidden field so the submitted JSON
        # can always be linked back to the blueprint that generated it.
        "pages": pages,
        "triggers": [],
        "calculatedValues": [
            {
                "name": "blueprint_method",
                "expression": f"'{method}'",
            },
            {
                "name": "blueprint_template_name",
                "expression": f"'{template_name}'",
            },
        ],
    }

    return survey


def apply_blueprint_customizations(df_info, df_result, df_conditions, json_blueprint):
    """
    Fill df_info, df_result, and df_conditions with default/custom values
    from the blueprint before writing to Excel.
    """
    # --- Method metadata ---
    method_meta = get_method_metadata(json_blueprint)
    df_info.loc[df_info['datamodel'] == 'METHOD', 'value'] = df_info.loc[df_info['datamodel'] == 'METHOD', 'param_name'].map(
        lambda x: method_meta.get(x, "")
    )

    # --- Sample metadata ---
    sample_meta = get_materials_metadata(json_blueprint)
    df_info.loc[df_info['datamodel'] == METADATA_SAMPLE_INFO, 'value'] = df_info.loc[df_info['datamodel'] == METADATA_SAMPLE_INFO, 'param_name'].map(
        lambda x: sample_meta.get(x, "")
    )

    # --- Sample prep metadata ---
    for prep in json_blueprint.get(METADATA_SAMPLE_PREP, []):
        mask = df_info['param_name'] == prep.get('param_sampleprep_name')
        df_info.loc[mask, 'value'] = prep.get('default_value', "")

    # --- Parameters ---
    for param in json_blueprint.get(METADATA_PARAMETERS, []):
        mask = df_info['param_name'] == param.get('param_name')
        df_info.loc[mask, 'value'] = param.get('default_value', "")

    # --- Treatments ---
    treatment_df = get_treatment(json_blueprint)
    for idx, row in df_info.iterrows():
        if row['param_name'] in treatment_df['param_name'].values:
            df_info.at[idx, 'value'] = treatment_df.loc[treatment_df['param_name'] == row['param_name'], 'value'].values[0]

    # --- Pre-fill results table if defaults exist ---
    if df_result is not None:
        for res in json_blueprint.get("question3", []):
            mask = df_result['result_name'] == res['result_name']
            if mask.any() and 'default_value' in res:
                # Fill first condition column with default
                conditions = res.get('results_conditions', [])
                if conditions:
                    first_cond = conditions[0]
                    if first_cond in df_result.columns:
                        df_result.loc[mask, first_cond] = res['default_value']

    # --- Fill units in df_conditions ---
    for idx, row in df_conditions.iterrows():
        df_conditions.at[idx, 'condition_unit'] = row.get('condition_unit', "")

    return df_info, df_result, df_conditions
    
# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python data_entry_survey.py <blueprint.json> [out.json]")
        sys.exit(1)
    with open(sys.argv[1]) as fh:
        blueprint = json.load(fh)
    survey_def = blueprint_to_data_entry_survey(blueprint)
    out_path = sys.argv[2] if len(sys.argv) > 2 else "data_entry_survey_output.json"
    with open(out_path, "w") as fh:
        json.dump(survey_def, fh, indent=2)
    print(f"Survey written to {out_path}")
    print(f"Pages: {[p['name'] for p in survey_def['pages']]}")
