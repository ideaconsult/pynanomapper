"""Regression tests for TemplateDesignerParser edge cases found while
converting real Template Designer workbooks.

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
    """A numeric endpoint whose MultiIndex second header level is NaN
    (a float, not the usual "Unnamed: N" string) must not crash reading its
    unit.

    Seen where a workbook has a bare endpoint column with an empty header
    cell below it, which pandas reads as float NaN rather than "Unnamed: N"
    -- `nan.startswith(...)` raised AttributeError.
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

    # One flat EffectRecord per data row -- assembling them into an
    # EffectArray is convert_effectrecords2array()'s job, not this method's.
    assert len(effects) == 3
    assert {e.endpoint for e in effects} == {"CXCL2 concentration"}
    assert all(e.result.unit is None for e in effects)
    assert [e.result.loValue for e in effects] == [1.0, 2.0, 3.0]


def test_row_missing_a_condition_value_omits_only_that_condition():
    """A row with no value for one of its declared conditions still yields a
    record -- just without that condition.

    Seen in dose-response tables that include vehicle / positive-control
    rows which legitimately have no `concentration` (a control has no dose).
    Those rows must not be dropped, and must not invent a concentration
    either; the conversion then groups them on the conditions they do have.
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

    assert len(effects) == 4
    assert [e.result.loValue for e in effects] == [2.48, 1.0, 0.69, 1.20]
    # The two control rows carry no concentration at all ...
    assert effects[0].conditions == {}
    assert effects[1].conditions == {}
    # ... while the dosed rows carry it as a Value with its declared unit.
    assert effects[2].conditions["concentration"].loValue == 1.0
    assert effects[2].conditions["concentration"].unit == "ug/ml"


def test_df_to_nd_effectarray_multicol_falls_back_to_blueprint_unit():
    """An axis whose data-table column carries no unit in its own header
    must still get the unit the blueprint declares for that condition.

    Seen where a workbook declares e.g. "Concentration: ug/mL" in the
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
    column) must still yield numeric records for every real number it
    holds, with only the marker cell dropped.

    Seen where a workbook declares quantity columns as `value_num` (unit
    "ng"), but one sample among many has a literal "-" instead of a value.
    Trusting pandas' dtype inference over the template's declared type turned
    46 real concentrations into stringified text.
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

    # The "-" marker is dropped; every real number survives as a numeric
    # record carrying the template's declared unit.
    assert len(effects) == 4
    assert sorted(e.result.loValue for e in effects) == [0.0, 11.5, 15.6, 21.8]
    assert all(e.result.unit == "ng" for e in effects)
    assert all(e.result.textValue is None for e in effects)


def test_to_substances_routes_each_record_to_its_own_material():
    """Each substance must get only the records about IT, not the whole
    file's data.

    Real case: a dose-response table commonly reports several materials at
    once (a dose series, its vehicle control, a shared calibration curve),
    all in one Raw_data_TABLE/Results_TABLE. to_substances() used to clone
    the SAME effects list onto every selected material -- every substance's
    study ended up holding every OTHER substance's measurements too.
    """
    import pyambit.datamodel as mx

    effects = [
        mx.EffectRecord(
            endpoint="Viability",
            result=mx.EffectResult(loValue=v, unit="%"),
            conditions={},
            sampleID=material,
        )
        for material, v in [("CuO", 80.0), ("CuO", 82.0), ("TiO2", 90.0)]
    ]
    pa = mx.ProtocolApplication(
        protocol=mx.Protocol(
            topcategory="TOX",
            category=mx.EndpointCategory(code="NPO_1339_SECTION"),
            endpoint="assay",
            guideline=["sop"],
        ),
        effects=effects,
    )

    parser = _bare_parser(
        materials=pd.DataFrame(
            {"ERM identifier": ["CuO", "TiO2 "], "type": ["metal_oxide", "metal_oxide"]}
        ),
        test_conditions=pd.DataFrame(
            {"A": ["Select item from Project Materials list"], "B": ["CuO"], "C": ["TiO2"]}
        ),
        template_json={"provenance_provider": "TestOwner"},
    )
    parser.get_project_name = lambda: "TestProject"

    substances = parser.to_substances(pa=pa).substance

    def signal_values(substance):
        effect = substance.study[0].effects[0]
        return set(np.asarray(effect.signal.values, dtype=float).tolist())

    # `name` is the material ID (see to_substances: i5uuid/name/publicname
    # are all set from the same stripped material_id).
    by_material = {s.name: s for s in substances}
    # No conditions on either endpoint, so each substance's own records
    # assemble into one EffectArray (convert_effectrecords2array) -- the
    # values that matter here are which ones ended up in it, not how many
    # EffectRecord/EffectArray objects that took.
    assert len(by_material["CuO"].study[0].effects) == 1
    assert len(by_material["TiO2"].study[0].effects) == 1
    assert signal_values(by_material["CuO"]) == {80.0, 82.0}
    assert signal_values(by_material["TiO2"]) == {90.0}


def test_to_substances_keeps_every_record_with_no_material_column():
    """A record with no sampleID at all (the table has no Material column)
    must stay available to every selected substance -- e.g. Py-GC-MS
    polymer-standard quantities that legitimately apply to every run, not
    to one material each.
    """
    import pyambit.datamodel as mx

    effects = [
        mx.EffectRecord(
            endpoint="PET",
            result=mx.EffectResult(loValue=11.5, unit="ng"),
            conditions={},
        )
    ]
    pa = mx.ProtocolApplication(
        protocol=mx.Protocol(
            topcategory="TOX",
            category=mx.EndpointCategory(code="NPO_1339_SECTION"),
            endpoint="assay",
            guideline=["sop"],
        ),
        effects=effects,
    )
    parser = _bare_parser(
        materials=pd.DataFrame({"ERM identifier": ["PET_std"], "type": ["polymer"]}),
        test_conditions=pd.DataFrame(
            {"A": ["Select item from Project Materials list"], "B": ["PET_std"]}
        ),
        template_json={},
    )
    parser.get_project_name = lambda: "TestProject"

    substances = parser.to_substances(pa=pa).substance

    assert len(substances) == 1
    assert len(substances[0].study[0].effects) == 1


def test_pchem_layout_end_to_end():
    """The "pchem" layout (FTIR/SLS/XRF): Provider_informations instead of
    Test_conditions, one Results_TABLE (4-level header: top-label / name /
    aggregate-type / unit) holding both raw and processed data instead of a
    Raw_data_TABLE/Results_TABLE split, and no selector cell for materials
    used -- SAMPLES/Results_TABLE are already keyed by Material ID.

    Before pchem support, __init__ unconditionally read Test_conditions,
    failing every such workbook with
    "Worksheet named 'Test_conditions' not found" -- these templates were
    entirely unparseable.
    """
    results = pd.DataFrame(
        {
            ("Material ID", "u0", "u0", "u0"): ["ERM1", "ERM1", "ERM2", "ERM2"],
            ("Position_ID", "u1", "u1", "u1"): [1, 1, 2, 2],
            ("Raw data", "Wavenumber (cm-1)", "RAW_DATA", "cm-1"): [
                670.0, 680.0, 670.0, 680.0,
            ],
            ("Raw data", "Transmission", "RAW_DATA", "%"): [85.9, 83.4, 90.1, 88.2],
        }
    )
    provider_info = pd.DataFrame(
        {
            0: [None, "General information", None, None, None, "Project", "Workpackage", "Partner"],
            1: [None, None, None, None, None, "MOMENTUM", "WP1", "TNO"],
            2: [None, "FTIR spectroscopy", None, None, None, None, None, None],
            3: [None, None, None, None, None, None, "Study", None],
            4: [None, None, None, None, None, None, "FTIR", None],
        }
    )
    measuring_conditions = pd.DataFrame(
        {
            ("Position_ID", "u0", "u0"): [1, 2],
            ("METADATA_PARAMETERS", "INSTRUMENT", "Instrument"): ["Nicolet iN10", "Nicolet iN10"],
        }
    )
    samples = pd.DataFrame(
        {
            ("Material ID", "u0"): ["ERM1", "ERM2"],
            ("Sample preparation", "DISPERSION"): ["1-propanol", "1-propanol"],
        }
    )

    parser = _bare_parser(
        template_json={
            "template_layout": "pchem",
            "PROTOCOL_TOP_CATEGORY": "P-CHEM",
            "PROTOCOL_CATEGORY_CODE": "ANALYTICAL_METHODS_SECTION",
            "METHOD": "FTIR",
            "EXPERIMENT": "FTIR spectroscopy",
            "raw_data_report": [
                {
                    "raw_endpoint": "Wavenumber (cm-1)",
                    "raw_aggregate": "RAW_DATA",
                    "raw_unit": "cm-1",
                    "raw_type": "value_num",
                },
                {
                    "raw_endpoint": "Transmission",
                    "raw_aggregate": "RAW_DATA",
                    "raw_unit": "%",
                    "raw_type": "value_num",
                },
            ],
            "question3": [],
            "conditions": [],
        },
        provider_info=provider_info,
        results=results,
        measuring_conditions=measuring_conditions,
        samples=samples,
        materials=pd.DataFrame(
            {"ERM identifier": ["ERM1", "ERM2"], "type": ["metal_oxide", "metal_oxide"]}
        ),
        test_conditions=None,
        raw=None,
        calibration=None,
    )

    assert parser.get_project_name() == "MOMENTUM"
    assert parser.get_work_package() == "WP1"
    assert parser.get_partner() == "TNO"

    pa = parser.to_protocol_application(convert_to_arrays=False)
    assert len(pa.effects) == 8  # 4 rows x 2 endpoints
    assert pa.citation.owner == "TNO"
    assert pa.citation.title == "WP1"

    substances = parser.to_substances(pa=pa).substance
    by_material = {s.name: s for s in substances}
    assert set(by_material) == {"ERM1", "ERM2"}
    erm1_wavenumber = next(
        e for e in by_material["ERM1"].study[0].effects
        if e.endpoint == "Wavenumber (cm-1)"
    )
    assert sorted(np.asarray(erm1_wavenumber.signal.values, dtype=float).tolist()) == [
        670.0, 680.0,
    ]
    assert erm1_wavenumber.signal.unit == "cm-1"


def test_pchem_text_conditions_promotes_axis_endpoint():
    """A pchem endpoint promoted via `text_conditions` becomes an axis of
    the other endpoints in its row, instead of its own independent scalar
    series.

    Real case: FTIR/SLS declare their x-axis ("Wavenumber (cm-1)",
    "Wavelength") as a plain RAW_DATA endpoint, with no raw_conditions on
    the real signal (Transmission, Number, Volume) pointing at it -- every
    spectrum wrote as several unlinked scalar series instead of one signal
    plotted against its axis.
    """
    results = pd.DataFrame(
        {
            ("Material ID", "u0", "u0", "u0"): ["ERM1", "ERM1", "ERM1"],
            ("Position_ID", "u1", "u1", "u1"): [1, 1, 1],
            ("Raw data", "Wavenumber (cm-1)", "RAW_DATA", "cm-1"): [
                670.0, 680.0, 690.0,
            ],
            ("Raw data", "Transmission", "RAW_DATA", "%"): [85.9, 83.4, 82.2],
        }
    )
    parser = _bare_parser(
        template_json={
            "template_layout": "pchem",
            "PROTOCOL_TOP_CATEGORY": "P-CHEM",
            "PROTOCOL_CATEGORY_CODE": "ANALYTICAL_METHODS_SECTION",
            "METHOD": "FTIR",
            "EXPERIMENT": "FTIR spectroscopy",
            "raw_data_report": [
                {
                    "raw_endpoint": "Wavenumber (cm-1)",
                    "raw_aggregate": "RAW_DATA",
                    "raw_unit": "cm-1",
                    "raw_type": "value_num",
                },
                {
                    "raw_endpoint": "Transmission",
                    "raw_aggregate": "RAW_DATA",
                    "raw_unit": "%",
                    "raw_type": "value_num",
                },
            ],
            "question3": [],
            "conditions": [],
        },
        provider_info=pd.DataFrame(),
        results=results,
        measuring_conditions=pd.DataFrame(),
        samples=pd.DataFrame(
            {
                ("Material ID", "u0"): ["ERM1"],
                ("Sample preparation", "DISPERSION"): ["1-propanol"],
            }
        ),
        materials=pd.DataFrame({"ERM identifier": ["ERM1"], "type": ["polymer"]}),
        test_conditions=None,
        raw=None,
        calibration=None,
    )

    pa = parser.to_protocol_application(text_conditions=["Wavenumber (cm-1)"])

    assert len(pa.effects) == 1
    effect = pa.effects[0]
    assert effect.endpoint == "Transmission"
    assert sorted(np.asarray(effect.signal.values, dtype=float).tolist()) == [
        82.2, 83.4, 85.9,
    ]
    axis = effect.axes["Wavenumber (cm-1)"]
    assert axis.unit == "cm-1"
    assert sorted(np.asarray(axis.values, dtype=float).tolist()) == [670.0, 680.0, 690.0]


def test_aux_signals_merges_two_arrays_sharing_axes():
    """A primary/aux pair with the same conditions and axes folds into one
    EffectArray (signal + auxiliary), not two independent NXdata entries.

    Real case: SLS reports "Number" and "Volume" as two independent
    endpoints, both a distribution over the same "Wavelength" bins -- two
    views of the same measurement, not two unrelated signals.
    """
    results = pd.DataFrame(
        {
            ("Material ID", "u0", "u0", "u0"): ["ERM1"] * 3,
            ("Position_ID", "u1", "u1", "u1"): [1, 1, 1],
            ("Raw data", "Wavelength", "RAW_DATA", "um"): [0.01, 0.02, 0.03],
            ("Raw data", "Number", "RAW_DATA", "%"): [1.0, 2.0, 3.0],
            ("Raw data", "Volume", "RAW_DATA", "%"): [10.0, 20.0, 30.0],
        }
    )
    parser = _bare_parser(
        template_json={
            "template_layout": "pchem",
            "PROTOCOL_TOP_CATEGORY": "P-CHEM",
            "PROTOCOL_CATEGORY_CODE": "PC_GRANULOMETRY_SECTION",
            "METHOD": "SLS",
            "EXPERIMENT": "SLS",
            "raw_data_report": [
                {"raw_endpoint": "Wavelength", "raw_aggregate": "RAW_DATA", "raw_unit": "um", "raw_type": "value_num"},
                {"raw_endpoint": "Number", "raw_aggregate": "RAW_DATA", "raw_unit": "%", "raw_type": "value_num"},
                {"raw_endpoint": "Volume", "raw_aggregate": "RAW_DATA", "raw_unit": "%", "raw_type": "value_num"},
            ],
            "question3": [],
            "conditions": [],
        },
        provider_info=pd.DataFrame(),
        results=results,
        measuring_conditions=pd.DataFrame(),
        samples=pd.DataFrame(
            {("Material ID", "u0"): ["ERM1"], ("Sample preparation", "u1"): ["dispersed"]}
        ),
        materials=pd.DataFrame({"ERM identifier": ["ERM1"], "type": ["polymer"]}),
        test_conditions=None,
        raw=None,
        calibration=None,
    )
    parser.get_project_name = lambda: "TestProject"

    pa = parser.to_protocol_application(
        convert_to_arrays=False, text_conditions=["Wavelength"]
    )
    substances = parser.to_substances(
        pa=pa, aux_signals={"Number": ["Volume"]}
    ).substance

    effects = substances[0].study[0].effects
    assert [e.endpoint for e in effects] == ["Number"]
    number = effects[0]
    assert sorted(np.asarray(number.signal.values, dtype=float).tolist()) == [
        1.0, 2.0, 3.0,
    ]
    volume = number.signal.auxiliary["Volume"]
    assert sorted(np.asarray(volume.values, dtype=float).tolist()) == [10.0, 20.0, 30.0]
    assert volume.unit == "%"


def test_share_conditions_lets_unconditioned_endpoint_merge_as_aux():
    """An endpoint with no declared conditions of its own borrows a
    primary's conditions (share_conditions) so it grid-builds over the same
    axes, then merges into the primary as an auxiliary signal (aux_signals)
    -- the two features composed, matching wp5's real case: "Fraction"/
    "Leachate"/... are outcomes of the same "Concentration bacteria" row,
    not conditions of it, but declare no conditions of their own at all, so
    aux_signals alone (structural conditions+axes matching) has nothing to
    match them by.

    Also exercises whitespace tolerance: real endpoint names carry trailing
    spaces ("Concentration bacteria "); the config here deliberately omits
    them, matching how a human would write pipeline.yaml.
    """
    import pyambit.datamodel as mx

    df = pd.DataFrame(
        {
            ("Material", "u0"): ["A", "A", "A", "A"],
            ("Concentration", "CFU/mL (start)"): [100, 100, 200, 200],
            ("Replicate", "u1"): [1, 2, 1, 2],
            ("Concentration bacteria ", "CFU/mL"): [10.0, 12.0, 30.0, 28.0],
            ("Fraction ", "Strainer/Flow-through/Total"): [
                "Total", "Total", "Strainer", "Strainer",
            ],
        }
    )
    endpoints_df = pd.DataFrame(
        [
            {
                "name": "Concentration bacteria ",
                "unit": "CFU/mL",
                "conditions": ["Concentration", "Replicate"],
                "type": "value_num",
            },
            {
                "name": "Fraction ",
                "unit": "Strainer/Flow-through/Total",
                "conditions": None,
                "type": "value_text",
            },
        ]
    )
    conditions_df = pd.DataFrame(
        [
            {"name": "Concentration", "unit": "CFU/mL (start)"},
            {"name": "Replicate", "unit": None},
        ]
    )
    parser = _bare_parser(template_json={})

    effects = parser._parse_effects_from_dataframe(
        df=df,
        endpoints_df=endpoints_df,
        conditions_df=conditions_df,
        endpoint_type="AGGREGATED",
        share_conditions={"Concentration bacteria": ["Fraction"]},
    )
    arrays, _ = mx.ProtocolApplication(
        protocol=mx.Protocol(
            topcategory="TOX",
            category=mx.EndpointCategory(code="NPO_1339_SECTION"),
            endpoint="assay",
            guideline=["sop"],
        ),
        effects=effects,
    ).convert_effectrecords2array()

    merged = parser._merge_auxiliary_signals(
        arrays, {"Concentration bacteria": ["Fraction"]}
    )

    assert [e.endpoint for e in merged] == ["Concentration bacteria "]
    primary = merged[0]
    signal_values = np.asarray(primary.signal.values, dtype=float)
    assert sorted(signal_values.ravel().tolist()) == [10.0, 12.0, 28.0, 30.0]

    fraction = primary.signal.auxiliary["Fraction"]
    fraction_values = np.asarray(fraction.values)
    assert set(fraction_values.ravel().tolist()) == {"Total", "Strainer"}
    # "Strainer/Flow-through/Total" is this endpoint's declared enum
    # options, not a physical unit (the blueprint packs both in the same
    # "unit" cell) -- a value_text result must never carry it through as
    # EffectResult.unit, so it must not survive here either.
    assert fraction.unit is None
    # Same shape as the primary signal -- merged in as a true auxiliary
    # signal (one NXdata), not a mismatched/broadcast side array.
    assert fraction_values.shape == signal_values.shape


def test_value_text_endpoint_never_carries_its_unit_cell_as_a_unit():
    """A value_text endpoint's declared "unit" is routinely the field's
    enum options packed into the same blueprint cell, not a physical unit
    -- e.g. "Fraction" declares unit "Strainer/Flow-through/Total",
    "Leachate" declares unit "Yes/No". Attaching that to EffectResult.unit
    made it surface as the written NeXus axis's `units` attribute
    ("Fraction (Strainer/Flow-through/Total)"), which is simply wrong: it
    is not a unit "Total" is measured in.
    """
    df = pd.DataFrame(
        {
            ("Material", "u0"): ["A", "A"],
            ("Fraction", "Strainer/Flow-through/Total"): ["Total", "Strainer"],
        }
    )
    endpoints_df = pd.DataFrame(
        [
            {
                "name": "Fraction",
                "unit": "Strainer/Flow-through/Total",
                "conditions": None,
                "type": "value_text",
            }
        ]
    )
    conditions_df = pd.DataFrame(columns=["name"])
    parser = _bare_parser(template_json={})

    effects = parser._parse_effects_from_dataframe(
        df=df,
        endpoints_df=endpoints_df,
        conditions_df=conditions_df,
        endpoint_type="AGGREGATED",
    )

    assert len(effects) == 2
    assert {e.result.textValue for e in effects} == {"Total", "Strainer"}
    assert all(e.result.unit is None for e in effects)


def test_generate_uuid_matches_java_nameUUIDFromBytes():
    """generate_uuid(prefix, s) must match
    net.enanomapper.parser.ExcelParserConfigurator.generateUUID(prefix, s)
    in nmdataparser/enmexcelparser EXACTLY -- a name-based uuid from the
    bare MD5 of `s`'s UTF-8 bytes (Java's UUID.nameUUIDFromBytes), NOT
    Python's uuid.uuid3 (which additionally hashes a namespace UUID's bytes
    in front of the name, producing a different result for the same input).
    Expected values pinned by evaluating the Java implementation directly.
    """
    from pynanomapper.datamodel.templates.template_parser import generate_uuid

    assert generate_uuid("XLSX", "my-ref-subst") == (
        "XLSX-2783d803-a237-3d01-88ad-048245654a31"
    )


def test_to_protocol_application_uuids_are_deterministic():
    """assay_uuid/investigation_uuid must be the SAME across repeated calls
    on the same workbook -- re-running the pipeline must replace a
    previous NeXus entry, not orphan it under a fresh random uuid4() every
    time (the bug this replaces: assay_uuid/investigation_uuid were plain
    uuid.uuid4() with no relationship to the workbook's own content at
    all).
    """
    parser = _bare_parser(
        template_json={
            "PROTOCOL_TOP_CATEGORY": "TOX",
            "PROTOCOL_CATEGORY_CODE": "NPO_1339_SECTION",
            "METHOD": "ELISA",
            "EXPERIMENT": "IL8 ELISA ALI exposures",
        },
        test_conditions=pd.DataFrame(
            {
                "A": ["Project name", "Work package", "Partner conducting test/assay"],
                "B": ["MOMENTUM", "WP4", "UM"],
            }
        ),
        materials=pd.DataFrame(columns=["ID"]),
        raw=None,
        results=None,
        calibration=None,
    )

    pa1 = parser.to_protocol_application(
        convert_to_arrays=False, uuid_prefix="MOMENTUM"
    )
    pa2 = parser.to_protocol_application(
        convert_to_arrays=False, uuid_prefix="MOMENTUM"
    )

    assert pa1.assay_uuid == pa2.assay_uuid
    assert pa1.investigation_uuid == pa2.investigation_uuid
    assert pa1.assay_uuid.startswith("MOMENTUM-")
    assert pa1.investigation_uuid.startswith("MOMENTUM-")


def test_param_group_maps_to_real_nexus_group():
    """A blueprint's predefined param_group values (CULTURE CONDITIONS,
    CELL LINE DETAILS, MEDIUM, ...) must map onto the real NeXus group they
    belong to (environment/instrument/parameters/calibration), not be
    written verbatim as their own literal top-level NeXus group.
    """
    from pynanomapper.datamodel.templates.template_parser import _map_param_group

    assert _map_param_group("CULTURE CONDITIONS") == "environment"
    assert _map_param_group("CELL LINE DETAILS") == "environment"
    assert _map_param_group("MEDIUM") == "environment"
    assert _map_param_group("INSTRUMENT") == "instrument"
    assert _map_param_group("MEASUREMENT CONDITIONS") == "instrument"
    assert _map_param_group("CALIBRATION") == "calibration"
    assert _map_param_group("OTHER_METADATA") == "parameters"
    assert _map_param_group("RESULT_ANALYSIS") == "parameters"
    # Case-insensitive (pchem's _get_pchem_parameters lowercases its group
    # before this call).
    assert _map_param_group("culture conditions") == "environment"
    # Unrecognized group: passed through unchanged rather than dropped.
    assert _map_param_group("SOME_NEW_GROUP") == "SOME_NEW_GROUP"


def test_get_parameters_uses_mapped_nexus_group_not_blueprint_group():
    """get_parameters()'s keys must carry the MAPPED NeXus group name, not
    the blueprint's own param_group string -- CULTURE CONDITIONS/Exposure
    method, not culture_conditions/... or CULTURE CONDITIONS/... verbatim.
    """
    test_conditions = pd.DataFrame(
        {"A": ["Exposure method"], "B": ["nebulization in cloud"]}
    )
    parser = _bare_parser(
        template_json={
            "METADATA_PARAMETERS": [
                {
                    "param_name": "Exposure method",
                    "param_group": "CULTURE CONDITIONS",
                    "param_unit": None,
                }
            ],
            "METADATA_SAMPLE_PREP": [],
        },
        test_conditions=test_conditions,
    )

    params = parser.get_parameters()

    assert "environment/Exposure method" in params
    assert "CULTURE CONDITIONS/Exposure method" not in params


def test_get_parameters_with_no_group_uses_bare_key():
    """A METADATA_PARAMETERS entry with no declared param_group must not
    write "None/<name>" -- str-interpolating a real Python None into the
    key. Falls back to a bare name (param_lookup's heuristic placement),
    same as any other group-less parameter.
    """
    test_conditions = pd.DataFrame(
        {"A": ["Serum concentration"], "B": [10.0]}
    )
    parser = _bare_parser(
        template_json={
            "METADATA_PARAMETERS": [
                {
                    "param_name": "Serum concentration",
                    "param_group": None,
                    "param_unit": None,
                }
            ],
            "METADATA_SAMPLE_PREP": [],
        },
        test_conditions=test_conditions,
    )

    params = parser.get_parameters()

    assert "Serum concentration" in params
    assert not any(k.startswith("None/") for k in params)


def test_to_substances_raises_when_data_material_has_no_materials_row():
    """A Material value with real data (a control like "non exposed" or
    "blank", commonly not catalogued in the Materials sheet the way a real
    test substance is) but no matching Materials-sheet row must fail
    loudly, not silently drop its records or invent a substance for it --
    same failure mode as "no material matched the selector" below it.
    """
    import pyambit.datamodel as mx

    effects = [
        mx.EffectRecord(
            endpoint="Viability",
            result=mx.EffectResult(loValue=80.0, unit="%"),
            conditions={},
            sampleID="CuO",
        ),
        mx.EffectRecord(
            endpoint="Viability",
            result=mx.EffectResult(loValue=99.0, unit="%"),
            conditions={},
            sampleID="non exposed",
        ),
    ]
    pa = mx.ProtocolApplication(
        protocol=mx.Protocol(
            topcategory="TOX",
            category=mx.EndpointCategory(code="NPO_1339_SECTION"),
            endpoint="assay",
            guideline=["sop"],
        ),
        effects=effects,
    )
    parser = _bare_parser(
        template_json={},
        materials=pd.DataFrame({"ERM identifier": ["CuO"], "ID": ["CuO"]}),
        test_conditions=pd.DataFrame({"A": ["Select item from Project Materials list"], "B": ["CuO"]}),
    )

    with pytest.raises(Exception, match="non exposed"):
        parser.to_substances(pa=pa, convert_to_arrays=False)
