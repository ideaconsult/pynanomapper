"""Regression tests for TemplateDesignerParser edge cases found while
converting the MOMENTUM Template Designer corpus.

Each test builds its inputs synthetically (no Excel file, no external
fixture) and calls `TemplateDesignerParser` methods directly on a bare
instance -- `TemplateDesignerParser.__init__` does file I/O this suite has no
need for, since every bug here lives entirely in post-parse logic that only
touches `self.template_json` / `self.test_conditions` / `self.raw` /
`self.results`.
"""

import numpy as np
import pandas as pd
import pytest

from pynanomapper.datamodel.templates.template_parser import (
    TemplateDesignerParser,
)


def _bare_parser(**attrs) -> TemplateDesignerParser:
    """A TemplateDesignerParser with only the given attributes set,
    bypassing __init__ (which reads an .xlsx file)."""
    parser = object.__new__(TemplateDesignerParser)
    for name, value in attrs.items():
        setattr(parser, name, value)
    return parser


def test_get_parameters_non_numeric_value_with_unit():
    """A METADATA_PARAMETERS entry that declares a unit but whose
    Test_conditions cell holds free text (not "<number> <unit>") must be
    stored as a plain string parameter, not crash trying to build an
    `mx.Value`.

    Real case: Py-GC-MS workbooks record "m/z 100" as an instrument setting.
    `parse_value_unit` cannot find a leading number there and returns the
    string unchanged, which used to be passed straight into
    `mx.Value(loValue=...)` -- loValue is numeric-only, so every such
    workbook failed with a pydantic ValidationError.
    """
    test_conditions = pd.DataFrame(
        {
            "A": ["Pyrolysis temperature", "no match"],
            "B": ["m/z 100", "irrelevant"],
        }
    )
    parser = _bare_parser(
        template_json={
            "METADATA_PARAMETERS": [
                {
                    "param_name": "Pyrolysis temperature",
                    "param_group": "instrument",
                    "param_unit": "m/z",
                }
            ],
            "METADATA_SAMPLE_PREP": [],
        },
        test_conditions=test_conditions,
    )

    params = parser.get_parameters()

    assert params["instrument/Pyrolysis temperature"] == "m/z 100"


def test_get_parameters_numeric_value_with_unit_still_builds_value():
    """The numeric case (the common one) must keep working unchanged."""
    test_conditions = pd.DataFrame(
        {"A": ["Concentration"], "B": ["12.5 mg/mL"]}
    )
    parser = _bare_parser(
        template_json={
            "METADATA_PARAMETERS": [
                {
                    "param_name": "Concentration",
                    "param_group": "dose",
                    "param_unit": "mg/mL",
                }
            ],
            "METADATA_SAMPLE_PREP": [],
        },
        test_conditions=test_conditions,
    )

    params = parser.get_parameters()

    value = params["dose/Concentration"]
    assert value.loValue == 12.5
    assert value.unit == "mg/mL"


def test_parse_effects_endpoint_with_nan_unit_header():
    """A 1D numeric endpoint whose MultiIndex second header level is NaN
    (a float, not the usual "Unnamed: N" string) must not crash reading its
    unit.

    Real case: several MOMENTUM cytokine-release workbooks have a bare
    endpoint column with an empty header cell below it, which pandas reads
    as float NaN rather than "Unnamed: N" -- `nan.startswith(...)` raised
    AttributeError. Endpoints with an axis condition are covered by
    `df_to_nd_effectarray_multicol`'s own (already-correct) `get_unit`; this
    exercises the simple 1D branch in `_parse_effects_from_dataframe`.
    """
    df = pd.DataFrame(
        {("CXCL2 concentration", float("nan")): [1.0, 2.0, 3.0]}
    )
    endpoints_df = pd.DataFrame(
        [{"name": "CXCL2 concentration", "unit": None, "conditions": None, "type": "value_num"}]
    )
    conditions_df = pd.DataFrame(columns=["name"])
    parser = _bare_parser(template_json={})

    effects = parser._parse_effects_from_dataframe(
        df=df,
        endpoints_df=endpoints_df,
        conditions_df=conditions_df,
        endpoint_type="AGGREGATED",
    )

    assert len(effects) == 1
    assert effects[0].endpoint == "CXCL2 concentration"
    assert effects[0].signal.unit is None
    assert list(effects[0].signal.values) == [1.0, 2.0, 3.0]


def test_df_to_nd_effectarray_multicol_skips_row_missing_axis_value():
    """A row with no value on one of the endpoint's own axes must be
    skipped, not crash the whole EffectArray.

    Real case: MOMENTUM ROS-production dose-response tables include vehicle
    / H2O2 control rows that legitimately have no `concentration` (there is
    no dose for a control). `pd.unique()` keeps NaN as a distinct axis
    value, but dict lookup on NaN is not reliably reflexive (nan != nan), so
    `idx_map[ax][row[axis_cols[ax]]]` raised `KeyError` on those rows and the
    surrounding try/except in `_parse_effects_from_dataframe` then dropped
    the ENTIRE endpoint -- silently turning a real dose-response signal into
    zero effects, for every workbook containing even one control row.
    """
    df = pd.DataFrame(
        {
            ("Material", "u0"): ["H2O2", "vehicle", "sample", "sample"],
            ("concentration", "ug/ml"): [np.nan, np.nan, 1.0, 10.0],
            ("Fold change", "u1"): [2.48, 1.0, 0.69, 1.20],
        }
    )
    endpoints_df = pd.DataFrame(
        [
            {
                "name": "Fold change",
                "unit": None,
                "conditions": ["concentration"],
                "type": "value_num",
            }
        ]
    )
    conditions_df = pd.DataFrame(
        [{"name": "concentration", "unit": "ug/ml"}]
    )
    parser = _bare_parser(template_json={})

    effects = parser._parse_effects_from_dataframe(
        df=df,
        endpoints_df=endpoints_df,
        conditions_df=conditions_df,
        endpoint_type="AGGREGATED",
    )

    assert len(effects) == 1
    signal = effects[0].signal
    values = np.asarray(signal.values, dtype=float)
    # The two NaN-concentration control rows are skipped (no cell for them);
    # the two dosed rows survive and land at their own concentration index.
    assert np.count_nonzero(~np.isnan(values)) == 2


def test_df_to_nd_effectarray_multicol_falls_back_to_blueprint_unit():
    """An axis whose data-table column carries no unit in its own header
    must still get the unit the blueprint declares for that condition.

    Real case: several MOMENTUM workbooks (uptake/RUG_PAM_phagocytosis,
    ROS-production/RUG_PAM-ROS) declare e.g. "Concentration: ug/mL" in the
    blueprint's `conditions`, but the actual Results_TABLE column's own unit
    cell is blank. `_parse_effects_from_dataframe` already resolves the
    correct unit from `conditions_df` and passes it into `axes_dict` --
    but `df_to_nd_effectarray_multicol` immediately rebuilt `axes_dict` from
    scratch using only the DataFrame header's own (blank) unit, discarding
    the caller's value and silently writing every such axis with no unit.
    """
    parser = _bare_parser(template_json={})
    df = pd.DataFrame(
        {
            ("Material", "u0"): ["A", "A", "A"],
            ("Concentration", float("nan")): [0, 1, 10],
            ("Positive cells", "%"): [5.0, 12.0, 40.0],
        }
    )
    # What _parse_effects_from_dataframe would have already resolved from
    # conditions_df before calling df_to_nd_effectarray_multicol.
    import pyambit.datamodel as mx

    axes_dict_in = {
        "Concentration": mx.ValueArray(values=np.array([0, 1, 10]), unit="ug/mL")
    }

    earray = parser.df_to_nd_effectarray_multicol(
        df=df,
        axes_dict=axes_dict_in,
        main_signal="Positive cells",
        endpoint="Positive cells",
        endpointtype="AGGREGATED",
    )

    assert earray.axes["Concentration"].unit == "ug/mL"


def test_parse_effects_value_num_column_with_one_marker_cell():
    """A `value_num` endpoint whose column has one non-numeric "not
    measured" marker cell (pandas then infers object dtype for the WHOLE
    column) must still parse as a numeric EffectArray, not be misrouted
    into text EffectRecords for every real number it holds.

    Real case: MOMENTUM Py-GC-MS workbooks (e.g. Bronchial wash_RUG.xlsx)
    declare polymer-quantity columns like "PET"/"PMMA" as `value_num` (unit
    "ng"), but one sample among 47 has a literal "-" instead of a value.
    `pd.api.types.is_numeric_dtype()` on that column returns False for the
    WHOLE column because of that one cell, and the old code trusted dtype
    inference over the blueprint's own declared type -- turning 46 real
    concentration numbers into a pile of stringified text EffectRecords
    instead of one numeric EffectArray.
    """
    df = pd.DataFrame({("PET", "ng"): [11.5, 15.6, "-", 21.8, 0]})
    endpoints_df = pd.DataFrame(
        [{"name": "PET", "unit": "ng", "conditions": None, "type": "value_num"}]
    )
    conditions_df = pd.DataFrame(columns=["name"])
    parser = _bare_parser(template_json={})

    effects = parser._parse_effects_from_dataframe(
        df=df,
        endpoints_df=endpoints_df,
        conditions_df=conditions_df,
        endpoint_type="AGGREGATED",
    )

    assert len(effects) == 1
    effect = effects[0]
    assert hasattr(effect, "signal"), "must be an EffectArray, not EffectRecords"
    values = np.asarray(effect.signal.values, dtype=float)
    assert sorted(values.tolist()) == [0.0, 11.5, 15.6, 21.8]
    assert effect.signal.unit == "ng"
