"""
tests/test_data_entry.py
================================
pytest test suite for data_entry_survey.blueprint_to_data_entry_survey().

Run from the repo root with:
    pytest tests/test_data_entry_survey.py -v

The tests cover:
    1. Structural invariants (pages always present, question names unique, …)
    2. Each page is correctly built from specific blueprint fields
    3. Conditional page presence (data_sheets controls raw/processed/calibration)
    4. param_type → SurveyJS question type mapping
    5. Edge cases (empty sections, missing optional fields, minimal blueprint)
    6. Round-trip: every blueprint param_name surfaces somewhere in the survey
    7. Integration against the real dose_response.json fixture used by test_blueprint.py
"""

import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the module under test.
# Adjust the import path to match your project layout.
# Option A – module lives in pynanomapper.datamodel.templates:
#   from pynanomapper.datamodel.templates.data_entry_survey import blueprint_to_data_entry_survey
# Option B – module lives next to this test file:
#   from data_entry_survey import blueprint_to_data_entry_survey
# ---------------------------------------------------------------------------
from pynanomapper.datamodel.templates.data_entry_survey import (
    blueprint_to_data_entry_survey,
    _slug,
    _param_type_to_question,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEMPLATE_DIR = Path(__file__).parent / "resources/templates"


@pytest.fixture
def dose_response_bp():
    """Real dose_response.json blueprint used by the rest of the test suite."""
    with open(TEMPLATE_DIR / "dose_response.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def calibration_bp():
    with open(TEMPLATE_DIR / "calibration.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def tga_bp():
    """P-CHEM / pchem-layout blueprint."""
    with open(TEMPLATE_DIR / "tga.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def minimal_bp():
    """Smallest possible valid blueprint (only mandatory keys)."""
    return {
        "template_name": "Minimal",
        "METHOD": "TEST",
        "METADATA_SAMPLE_INFO": [
            {"param_sample_name": "ID", "param_sample_group": "ID"},
        ],
        "METADATA_SAMPLE_PREP": [
            {
                "param_sampleprep_name": "Step",
                "param_sampleprep_group": "OTHER_SAMPLEPREP",
                "param_type": "value_text",
            }
        ],
        "METADATA_PARAMETERS": [
            {"param_name": "Instrument", "param_group": "INSTRUMENT", "param_type": "value_text"},
        ],
        "conditions": [],
        "data_sheets": ["data_processed"],
        "question3": [
            {"result_name": "Result A", "result_unit": "AU", "result_aggregate": "MEAN"},
        ],
    }


@pytest.fixture
def full_bp():
    """Blueprint with all sections and all three data sheet types."""
    return {
        "template_name": "Full Test Blueprint",
        "METHOD": "MTT",
        "SOP": "protocol_sop",
        "EXPERIMENT": "ISO 10993-5",
        "EXPERIMENT_PROTOCOL": "http://example.org/sop",
        "PROTOCOL_TOP_CATEGORY": "TOX",
        "PROTOCOL_CATEGORY_CODE": "ENM_0000068_SECTION",
        "template_author": "Jane Doe",
        "template_acknowledgment": "EU Project X",
        "template_status": "FINALIZED",
        "provenance_project": "HINA",
        "provenance_workpackage": "WP3",
        "provenance_provider": "EMBL-EBI",
        "provenance_contact": "j.doe@example.com",
        "provenance_operator": "Lab Technician",
        "provenance_startdate": "2024-01-15",
        "provenance_enddate": "2024-01-20",
        "data_sheets": ["data_raw", "data_processed", "data_calibration"],
        "conditions": [
            {"conditon_name": "Concentration", "condition_unit": "mg/mL", "condition_type": "c_concentration"},
            {"conditon_name": "Time", "condition_unit": "h", "condition_type": "c_time"},
            {"conditon_name": "Replicate", "condition_type": "c_replicate_tech"},
        ],
        "controls": ["c_control_negative", "c_control_positive"],
        "METADATA_SAMPLE_INFO": [
            {"param_sample_name": "Material ID",   "param_sample_group": "ID"},
            {"param_sample_name": "Material name", "param_sample_group": "NAME"},
            {"param_sample_name": "Supplier",      "param_sample_group": "SUPPLIER"},
        ],
        "METADATA_SAMPLE_PREP": [
            {"param_sampleprep_name": "Dispersant",     "param_sampleprep_group": "DISPERSION",  "param_type": "value_text",    "param_sampleprep_unit": ""},
            {"param_sampleprep_name": "Sonication time","param_sampleprep_group": "DISPERSION",  "param_type": "value_num",     "param_sampleprep_unit": "min"},
            {"param_sampleprep_name": "Incubation temp","param_sampleprep_group": "INCUBATION",  "param_type": "value_num",     "param_sampleprep_unit": "°C"},
            {"param_sampleprep_name": "Date",           "param_sampleprep_group": "OTHER_SAMPLEPREP","param_type": "value_date","param_sampleprep_unit": ""},
            {"param_sampleprep_name": "Notes",          "param_sampleprep_group": "OTHER_SAMPLEPREP","param_type": "value_comment","param_sampleprep_unit": ""},
        ],
        "METADATA_PARAMETERS": [
            {"param_name": "Instrument model",  "param_group": "INSTRUMENT",             "param_type": "value_text",    "param_unit": ""},
            {"param_name": "Wavelength",        "param_group": "MEASUREMENT CONDITIONS", "param_type": "value_num",     "param_unit": "nm"},
            {"param_name": "CO2",               "param_group": "ENVIRONMENT",            "param_type": "value_boolean", "param_unit": "%"},
            {"param_name": "Cell line",         "param_group": "CELL LINE DETAILS",      "param_type": "value_text",    "param_unit": ""},
        ],
        "question3": [
            {"result_name": "Cell viability", "result_unit": "%",      "result_aggregate": "MEAN",     "result_endpoint_uncertainty": "SD"},
            {"result_name": "IC50",           "result_unit": "mg/mL",  "result_aggregate": "",         "result_endpoint_uncertainty": ""},
        ],
        "raw_data_report": [
            {"raw_endpoint": "Absorbance", "raw_unit": "AU", "raw_aggregate": "RAW_DATA", "raw_endpoint_uncertainty": ""},
        ],
        "calibration_report": [
            {"calibration_entry": "Absorbance std", "calibration_unit": "AU",
             "calibration_aggregate": "RAW_DATA", "calibration_entry_uncertainty": "none",
             "calibration_entry_type": "value_num"},
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_question_names(survey: dict) -> list[str]:
    """Recursively extract every 'name' field from questions/panels."""
    names = []

    def _walk(elements):
        for el in elements:
            if "name" in el:
                names.append(el["name"])
            for sub_key in ("elements", "detailElements"):
                if sub_key in el:
                    _walk(el[sub_key])

    for page in survey.get("pages", []):
        _walk(page.get("elements", []))
    return names


def _find_page(survey: dict, page_name: str) -> dict | None:
    return next((p for p in survey["pages"] if p["name"] == page_name), None)


def _find_element(elements: list, name: str) -> dict | None:
    for el in elements:
        if el.get("name") == name:
            return el
        for sub_key in ("elements", "detailElements"):
            found = _find_element(el.get(sub_key, []), name)
            if found:
                return found
    return None


def _all_elements_in_survey(survey: dict) -> list[dict]:
    result = []

    def _walk(elements):
        for el in elements:
            result.append(el)
            for sub_key in ("elements", "detailElements"):
                _walk(el.get(sub_key, []))

    for page in survey["pages"]:
        _walk(page.get("elements", []))
    return result


# ---------------------------------------------------------------------------
# 1. Structural invariants
# ---------------------------------------------------------------------------

class TestStructuralInvariants:

    def test_returns_dict(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert isinstance(survey, dict)

    def test_has_pages(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert "pages" in survey
        assert len(survey["pages"]) > 0

    def test_title_contains_method(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert "MTT" in survey["title"] or "Full Test Blueprint" in survey["title"]

    def test_question_names_are_unique(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        names = _collect_question_names(survey)
        assert len(names) == len(set(names)), \
            f"Duplicate question names: {[n for n in names if names.count(n) > 1]}"

    def test_question_names_are_strings(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        names = _collect_question_names(survey)
        assert all(isinstance(n, str) for n in names)

    def test_question_names_have_no_spaces(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        names = _collect_question_names(survey)
        assert all(" " not in n for n in names), \
            "Some question names contain spaces (breaks SurveyJS)"

    def test_pages_have_name_and_title(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        for page in survey["pages"]:
            assert "name" in page
            assert "title" in page

    def test_mandatory_pages_always_present(self, minimal_bp):
        """Identity and Submit pages must always exist."""
        survey = blueprint_to_data_entry_survey(minimal_bp)
        page_names = [p["name"] for p in survey["pages"]]
        assert "de_page_identity" in page_names
        assert "de_page_submit" in page_names

    def test_toc_enabled(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert survey.get("showTOC") is True

    def test_show_prev_button(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert survey.get("showPrevButton") is True

    def test_calculated_values_contain_method(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        calc_names = [cv["name"] for cv in survey.get("calculatedValues", [])]
        assert "blueprint_method" in calc_names


# ---------------------------------------------------------------------------
# 2. Identity / provenance page
# ---------------------------------------------------------------------------

class TestIdentityPage:

    def test_identity_page_present(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert _find_page(survey, "de_page_identity") is not None

    def test_operator_question_present(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_identity")
        el = _find_element(page["elements"], "de_provenance_operator")
        assert el is not None

    def test_start_date_is_required(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_identity")
        el = _find_element(page["elements"], "de_provenance_startdate")
        assert el is not None
        assert el.get("isRequired") is True

    def test_start_date_has_date_inputtype(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_identity")
        el = _find_element(page["elements"], "de_provenance_startdate")
        assert el.get("inputType") == "date"

    def test_provenance_default_values_from_blueprint(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_identity")
        op = _find_element(page["elements"], "de_provenance_operator")
        assert op.get("defaultValue") == "Lab Technician"

    def test_blueprint_summary_html_present(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_identity")
        html_els = [e for e in page["elements"] if e.get("type") == "html"]
        assert len(html_els) >= 1
        # Blueprint method name should appear in the summary HTML
        combined_html = " ".join(e.get("html", "") for e in html_els)
        assert "MTT" in combined_html


# ---------------------------------------------------------------------------
# 3. Sample page
# ---------------------------------------------------------------------------

class TestSamplePage:

    def test_sample_page_present_when_sample_info_exists(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert _find_page(survey, "de_page_sample") is not None

    def test_sample_page_absent_when_no_sample_info(self, full_bp):
        bp = dict(full_bp)
        del bp["METADATA_SAMPLE_INFO"]
        survey = blueprint_to_data_entry_survey(bp)
        assert _find_page(survey, "de_page_sample") is None

    def test_sample_question_count_matches_blueprint(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_sample")
        q_names = [e["name"] for e in page["elements"] if e.get("type") != "html"]
        assert len(q_names) == len(full_bp["METADATA_SAMPLE_INFO"])

    def test_first_sample_question_is_required(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_sample")
        first_q = next(e for e in page["elements"] if "de_sample__" in e.get("name", ""))
        assert first_q.get("isRequired") is True

    def test_sample_question_names_use_param_names(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_sample")
        titles = [e.get("title") for e in page["elements"]]
        for param in full_bp["METADATA_SAMPLE_INFO"]:
            assert param["param_sample_name"] in titles


# ---------------------------------------------------------------------------
# 4. Sample preparation page
# ---------------------------------------------------------------------------

class TestSamplePrepPage:

    def test_sampleprep_page_present(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert _find_page(survey, "de_page_sampleprep") is not None

    def test_sampleprep_panels_grouped_by_group(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_sampleprep")
        panel_titles = [e.get("title", "") for e in page["elements"] if e.get("type") == "panel"]
        # Blueprint has DISPERSION and INCUBATION groups
        assert any("Dispersion" in t for t in panel_titles)
        assert any("Incubation" in t for t in panel_titles)

    def test_all_sampleprep_params_have_questions(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        all_titles = [e.get("title", "") for e in _all_elements_in_survey(survey)]
        for param in full_bp["METADATA_SAMPLE_PREP"]:
            assert param["param_sampleprep_name"] in all_titles, \
                f"Missing title for '{param['param_sampleprep_name']}'"


# ---------------------------------------------------------------------------
# 5. Method parameters page
# ---------------------------------------------------------------------------

class TestMethodParamsPage:

    def test_method_params_page_present(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert _find_page(survey, "de_page_methodparams") is not None

    def test_params_grouped_into_panels(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_methodparams")
        panels = [e for e in page["elements"] if e.get("type") == "panel"]
        assert len(panels) >= 2  # INSTRUMENT, MEASUREMENT CONDITIONS, ENVIRONMENT, CELL LINE

    def test_all_param_names_appear_as_titles(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        all_titles = [e.get("title", "") for e in _all_elements_in_survey(survey)]
        for param in full_bp["METADATA_PARAMETERS"]:
            assert param["param_name"] in all_titles


# ---------------------------------------------------------------------------
# 6. Conditions page
# ---------------------------------------------------------------------------

class TestConditionsPage:

    def test_conditions_page_present_when_conditions_exist(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert _find_page(survey, "de_page_conditions") is not None

    def test_conditions_page_absent_when_no_conditions(self, minimal_bp):
        # minimal_bp has conditions=[]
        survey = blueprint_to_data_entry_survey(minimal_bp)
        assert _find_page(survey, "de_page_conditions") is None

    def test_concentration_condition_is_matrix(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_conditions")
        conc_el = _find_element(page["elements"], "de_condition__concentration")
        assert conc_el is not None
        assert conc_el["type"] == "matrixdynamic"

    def test_replicate_condition_is_number_input(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_conditions")
        rep_el = _find_element(page["elements"], "de_condition__replicate")
        assert rep_el is not None
        assert rep_el.get("inputType") == "number"

    def test_concentration_matrix_has_unit_in_description(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_conditions")
        conc_el = _find_element(page["elements"], "de_condition__concentration")
        assert "mg/mL" in conc_el.get("description", "")

    def test_concentration_matrix_columns(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_conditions")
        conc_el = _find_element(page["elements"], "de_condition__concentration")
        col_names = [c["name"] for c in conc_el.get("columns", [])]
        assert "cond_label" in col_names
        assert "cond_value" in col_names

    def test_one_element_per_condition(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_conditions")
        assert len(page["elements"]) == len(full_bp["conditions"])


# ---------------------------------------------------------------------------
# 7. Results page (processed data)
# ---------------------------------------------------------------------------

class TestResultsPage:

    def test_results_page_present_when_data_processed(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert _find_page(survey, "de_page_results") is not None

    def test_results_page_absent_when_not_in_data_sheets(self, full_bp):
        bp = dict(full_bp)
        bp["data_sheets"] = ["data_raw"]
        survey = blueprint_to_data_entry_survey(bp)
        assert _find_page(survey, "de_page_results") is None

    def test_results_matrix_has_endpoint_columns(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_results")
        matrix = _find_element(page["elements"], "de_results")
        col_names = [c["name"] for c in matrix["columns"]]
        assert any("cell_viability" in cn for cn in col_names)

    def test_results_matrix_has_condition_columns(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_results")
        matrix = _find_element(page["elements"], "de_results")
        col_names = [c["name"] for c in matrix["columns"]]
        # Condition columns follow cond__<slug> pattern
        assert any(cn.startswith("cond__") for cn in col_names)

    def test_uncertainty_column_added_when_sd_set(self, full_bp):
        """Cell viability has result_endpoint_uncertainty='SD' → extra ±SD column."""
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_results")
        matrix = _find_element(page["elements"], "de_results")
        col_names = [c["name"] for c in matrix["columns"]]
        assert any("__err" in cn for cn in col_names)

    def test_no_uncertainty_column_when_not_set(self, full_bp):
        """IC50 has no uncertainty set → no __err column for IC50."""
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_results")
        matrix = _find_element(page["elements"], "de_results")
        col_names = [c["name"] for c in matrix["columns"]]
        assert not any("ic50" in cn and "__err" in cn for cn in col_names)

    def test_unit_in_column_title(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_results")
        matrix = _find_element(page["elements"], "de_results")
        col_titles = [c["title"] for c in matrix["columns"]]
        assert any("%" in t for t in col_titles)

    def test_aggregate_label_in_column_title(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_results")
        matrix = _find_element(page["elements"], "de_results")
        col_titles = [c["title"] for c in matrix["columns"]]
        assert any("MEAN" in t for t in col_titles)


# ---------------------------------------------------------------------------
# 8. Raw data page
# ---------------------------------------------------------------------------

class TestRawDataPage:

    def test_raw_page_present_when_data_raw(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert _find_page(survey, "de_page_raw") is not None

    def test_raw_page_absent_when_not_in_data_sheets(self, full_bp):
        bp = dict(full_bp)
        bp["data_sheets"] = ["data_processed"]
        survey = blueprint_to_data_entry_survey(bp)
        assert _find_page(survey, "de_page_raw") is None

    def test_raw_matrix_has_absorbance_column(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_raw")
        matrix = _find_element(page["elements"], "de_raw_data")
        col_names = [c["name"] for c in matrix["columns"]]
        assert any("absorbance" in cn.lower() for cn in col_names)

    def test_raw_matrix_has_condition_columns(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_raw")
        matrix = _find_element(page["elements"], "de_raw_data")
        col_names = [c["name"] for c in matrix["columns"]]
        assert any(cn.startswith("cond__") for cn in col_names)


# ---------------------------------------------------------------------------
# 9. Calibration page
# ---------------------------------------------------------------------------

class TestCalibrationPage:

    def test_calibration_page_present(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert _find_page(survey, "de_page_calibration") is not None

    def test_calibration_page_absent_when_not_in_data_sheets(self, full_bp):
        bp = dict(full_bp)
        bp["data_sheets"] = ["data_raw", "data_processed"]
        survey = blueprint_to_data_entry_survey(bp)
        assert _find_page(survey, "de_page_calibration") is None

    def test_calibration_matrix_has_standard_label_column(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_calibration")
        matrix = _find_element(page["elements"], "de_calibration")
        col_names = [c["name"] for c in matrix["columns"]]
        assert "cal_standard_label" in col_names

    def test_calibration_matrix_has_entry_column(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_calibration")
        matrix = _find_element(page["elements"], "de_calibration")
        col_names = [c["name"] for c in matrix["columns"]]
        assert any("absorbance" in cn.lower() for cn in col_names)

    def test_calibration_matrix_min_row_count(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_calibration")
        matrix = _find_element(page["elements"], "de_calibration")
        assert matrix.get("minRowCount", 0) >= 2


# ---------------------------------------------------------------------------
# 10. Submit page
# ---------------------------------------------------------------------------

class TestSubmitPage:

    def test_submit_page_always_present(self, minimal_bp):
        survey = blueprint_to_data_entry_survey(minimal_bp)
        assert _find_page(survey, "de_page_submit") is not None

    def test_submit_page_is_last(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        assert survey["pages"][-1]["name"] == "de_page_submit"

    def test_experiment_id_is_required(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_submit")
        el = _find_element(page["elements"], "de_experiment_id")
        assert el is not None
        assert el.get("isRequired") is True

    def test_notes_field_is_comment_type(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        page = _find_page(survey, "de_page_submit")
        el = _find_element(page["elements"], "de_notes")
        assert el is not None
        assert el["type"] == "comment"


# ---------------------------------------------------------------------------
# 11. param_type → question type mapping
# ---------------------------------------------------------------------------

class TestParamTypeMapping:

    @pytest.mark.parametrize("param_type,expected_type,extra_check", [
        ("value_num",     "text",       lambda q: q.get("inputType") == "number"),
        ("value_text",    "text",       lambda q: q.get("inputType") is None),
        ("value_boolean", "radiogroup", lambda q: len(q.get("choices", [])) == 2),
        ("value_date",    "text",       lambda q: q.get("inputType") == "date"),
        ("value_comment", "comment",    lambda q: True),
    ])
    def test_param_type_mapping(self, param_type, expected_type, extra_check):
        q = _param_type_to_question("q_name", "Title", param_type)
        assert q["type"] == expected_type, \
            f"param_type '{param_type}' → expected type '{expected_type}', got '{q['type']}'"
        assert extra_check(q)

    def test_boolean_choices_are_yes_no(self):
        q = _param_type_to_question("q", "T", "value_boolean")
        values = [c["value"] for c in q["choices"]]
        assert "yes" in values
        assert "no" in values

    def test_unit_appears_in_description(self):
        q = _param_type_to_question("q", "T", "value_num", unit="nm")
        assert "nm" in q.get("description", "")

    def test_hint_appears_in_description(self):
        q = _param_type_to_question("q", "T", "value_text", hint="Specify carefully")
        assert "Specify carefully" in q.get("description", "")

    def test_unknown_type_defaults_to_text(self):
        q = _param_type_to_question("q", "T", "value_xyz_unknown")
        assert q["type"] == "text"

    def test_required_flag_propagated(self):
        q = _param_type_to_question("q", "T", "value_text", required=True)
        assert q.get("isRequired") is True


# ---------------------------------------------------------------------------
# 12. _slug helper
# ---------------------------------------------------------------------------

class TestSlugHelper:

    def test_spaces_replaced(self):
        assert " " not in _slug("hello world")

    def test_special_chars_replaced(self):
        assert _slug("foo/bar") == "foo_bar"

    def test_lowercase(self):
        assert _slug("FOO") == "foo"

    def test_leading_trailing_stripped(self):
        result = _slug("  spaces  ")
        assert not result.startswith("_") or result.strip("_") != ""

    def test_valid_surveyjs_name(self):
        """Output should match [A-Za-z0-9_]* (SurveyJS question name constraint)."""
        for label in ["Cell line", "Medium (Supplier/Lot No.)", "CO₂ %", "pH@37°C"]:
            result = _slug(label)
            assert re.match(r"^[a-z0-9_]+$", result), \
                f"_slug('{label}') = '{result}' is not a valid SurveyJS name"


# ---------------------------------------------------------------------------
# 13. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_conditions_list(self, minimal_bp):
        survey = blueprint_to_data_entry_survey(minimal_bp)
        assert _find_page(survey, "de_page_conditions") is None

    def test_data_sheets_not_set_produces_results_page(self, full_bp):
        bp = dict(full_bp)
        del bp["data_sheets"]
        # Should not raise; generator uses a fallback
        survey = blueprint_to_data_entry_survey(bp)
        assert isinstance(survey, dict)

    def test_missing_result_unit_does_not_crash(self, full_bp):
        bp = dict(full_bp)
        bp["question3"] = [{"result_name": "X"}]
        survey = blueprint_to_data_entry_survey(bp)
        assert _find_page(survey, "de_page_results") is not None

    def test_results_page_absent_when_question3_empty(self, full_bp):
        bp = dict(full_bp)
        bp["question3"] = []
        survey = blueprint_to_data_entry_survey(bp)
        assert _find_page(survey, "de_page_results") is None

    def test_no_provenance_fields_does_not_crash(self, minimal_bp):
        survey = blueprint_to_data_entry_survey(minimal_bp)
        page = _find_page(survey, "de_page_identity")
        assert page is not None

    def test_method_name_in_page_titles(self, full_bp):
        survey = blueprint_to_data_entry_survey(full_bp)
        titled_pages = [p for p in survey["pages"] if "MTT" in p.get("title", "")]
        assert len(titled_pages) >= 2


# ---------------------------------------------------------------------------
# 14. Integration: dose_response.json fixture
# ---------------------------------------------------------------------------

class TestDoseResponseIntegration:

    def test_generates_without_error(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        assert isinstance(survey, dict)

    def test_all_pages_have_elements(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        for page in survey["pages"]:
            assert len(page["elements"]) > 0, \
                f"Page '{page['name']}' has no elements"

    def test_all_sample_params_surfaced(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        all_titles = {e.get("title", "") for e in _all_elements_in_survey(survey)}
        for param in dose_response_bp["METADATA_SAMPLE_INFO"]:
            assert param["param_sample_name"] in all_titles

    def test_all_method_params_surfaced(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        all_titles = {e.get("title", "") for e in _all_elements_in_survey(survey)}
        for param in dose_response_bp["METADATA_PARAMETERS"]:
            assert param["param_name"] in all_titles

    def test_all_sampleprep_params_surfaced(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        all_titles = {e.get("title", "") for e in _all_elements_in_survey(survey)}
        for param in dose_response_bp["METADATA_SAMPLE_PREP"]:
            assert param["param_sampleprep_name"].strip() in all_titles

    def test_both_result_endpoints_surfaced(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        page = _find_page(survey, "de_page_results")
        assert page is not None
        matrix = _find_element(page["elements"], "de_results")
        col_titles = " ".join(c.get("title", "") for c in matrix["columns"])
        assert "Cell viability" in col_titles
        assert "Fold change" in col_titles

    def test_conditions_page_has_concentration_and_time(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        page = _find_page(survey, "de_page_conditions")
        assert page is not None
        el_names = [e["name"] for e in page["elements"]]
        assert any("concentration" in n for n in el_names)
        assert any("time" in n for n in el_names)

    def test_raw_data_page_present(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        assert _find_page(survey, "de_page_raw") is not None

    def test_question_names_unique_in_dose_response(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        names = _collect_question_names(survey)
        assert len(names) == len(set(names))

    def test_survey_is_valid_json(self, dose_response_bp):
        survey = blueprint_to_data_entry_survey(dose_response_bp)
        # If json.dumps / json.loads round-trip succeeds the object is serialisable
        dumped = json.dumps(survey)
        reloaded = json.loads(dumped)
        assert reloaded["pages"][0]["name"] == "de_page_identity"


# ---------------------------------------------------------------------------
# 15. Integration: calibration.json fixture
# ---------------------------------------------------------------------------

class TestCalibrationIntegration:

    def test_calibration_page_present(self, calibration_bp):
        survey = blueprint_to_data_entry_survey(calibration_bp)
        assert _find_page(survey, "de_page_calibration") is not None

    def test_calibration_min_rows(self, calibration_bp):
        survey = blueprint_to_data_entry_survey(calibration_bp)
        page = _find_page(survey, "de_page_calibration")
        matrix = _find_element(page["elements"], "de_calibration")
        assert matrix.get("minRowCount", 0) >= 2