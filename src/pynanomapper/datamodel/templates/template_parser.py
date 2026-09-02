import hashlib
import uuid
import pyambit.datamodel as mx
import pandas as pd
import numbers
import re
from typing import IO, List
from openpyxl.utils import get_column_letter
import numpy as np
from pynanomapper.datamodel.templates.template_config import TemplateDesignerConfig


def generate_uuid(prefix: str, s: str) -> str:
    """"{prefix}-{name-uuid}", matching
    net.enanomapper.parser.ExcelParserConfigurator.generateUUID(prefix, s) in
    nmdataparser/enmexcelparser exactly: a name-based UUID from the bare MD5
    of `s`'s UTF-8 bytes, with the version (3) and variant bits patched in --
    i.e. Java's `UUID.nameUUIDFromBytes`, NOT Python's `uuid.uuid3` (which
    additionally prepends a namespace UUID's bytes before hashing, so it is
    NOT a drop-in equivalent and produces a different UUID for the same
    input).

    Deterministic: converting the SAME workbook/material/assay identity
    again produces the SAME uuid, so re-running the pipeline replaces a
    previous NeXus entry instead of leaving it orphaned under a fresh random
    id every time. `prefix` is caller-supplied (project-specific, like
    nmdataparser's own default "XLSX") rather than hardcoded here.
    """
    digest = bytearray(hashlib.md5(s.encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # version 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # variant
    return "{}-{}".format(prefix, str(uuid.UUID(bytes=bytes(digest))))

# Template Designer blueprints declare a fixed, predefined set of
# METADATA_PARAMETERS/METADATA_SAMPLE_PREP `param_group` values -- not free
# text, an enumeration -- so each is mapped explicitly onto the real NeXus
# group it belongs to (pyambit.nexus_writer.to_nexus's parameter loop splits
# a "<group>/<name>" parameter key on "/" and writes it as a nested NeXus
# group, using whatever the first segment says verbatim). Without this, a
# blueprint group like "CULTURE CONDITIONS" or "CELL LINE DETAILS" was
# written as its own literal top-level NeXus group instead of joining the
# standard vocabulary (environment/instrument/parameters) other readers
# expect. Keys are matched case-insensitively -- get_parameters() uses the
# blueprint's own casing, _get_pchem_parameters() lowercases it first.
PARAM_GROUP_TO_NEXUS_GROUP = {
    "CALIBRATION": "calibration",
    "CELL LINE DETAILS": "environment",
    "CULTURE CONDITIONS": "environment",
    "ENVIRONMENT": "environment",
    "INSTRUMENT": "instrument",
    "MEASUREMENT CONDITIONS": "instrument",
    "MEDIUM": "environment",
    "OTHER_METADATA": "parameters",
    "RESULT_ANALYSIS": "parameters",
}


def _map_param_group(group) -> str:
    """The real NeXus group a blueprint `param_group` belongs to, via
    PARAM_GROUP_TO_NEXUS_GROUP (case-insensitive) -- or the group name
    unchanged when it is not one of the predefined blueprint groups, so an
    unrecognized group still writes somewhere sensible instead of being
    silently dropped.
    """
    if group is None:
        return group
    mapped = PARAM_GROUP_TO_NEXUS_GROUP.get(str(group).strip().upper())
    return mapped if mapped is not None else group


class TemplateDesignerParser(TemplateDesignerConfig):
    """Parser to convert TemplateDesigner Excel files into AMBIT data model objects."""

    def __init__(self, xlsx_file: IO):
        self.template_json = self.parse_hidden(xlsx_file)
        self.materials = pd.read_excel(xlsx_file, sheet_name="Materials")
        if self.template_json.get("template_layout") == "pchem":
            self._init_pchem(xlsx_file)
            return
        tc = pd.read_excel(xlsx_file, sheet_name="Test_conditions", header=None)
        tc.columns = [get_column_letter(i+1) for i in range(tc.shape[1])]
        self.test_conditions = tc
        _data_sheets = self.template_json["data_sheets"]
        if "data_raw" in _data_sheets:
            self.raw = pd.read_excel(xlsx_file, sheet_name="Raw_data_TABLE", header=[0,1])
        else:
            self.raw = None
        if "data_processed" in _data_sheets:
            self.results = pd.read_excel(xlsx_file, sheet_name="Results_TABLE", header=[0,1])
        else:
            self.results = None
        if "data_calibration" in _data_sheets:
            self.calibration = pd.read_excel(xlsx_file, sheet_name="Calibration_TABLE", header=[0,1])
        else:
            self.calibration = None

    def _init_pchem(self, xlsx_file: IO) -> None:
        """The "pchem" layout (FTIR, SLS, XRF): one Results_TABLE holding
        both raw and processed data (per-column `type`/`unit` in its own
        4-level header, no separate Raw_data_TABLE), a fixed-cell
        Provider_informations sheet instead of Test_conditions, and a
        Measuring_conditions sheet of per-Position_ID instrument settings
        instead of a single set of protocol parameters.

        `self.test_conditions` / `self.raw` / `self.calibration` stay None --
        that vocabulary belongs to the "dose_response" layout, and every
        place that reads them already checks for None first.
        """
        self.test_conditions = None
        self.raw = None
        self.calibration = None
        self.provider_info = pd.read_excel(
            xlsx_file, sheet_name="Provider_informations", header=None
        )
        self.results = pd.read_excel(
            xlsx_file, sheet_name="Results_TABLE", header=[0, 1, 2, 3]
        )
        measuring_conditions = pd.read_excel(
            xlsx_file, sheet_name="Measuring_conditions", header=[0, 1, 2]
        )
        position_col = self.pick_column(measuring_conditions, "Position_ID")
        self.measuring_conditions = (
            measuring_conditions[measuring_conditions[position_col].notna()]
            if position_col is not None
            else measuring_conditions
        )
        samples = pd.read_excel(xlsx_file, sheet_name="SAMPLES", header=[0, 1])
        material_col = self.pick_column(samples, "Material ID")
        self.samples = (
            samples[samples[material_col].notna()]
            if material_col is not None
            else samples
        )

   
    def parse_value_unit(self, s, unit=None):
        """
        Parses a string with a numeric value followed by a unit.
        
        Args:
            s: Input string, e.g. "12.5 mg", "100kg", "3.2e-4 mol"
            
        Returns:
            tuple: (value as float, unit as string)
                Returns (s, "") if input is not a string.
        """
        if not isinstance(s, str):
            # If already a number or None, return as value with empty unit
            return s, unit
        
        s = s.strip()
        match = re.match(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(.*)", s)
        if match:
            value = float(match.group(1))
            unit = match.group(2).strip()
            return value, unit
        else:
            # Could not parse, return original string as unitless value
            return s, unit

    def _get_rows_from_match(self, df, search_text, n_rows=1, start_col="B"):
        """
        Finds the row in column 'A' matching search_text and returns a subset DataFrame
        starting from start_col to the first empty column, for n_rows downward.

        Args:
            df (pd.DataFrame): The DataFrame to search.
            search_text: Value to find in column 'A'.
            n_rows (int): Number of rows to take starting from the found row.
            start_col (str): Column to start from (default "B").

        Returns:
            pd.DataFrame: Subset of the DataFrame with header columns.
                        Empty DataFrame if search_text not found.
        """
        # Find the row index
        matching_rows = df[df["A"] == search_text]
        if matching_rows.empty:
            return pd.DataFrame(columns=df.columns)  # empty DF with same headers

        start_row_idx = matching_rows.index[0]
        end_row_idx = start_row_idx + n_rows

        # Determine the range of columns from start_col to first empty in the first matched row
        start_idx = df.columns.get_loc(start_col)
        row = df.iloc[start_row_idx]

        # Find first empty column after start_col
        end_idx = start_idx
        for col in df.columns[start_idx:]:
            if pd.isna(row[col]) or row[col] == "":
                break
            end_idx += 1

        subset_df = df.iloc[start_row_idx:end_row_idx, start_idx:end_idx]

        return subset_df

    def get_materials_used(self):
        if self.template_json.get("template_layout") == "pchem":
            # No selector cell in this layout -- SAMPLES (and Results_TABLE)
            # are already keyed directly by Material ID, so the materials
            # actually used are exactly the distinct values that appear
            # there, same shape contract as the dose_response branch below
            # (a single-row frame; to_substances() reads .iloc[0]).
            col = self.pick_column(self.samples, "Material ID")
            values = self.samples[col].dropna().unique() if col is not None else []
            return pd.DataFrame([values])
        return self._get_rows_from_match(self.test_conditions, "Select item from Project Materials list", n_rows=1)

    def _provider_cell(self, row: int, col: int):
        """One 0-indexed (row, col) cell of Provider_informations (the
        pchem-layout equivalent of Test_conditions), or None if the sheet is
        absent, too small, or the cell is blank. Cell addresses match
        blueprint.py's pchem_format_2excel, which writes these fixed
        addresses when generating the sheet.
        """
        info = getattr(self, "provider_info", None)
        if info is None or row >= info.shape[0] or col >= info.shape[1]:
            return None
        value = info.iat[row, col]
        return None if pd.isna(value) else str(value).strip()

    def get_project_name(self):
        """The project the data belongs to.

        dose_response: cell A1 of Test_conditions. pchem: cell B6 of
        Provider_informations ("Project").

        Either way this is the OWNER of the substances a workbook reports
        on: the individual partner ran the assay, but the material and the
        data belong to the project. Returns None when the sheet has no such
        header.
        """
        if self.template_json.get("template_layout") == "pchem":
            return self._provider_cell(5, 1)
        if self.test_conditions is None or self.test_conditions.empty:
            return None
        value = self.test_conditions.iloc[0, 0]
        return None if pd.isna(value) else str(value).strip()

    def get_partner(self):
        """The partner that actually ran the assay.

        dose_response: the row labelled "Partner conducting test/assay" in
        Test_conditions. pchem: cell B8 of Provider_informations
        ("Partner").

        This is who the data is CITED to, as opposed to the project that owns
        it (see get_project_name).
        """
        if self.template_json.get("template_layout") == "pchem":
            return self._provider_cell(7, 1)
        row = self._get_rows_from_match(
            self.test_conditions, "Partner conducting test/assay"
        )
        if row.empty:
            return None
        value = row.iloc[0, 0]
        return None if pd.isna(value) else str(value).strip()

    def get_work_package(self):
        """The project work package the assay belongs to.

        dose_response: the row labelled "Project Work Package" in
        Test_conditions (e.g. "WP4"). pchem: cell B7 of
        Provider_informations ("Workpackage").
        """
        if self.template_json.get("template_layout") == "pchem":
            return self._provider_cell(6, 1)
        row = self._get_rows_from_match(
            self.test_conditions, "Project Work Package"
        )
        if row.empty:
            return None
        value = row.iloc[0, 0]
        return None if pd.isna(value) else str(value).strip()

    def get_start_year(self):
        """The year the assay was run -- from the "Test start date" row of
        Test_conditions.

        These are unpublished lab records, so there is no publication year;
        the date the work was done is the meaningful one to cite them by.
        Provider_informations (pchem) carries no equivalent date field, so
        this always returns None for that layout.
        """
        if self.template_json.get("template_layout") == "pchem" or self.test_conditions is None:
            return None
        row = self._get_rows_from_match(self.test_conditions, "Test start date")
        if row.empty:
            return None
        value = row.iloc[0, 0]
        if pd.isna(value):
            return None
        parsed = pd.to_datetime(value, errors="coerce")
        return None if pd.isna(parsed) else int(parsed.year)

    def get_protocol_application(self):
        # Define Protocol from template metadata
        protocol = mx.Protocol(
            topcategory=self.template_json["PROTOCOL_TOP_CATEGORY"],
            category=mx.EndpointCategory(code=self.template_json["PROTOCOL_CATEGORY_CODE"]),
            guideline=[self.template_json["METHOD"]]
        )
        pa = mx.ProtocolApplication(protocol=protocol, effects=[])
        pa.parameters = self.get_parameters()
        return pa

    def _add_excel_col_letters(self, c_df: pd.DataFrame, cols_array, col_letter="col_letter") -> pd.DataFrame:
        """
        Adds an Excel-style column letter to each row in c_df where the 'name' matches a column in cols_array.

        Parameters
        ----------
        c_df : pd.DataFrame
            DataFrame with a column 'name' containing the logical column names.
        cols_array : Index or list
            Column array (can be MultiIndex or list of strings).

        Returns
        -------
        pd.DataFrame
            c_df with an additional column 'col_letter' containing Excel letters.
        """
        # An empty `conditions`/endpoints declaration (a template with none
        # of that kind) makes c_df a zero-column frame with no "name" column
        # at all -- nothing to look up, return it unchanged rather than
        # crash on c_df["name"].
        if "name" not in c_df.columns:
            return c_df

        # Build mapping from column names to Excel letters
        name_to_letter = {}
        for i, col in enumerate(cols_array):
            col_name = col[0] if isinstance(col, tuple) else col
            if col_name in c_df["name"].values:
                name_to_letter[col_name] = get_column_letter(i + 1)  # Excel is 1-based

        # Add 'col_letter' column
        c_df = c_df.copy()
        c_df[col_letter] = c_df["name"].map(name_to_letter)
        return c_df

    def get_condition_df(self):
        df = pd.DataFrame(self.template_json["conditions"])
        df = df.rename(columns=lambda x: x.replace("condition_", "", 1))
        df = df.rename(columns=lambda x: x.replace("conditon_", "", 1))
        if self.results is not None:
            df = self._add_excel_col_letters(df, self.results.columns, col_letter="results_pos")
        if self.raw is not None:            
            df = self._add_excel_col_letters(df, self.raw.columns, col_letter="raw_pos")
        return df

    def get_parameters(self):
        if self.template_json.get("template_layout") == "pchem":
            return self._get_pchem_parameters()
        params = {}
        # 5. Add metadata parameters
        for tag in ["METADATA_PARAMETERS", "METADATA_SAMPLE_PREP"]:
            for p in self.template_json.get(tag, []):
                p_name = p.get("param_name", None)
                p_group = p.get("param_group", None)
                p_unit = p.get("param_unit", None)                
                if p_name is None:
                    continue
                value = self._get_rows_from_match(self.test_conditions, p_name, n_rows=1)
                if value.empty:
                    continue
                value = value.iloc[0,0]
                # No declared group: a bare name, NOT "None/<name>" (str
                # interpolating a real Python None) -- nexus_writer's
                # param_lookup() already has a heuristic for placing a
                # single-segment key, which is the correct fallback here.
                nx_group = _map_param_group(p_group)
                param_key = f"{nx_group}/{p_name}" if nx_group else p_name
                if p_unit is None:
                    if isinstance(value, numbers.Number):
                        params[param_key] = mx.Value(loValue=value)
                    elif pd.isna(value):
                        pass
                    else:
                        params[param_key] = value  # already string
                else:
                    _val, _unit = self.parse_value_unit(value, p_unit)
                    # parse_value_unit falls back to returning the original
                    # string unchanged when it cannot find a leading number
                    # (e.g. "m/z 100" -- a unit label, not a measured
                    # quantity). mx.Value.loValue is numeric-only, so a
                    # non-numeric _val must be stored as a plain string
                    # parameter instead, the same as the p_unit is None
                    # branch above already does.
                    if isinstance(_val, numbers.Number):
                        params[param_key] = mx.Value(
                            loValue=_val, unit=_unit
                        )
                    elif not pd.isna(_val):
                        params[param_key] = _val
        return params

    # --- Detect actual columns in MultiIndex safely ---
    def pick_column(self, df, name):
        """Return first matching column tuple for level 0 == name; None if not found."""
        for c in df.columns:
            if isinstance(c, tuple) and c[0] == name:
                return c
            elif c == name:
                return c
        return None

    @staticmethod
    def _column_looks_numeric(values, threshold: float = 0.9) -> bool:
        """True if at least `threshold` of the non-null values in `values`
        parse as numbers.

        Used to override a template's `value_text` declaration for an
        endpoint whose unit alone cannot tell a real unit ("mL") from an
        enum list packed into the unit field ("Strainer/Flow-through/
        Total") -- both are just non-empty strings. Real case: a "Volume"
        endpoint declared value_text with unit "mL", whose actual recorded
        values were plain numbers (0.2, 0.022, ...) -- written through as
        digit strings under EffectResult.textValue, that value then broke
        the NeXus write entirely (nexus_writer force-casts anything named
        "textValue" to string dtype and cannot write a float array through
        that path). The recorded values themselves settle what the
        declared unit cannot.
        """
        values = pd.Series(values).dropna()
        if values.empty:
            return False
        numeric = pd.to_numeric(values, errors="coerce")
        return numeric.notna().mean() > threshold

    @staticmethod
    def _numeric_axis_values(values):
        """Coerce axis values to numeric where the text just wraps a number
        ("Replicate 1" -> 1.0); anything else is returned unchanged.

        The implementation now lives in pyambit.datamodel.numeric_axis_values,
        beside the record->array conversion that is the real consumer of the
        rule. pyambit cannot import pynanomapper (the dependency runs the
        other way, see pyambit/units.py), so it moved down rather than being
        duplicated; this stays as the parser's own name for it.
        """
        return mx.numeric_axis_values(values)
    
    def df_to_nd_effectarray_multicol(
        self,
        df: pd.DataFrame,
        axes_dict: dict,
        main_signal: str,
        aux_signals: list = None,
        endpoint: str = None,
        endpointtype: str = None,
    ):
        """
        Build an nD EffectArray from a DataFrame with MultiIndex columns.

        Units are automatically taken from the second level of the MultiIndex.
        """

        # --- Get units from second level of MultiIndex ---
        def get_unit(col):
            if isinstance(col, tuple) and len(col) > 1:
                unit = col[1]
                # The second header level is sometimes NaN (a float), not
                # "Unnamed: N" (a str), when a column has no unit row at all
                # -- pd.isna() catches that; a bare `unit is None` check does
                # not, and NaN is truthy, so returning it unchanged here used
                # to defeat the caller's own blueprint-unit fallback (the
                # `or` never triggered because `nan` is not falsy).
                #
                # A real unit cell is always text -- when a workbook is
                # missing its units header row entirely, pandas reads the
                # first DATA row as that second level instead, and whatever
                # ended up under this particular column can be anything
                # (e.g. an int like 24). Not a str -> not a unit, same
                # verdict as NaN, rather than crashing mx.ValueArray(unit=...)
                # (which requires a str) on a stray data value.
                if (
                    unit is None
                    or pd.isna(unit)
                    or not isinstance(unit, str)
                    or unit.startswith("Unnamed")
                ):
                    return None
                return unit
            return None

        axes_names = list(axes_dict.keys())
        # Filter columns that exist
        axis_cols = {ax: col for ax, col in ((ax, self.pick_column(df, ax)) for ax in axes_names) if col is not None}
        for ax in axes_names or []:
            col = self.pick_column(df, ax)
            if col is not None:
                axis_cols[ax] = col

        main_col = self.pick_column(df, main_signal)
        if main_col is None:
            raise ValueError(f"Main signal column '{main_signal}' not found in DataFrame")
        aux_cols = {}
        aux_signals = list(aux_signals) if aux_signals is not None else []
        for aux in aux_signals:
            col = self.pick_column(df, aux)
            if col is not None:
                aux_cols[aux] = col

        # --- Build axes ValueArrays dynamically ---
        # idx_map is keyed on the RAW column values (row lookups below use
        # those), while axes_dict stores the numeric-coerced values where
        # possible ("Replicate 1" -> 1.0): an object-dtype axis has no HDF5
        # equivalent, and the label text carries no information the number
        # doesn't. The two must stay separate -- coercing axes_dict in place
        # would break the row lookup, which still sees the raw text.
        #
        # Unit precedence: the caller's blueprint-resolved unit (passed in
        # via the `axes_dict` parameter, which this loop is about to
        # overwrite) FIRST, falling back to the DataFrame's own MultiIndex
        # header (get_unit) only when the blueprint declares none. The
        # blueprint is the trusted schema -- it says what a condition's unit
        # actually is -- while a data table's own unit cell is exactly the
        # thing repeatedly found corrupted across this corpus (blank, an int
        # that leaked from a missing-header-row-consumed data row, or even a
        # plausible-looking but WRONG string like a stray "Replicate 1" for
        # the same reason). Preferring the header would then silently prefer
        # garbage over a unit the blueprint already got right.
        caller_units = {ax: va.unit for ax, va in axes_dict.items()}
        axes_dict = {}
        idx_map = {}
        for ax, col in axis_cols.items():
            raw_values = pd.unique(df[col])
            _unit = caller_units.get(ax) or get_unit(col)
            axes_dict[ax] = mx.ValueArray(
                values=self._numeric_axis_values(raw_values), unit=_unit
            )
            idx_map[ax] = {val: i for i, val in enumerate(raw_values)}

        # --- Prepare nD shape ---
        axes_list = list(axes_dict.keys())
        shape = tuple(len(axes_dict[ax].values) for ax in axes_list)

        # --- Initialize main signal and auxiliary matrices ---
        signal_matrix = np.full(shape, np.nan)
        aux_matrices = {}
        for aux_name, col_id in aux_cols.items():  # col_id is the MultiIndex tuple
            col_data = df[col_id]                 # get the actual column
            if np.issubdtype(col_data.dtype, np.number):
                aux_matrices[aux_name] = np.full(shape, np.nan)
            else:
                aux_matrices[aux_name] = np.full(shape, None, dtype=object)

        # --- Fill matrices ---
        for _, row in df.iterrows():
            try:
                idx = tuple(
                    idx_map[ax][row[axis_cols[ax]]] for ax in axes_list
                )
            except KeyError:
                # A row with no value on one of this endpoint's axes -- e.g. a
                # vehicle/H2O2 control that has no `concentration` in a
                # dose-response table -- legitimately has no cell in this
                # signal matrix. pd.unique() keeps NaN as a distinct axis
                # value, but dict lookup on NaN is not reliably reflexive
                # (nan != nan), so the same "missing axis value" row can
                # raise KeyError here rather than silently matching its own
                # NaN. Either way the row does not belong in this endpoint's
                # matrix: skip it rather than losing the whole EffectArray to
                # one row.
                continue
            signal_matrix[idx] = row[main_col]
            for aux_name, aux_col in aux_cols.items():
                aux_matrices[aux_name][idx] = row[aux_col]

        main_unit = get_unit(main_col)
        auxiliary = {k: mx.ValueArray(values=v, unit=get_unit(aux_cols[k])) for k, v in aux_matrices.items()} if aux_matrices else None

        # --- Build main signal ValueArray ---
        signal_va = mx.ValueArray(
            values=signal_matrix,
            unit=main_unit,
            auxiliary=auxiliary
        )

        # --- Build EffectArray ---
        earray = mx.EffectArray(
            endpoint=endpoint or main_signal,
            endpointtype=endpointtype,
            conditions={},
            signal=signal_va,
            axes=axes_dict,
            axis_groups=None
        )
        return earray

    def parse(self) -> mx.Substances:
        _data_sheets = self.template_json["data_sheets"]    
        if "data_raw" in _data_sheets:
            self.parse_raw_data()
        if "data_processed" in _data_sheets:
            self.parse_processed_data()
        if "data_calibration" in _data_sheets:
            self.parse_calibration()

    def _parse_data(self, data=None, endpoints_df=None):
        if data is None:
            return
        for index, row in data.iterrows():
            for (name, unit) in data.columns:
                value = row[(name, unit)]   # <-- this gives the cell value
                _unit = None if unit.startswith("Unnamed") else unit
                if name == "Material":
                    print(value)
                else:
                    if pd.notna(value):
                        print(f"Row {index}, {name} [{_unit}] = {value}")
                                               
        return data, endpoints_df
    
    def parse_raw_data(self):
        if self.raw is None:
            return None, None
        else:
            df = self._get_endpoints_df_raw()
            return self._parse_data(self.raw, df)

    def parse_processed_data(self):
        if self.results is None:
            return None, None
        else:
            df = self._get_endpoints_df_results()
            return self._parse_data(self.results, df)

    def _get_endpoints_df(self, tag="raw_data_report"):
        df = pd.DataFrame(self.template_json[tag])
        df = df.rename(columns=lambda x: x.replace("raw_", "", 1))
        df = df.rename(columns={"endpoint": "name"})
        df = df.rename(columns=lambda x: x.replace("result_", "", 1))
        df = df.rename(columns=lambda x: x.replace("results_", "", 1))
        return df

    def get_endpoints_df_raw(self):
        df = self._get_endpoints_df(tag="raw_data_report")
        return self._add_excel_col_letters(df, self.raw.columns, col_letter="raw_pos")

    def get_endpoints_df_results(self):
        df = self._get_endpoints_df(tag="question3")
        return self._add_excel_col_letters(df, self.results.columns, col_letter="results_pos")

    def _get_config_effects(self, cols_array, conditions_df, endpoints,
                            col_pos="raw_pos", sheet_name=None):
        effects = []
        for i, col in enumerate(cols_array):
            e = endpoints.loc[endpoints["name"] == col[0]]
            if not e.empty:
                col_letter = get_column_letter(i + 1) 
                effectrecord = {"ENDPOINT" : col[0], 
                                "VALUE" : { "COLUMN_INDEX": col_letter}
                                }
                if sheet_name is not None:
                    effectrecord["SHEET_NAME"] = sheet_name
                endpoint_type = e.get("aggregate",None)
                if endpoint_type is not None:
                    if not pd.isna(endpoint_type.values[0]):
                        effectrecord["ENDPOINT_TYPE"] = endpoint_type.values[0]
                conditions = e.get("conditions",None)
                if conditions is not None:
                    effectrecord["CONDITIONS"] = {}
                    conditions = conditions.values[0]
                    for cond in conditions:
                        c = conditions_df.loc[conditions_df["name"] == cond]
                        if not c.empty:
                            effectrecord["CONDITIONS"][cond] = {"COLUMN_INDEX" : c[col_pos].values[0]}
                if not pd.isna(e["unit"].values[0] ):
                    effectrecord["UNIT"] = e["unit"].values[0]
                effects.append(effectrecord)
        return effects
    
    def get_config(self):
        if self.get_layout() == "dose_response":
            config = {}
            config["PROTOCOL_APPLICATIONS"] = []
            config["PROTOCOL_APPLICATIONS"].append(self.get_config_papp())
            return config
        else:
            raise Exception("Not implemented")

    def get_config_params(self):
        config = {}
        # 5. Add metadata parameters
        for tag in ["METADATA_PARAMETERS", "METADATA_SAMPLE_PREP"]:
            for p in self.template_json.get(tag, []):
                p_name = p.get("param_name",None)
                if p_name is None:
                    continue
                value = self._get_rows_from_match(self.test_conditions, p_name, n_rows=1)
                if value.empty:
                    continue
                p_group = p.get("param_group", None)
                p_unit = p.get("param_unit", None)            
                config[f"{p_group}/{p_name}"] = {"ITERATION": "ABSOLUTE_LOCATION",
                        "SHEET_INDEX": 1,
                        "COLUMN_INDEX": "B",
                        "ROW_INDEX": value.index[0]
                        }
                if p_unit is not None:
                    config[f"{p_group}/{p_name}"]["UNIT"] = p_unit
        return config

    def get_config_papp(self):
        return {
            "PROTOCOL_TOP_CATEGORY" : None,
			"PROTOCOL_ENDPOINT": None,
			"PROTOCOL_CATEGORY_CODE": None,
			"PROTOCOL_GUIDELINE": {
				"guideline1": {
					"COLUMN_INDEX": None
				}
			},
			"CITATION_YEAR": {
				"COLUMN_INDEX": None,
				"DATA_INTERPRETATION": "AS_DATE"
			},
			"CITATION_TITLE": {
				"COLUMN_INDEX": None
			},
			"CITATION_OWNER": {
				"COLUMN_INDEX": None
			},
            "PARAMETERS": self.get_config_params(),
            "EFFECTS": self.get_config_effects(),
        }

    def get_config_effects(self):
        effects_raw = []
        effects_result = []
        if self.raw is not None:
            effects_raw = self._get_config_effects(
                cols_array=self.raw.columns,
                conditions_df=self.get_condition_df(), 
                endpoints=self.get_endpoints_df_raw(),
                col_pos="raw_pos",
                sheet_name="Raw_data_TABLE")
        if self.results is not None:
            effects_result = self._get_config_effects(
                cols_array=self.results.columns,
                conditions_df=self.get_condition_df(), 
                endpoints=self.get_endpoints_df_results(), 
                col_pos="results_pos",
                sheet_name="Results_TABLE")
        effects_raw.extend(effects_result)
        return effects_raw

    def parse_calibration(self):
        return None

    def to_protocol_application(
        self,
        convert_to_arrays: bool = True,
        text_conditions: List[str] = None,
        share_conditions: dict = None,
        uuid_prefix: str = "XLSX",
    ) -> mx.ProtocolApplication:
        """
        Convert parsed Excel template to AMBIT ProtocolApplication.

        Args:
            convert_to_arrays: assemble the parsed EffectRecords into
                EffectArrays via convert_effectrecords2array(). Pass False to
                get the flat EffectRecord form instead -- that is the AMBIT
                interchange representation: it serializes to JSON as-is, so
                it can be dumped for verification or handed to the original
                AMBIT importers, neither of which an assembled array grid
                supports.
            uuid_prefix: passed to generate_uuid() for assay_uuid/
                investigation_uuid -- project-specific (matches
                nmdataparser's own ExcelParserConfigurator.generateUUID,
                whose default is likewise a plain string, not derived from
                the workbook), so a caller converting several projects'
                workbooks through the same pipeline can keep their UUID
                spaces from colliding.

        Returns:
            ProtocolApplication object with protocol, parameters, and effects

        Example:
            >>> parser = TemplateDesignerParser("template.xlsx")
            >>> pa = parser.to_protocol_application()
            >>> print(pa.protocol.category.code)
        """
        # Get protocol from template metadata. `endpoint` is the METHOD itself
        # ("AFIM", "Py-GC-MS") -- the field a consumer reads to know which
        # technique produced the data -- while `guideline` stays the
        # EXPERIMENT/SOP text (a prose description, not a method name).
        protocol = mx.Protocol(
            topcategory=self.template_json.get("PROTOCOL_TOP_CATEGORY"),
            category=mx.EndpointCategory(
                code=self.template_json.get("PROTOCOL_CATEGORY_CODE", "")
            ),
            endpoint=self.template_json.get("METHOD"),
            guideline=[self.template_json.get("EXPERIMENT", "")]
        )
        
        # Get parameters
        parameters = self.get_parameters()
        
        # Parse effects from raw and processed data.
        #
        # Both tables are flattened to plain EffectRecords -- one per data row
        # per endpoint, carrying that row's declared conditions -- and NOT
        # assembled into EffectArrays here. Building the nD signal grid (and
        # splitting it on categorical conditions) is exactly what
        # ProtocolApplication.convert_effectrecords2array() already does for
        # every pyambit consumer: it groups by endpointtype/endpoint/unit,
        # detects string-only condition columns (find_string_only_columns),
        # splits into one EffectArray per distinct combination of those
        # (split_df_by_columns), and strips text that just wraps a number
        # ("Replicate 1" -> 1) via transform_array. Duplicating any of that
        # here would be a second, divergent implementation of the same rules.
        #
        # The flat EffectRecord list is also the AMBIT interchange
        # representation -- it round-trips to JSON, so a template's parse can
        # be dumped for verification or fed to the original AMBIT Java
        # importers, which an EffectArray grid cannot be.
        effects = []

        if self.template_json.get("template_layout") == "pchem":
            # One Results_TABLE holds both raw and processed data already
            # tagged per column (see _parse_effects_from_pchem) -- there is
            # no separate Raw_data_TABLE/Results_TABLE split to iterate.
            effects.extend(
                self._parse_effects_from_pchem(text_conditions=text_conditions)
            )
        else:
            if self.raw is not None:
                effects.extend(
                    self._parse_effects_from_dataframe(
                        df=self.raw,
                        endpoints_df=self.get_endpoints_df_raw(),
                        conditions_df=self.get_condition_df(),
                        endpoint_type="RAW_DATA",
                        text_conditions=text_conditions,
                        share_conditions=share_conditions,
                    )
                )

            if self.results is not None:
                effects.extend(
                    self._parse_effects_from_dataframe(
                        df=self.results,
                        endpoints_df=self.get_endpoints_df_results(),
                        conditions_df=self.get_condition_df(),
                        endpoint_type="AGGREGATED",
                        text_conditions=text_conditions,
                        share_conditions=share_conditions,
                    )
                )
        # investigation_uuid links related investigations across DIFFERENT
        # assay types run on the same project/work package -- e.g. a
        # physchem characterization and its paired bioassay -- so every
        # workbook that shares project+work_package must resolve to the
        # SAME uuid; a random uuid4() per file could never do that no
        # matter how many times the pipeline reruns.
        project_name = self.get_project_name()
        work_package = self.get_work_package()
        investigation_uuid = self.template_json.get("investigation_uuid")
        if investigation_uuid is None and project_name:
            investigation_uuid = generate_uuid(
                uuid_prefix, f"{project_name}/{work_package or ''}"
            )
        elif investigation_uuid is None:
            investigation_uuid = str(uuid.uuid4())

        # assay_uuid identifies "the same assay" across the several files it
        # is commonly split into -- project-scoped (the same technique name
        # exists in other projects too) and specific enough to separate real
        # protocol variants (e.g. ELISA run submerged vs ALI), which
        # guideline (the EXPERIMENT/SOP text) already distinguishes.
        assay_uuid = self.template_json.get("assay_uuid")
        if assay_uuid is None and project_name:
            assay_uuid = generate_uuid(
                uuid_prefix,
                "/".join(
                    x
                    for x in (project_name, protocol.endpoint, *(protocol.guideline or []))
                    if x
                ),
            )
        elif assay_uuid is None:
            assay_uuid = str(uuid.uuid4())

        # Create ProtocolApplication
        pa = mx.ProtocolApplication(
            protocol=protocol,
            effects=effects,
            parameters=parameters,
            uuid=str(uuid.uuid4()),
            investigation_uuid=investigation_uuid,
            assay_uuid=assay_uuid,
            citation=mx.Citation(
                owner=(
                    self.get_partner()
                    or self.template_json.get("provenance_provider")
                    or "Unknown"
                ),
                title=(
                    self.get_work_package()
                    or self.template_json.get("EXPERIMENT")
                    or "Template Designer Export"
                ),
                year=self.get_start_year()
            )
        )

        # Grid-build/split the flat records into EffectArrays, in the one
        # shared place that knows how (see comment above).
        if convert_to_arrays:
            pa.effects, _ = pa.convert_effectrecords2array()

        return pa

    def _get_pchem_parameters(self) -> dict:
        """File-level parameters for the pchem layout, from the first
        populated row of Measuring_conditions.

        Measuring_conditions is keyed by Position_ID -- instrument settings
        genuinely can vary per position -- but ProtocolApplication.parameters
        is one flat dict for the whole file, with nowhere to attach a value
        per position. Taking the first row is a real simplification (see
        AGENTS.md); most of this corpus's pchem workbooks use one instrument
        configuration throughout, so it is usually also the only row.
        Naming matches tdparser.py's TemplateParserPChem.get_parameters
        ("{group}/{name}", lowercased) for consistency with that prior
        implementation of the same idea.
        """
        params = {}
        table = getattr(self, "measuring_conditions", None)
        if table is None or table.empty:
            return params
        row = table.iloc[0]
        for col in table.columns:
            if not isinstance(col, tuple) or col[0] != "METADATA_PARAMETERS":
                continue
            group, name = col[1], col[2]
            value = row[col]
            if pd.isna(value):
                continue
            # No declared group (a NaN column level): a bare name, not
            # "nan/<name>" -- same fix as get_parameters()'s dose_response
            # branch, for the same reason.
            mapped_group = _map_param_group(group)
            param_key = (
                f"{str(mapped_group).lower()}/{str(name).lower()}"
                if mapped_group is not None and not pd.isna(mapped_group)
                else str(name).lower()
            )
            params[param_key] = value
        return params

    def _parse_effects_from_pchem(
        self, text_conditions: List[str] = None
    ) -> List[mx.EffectRecord]:
        """Flatten pchem's single Results_TABLE into plain EffectRecords --
        the same flat-record contract _parse_effects_from_dataframe produces
        for dose_response, so to_substances() and
        convert_effectrecords2array() work unchanged regardless of layout.

        Results_TABLE already self-describes each column's endpoint name,
        aggregate/type tag and unit in its own 4-level header (see
        _init_pchem), generated straight from the SAME raw_data_report /
        question3 / conditions blueprint sections dose_response uses --
        reused here via _get_endpoints_df() and get_condition_df() rather
        than re-deriving endpoint/condition metadata a second way.

        `text_conditions` (same override as the dose_response branch, kept
        under its original name though it is no longer only about text)
        names raw_data_report endpoints that are actually the x-axis of the
        OTHER endpoints in the same row, but which the blueprint declares as
        a plain endpoint rather than a condition. Real case: FTIR/SLS declare
        "Wavenumber (cm-1)"/"Wavelength" as their own RAW_DATA endpoint, with
        no raw_conditions on "Transmission"/"Number"/"Volume" pointing at it
        -- every spectrum then wrote as several independent scalar series
        instead of one signal plotted against its axis.
        """
        effects: List[mx.EffectRecord] = []
        df = self.results
        if df is None:
            return effects

        material_col = self.pick_column(df, "Material ID")
        position_col = self.pick_column(df, "Position_ID")

        endpoints = pd.concat(
            [
                self._get_endpoints_df(tag="raw_data_report"),
                self._get_endpoints_df(tag="question3"),
            ],
            ignore_index=True,
        )
        endpoint_meta = {
            row["name"]: row for _, row in endpoints.iterrows() if "name" in row
        }
        condition_units = self._condition_units(self.get_condition_df())
        condition_names = set(condition_units)
        promoted = set(text_conditions or [])

        endpoint_cols = []
        condition_cols = {}
        for col in df.columns:
            if col in (material_col, position_col) or not isinstance(col, tuple):
                continue
            top, name = col[0], col[1]
            if top == "Experimental factors" and name in condition_names:
                condition_cols[name] = col
            elif name in promoted and name in endpoint_meta:
                # Promoted to a condition of every other endpoint in the
                # row -- its own declared unit, not looked up in
                # condition_units (the blueprint never listed it there).
                condition_cols[name] = col
                promoted_unit = endpoint_meta[name].get("unit")
                condition_units.setdefault(
                    name, None if pd.isna(promoted_unit) else promoted_unit
                )
            elif name in endpoint_meta:
                endpoint_cols.append((name, col))
            # else: a column the blueprint declared but never gave data for
            # in this particular workbook (e.g. an unused "Results" slot) --
            # nothing to attach it to.

        # A value_text endpoint whose recorded values are nearly all numbers
        # anyway is trusted as numeric -- same override as the dose_response
        # branch (_column_looks_numeric's own docstring has the real case:
        # "Volume" declared value_text with unit "mL", genuinely 0.2/0.022/...
        # throughout). Computed once per endpoint column, not per row.
        text_endpoints = {
            name
            for name, col in endpoint_cols
            if endpoint_meta[name].get("type") == "value_text"
            and not self._column_looks_numeric(df[col])
        }

        for idx in df.index:
            material = (
                None
                if material_col is None or pd.isna(df.at[idx, material_col])
                else str(df.at[idx, material_col]).strip()
            )

            conditions = {}
            for cond_name, cond_col in condition_cols.items():
                raw = df.at[idx, cond_col]
                if pd.isna(raw):
                    continue
                numeric = pd.to_numeric(raw, errors="coerce")
                cond_unit = condition_units.get(cond_name)
                conditions[cond_name] = (
                    mx.Value(loValue=float(numeric), unit=cond_unit)
                    if not pd.isna(numeric)
                    else str(raw)
                )

            for name, col in endpoint_cols:
                value = df.at[idx, col]
                if pd.isna(value):
                    continue
                meta = endpoint_meta[name]
                unit = meta.get("unit")
                unit = None if pd.isna(unit) else unit
                endpoint_type = meta.get("aggregate")
                endpoint_type = None if pd.isna(endpoint_type) else endpoint_type

                # The template says whether an endpoint is a number or text
                # ("value_num" / "value_text"); same rule as the
                # dose_response branch, including the same one override --
                # see text_endpoints above.
                if name in text_endpoints:
                    # A value_text endpoint's "unit" cell is not a physical
                    # unit -- real workbooks pack the field's allowed
                    # categories in it instead (e.g. "Fraction" carries
                    # "Strainer/Flow-through/Total", "Leachate" carries
                    # "Yes/No"). Attaching that as EffectResult.unit made it
                    # show up as the axis's NeXus `units` attribute, which is
                    # simply wrong -- "Strainer/Flow-through/Total" is not a
                    # unit "Total" is measured in.
                    result = mx.EffectResult(textValue=str(value), unit=None)
                else:
                    numeric_value = pd.to_numeric(value, errors="coerce")
                    if pd.isna(numeric_value):
                        continue
                    result = mx.EffectResult(loValue=float(numeric_value), unit=unit)

                effects.append(
                    mx.EffectRecord(
                        endpoint=name,
                        endpointtype=endpoint_type,
                        result=result,
                        conditions=dict(conditions),
                        sampleID=material,
                    )
                )

        return effects

    @staticmethod
    def _axes_match(a: mx.EffectArray, b: mx.EffectArray) -> bool:
        """True if two EffectArrays were built over the same axes -- same
        names, same values -- i.e. they measure the same rows and can share
        one NXdata as signal + auxiliary signal."""
        a_axes, b_axes = (a.axes or {}), (b.axes or {})
        if set(a_axes) != set(b_axes):
            return False
        for name, a_axis in a_axes.items():
            b_axis = b_axes[name]
            a_values = np.asarray(a_axis.values)
            b_values = np.asarray(b_axis.values)
            if a_values.shape != b_values.shape:
                return False
            if a_values.dtype.kind in "fiu" and b_values.dtype.kind in "fiu":
                if not np.allclose(
                    a_values.astype(float), b_values.astype(float), equal_nan=True
                ):
                    return False
            elif not np.array_equal(a_values, b_values):
                return False
        return True

    def _merge_auxiliary_signals(
        self, effects: List[mx.EffectRecord], primary_to_aux: dict
    ) -> List[mx.EffectRecord]:
        """Fold each of `primary_to_aux[primary]`'s arrays into `primary`'s
        own array as an auxiliary signal, for one already-assembled EffectArray
        list (i.e. called after convert_effectrecords2array()).

        A primary/aux pair might have been split into several EffectArrays
        each (a categorical condition neither declares as such, say) -- match
        each primary to its aux candidate structurally, by shared
        `conditions` and `axes`, rather than assuming there is exactly one of
        each and they already line up.
        """
        # Keyed by stripped endpoint name: MOMENTUM endpoint names routinely
        # carry incidental trailing whitespace ("Concentration bacteria "),
        # and a primary_to_aux entry that silently fails to match here would
        # just leave every candidate unmerged with no error at all.
        by_endpoint: dict = {}
        for effect in effects:
            by_endpoint.setdefault((effect.endpoint or "").strip(), []).append(effect)

        consumed = set()
        for primary_name, aux_names in primary_to_aux.items():
            for primary in by_endpoint.get(primary_name.strip(), []):
                if getattr(primary, "signal", None) is None:
                    continue
                auxiliary = dict(primary.signal.auxiliary or {})
                for aux_name in aux_names:
                    for candidate in by_endpoint.get(aux_name.strip(), []):
                        if (
                            id(candidate) in consumed
                            or getattr(candidate, "signal", None) is None
                        ):
                            continue
                        if candidate.conditions == primary.conditions and (
                            self._axes_match(primary, candidate)
                        ):
                            # A candidate that is itself purely categorical
                            # (no loValue/upValue anywhere, only textValue --
                            # see _parse_effects_from_dataframe's
                            # is_text_endpoint) has NO real content in its
                            # own signal: create_multidimensional_matrix
                            # never lets textValue become the primary
                            # signal_col, so that signal is an all-NaN
                            # placeholder and the real values are one level
                            # down, in ITS OWN textValue auxiliary. Fold
                            # THAT in under aux_name, not the empty
                            # placeholder, when it has one.
                            own_text = (candidate.signal.auxiliary or {}).get(
                                "textValue"
                            )
                            if own_text is not None:
                                # create_multidimensional_matrix's own
                                # aux dict holds plain ndarrays, not
                                # ValueArray -- nexus_writer treats a bare
                                # ndarray as unit-less and borrows the
                                # PRIMARY signal's unit for it (a real,
                                # separately-fixed bug elsewhere this
                                # session: "a plain ValueArray fell
                                # through to the ndarray branch"). Wrap it
                                # so the merged-in aux keeps its own
                                # declared unit, not Concentration
                                # bacteria's CFU/mL.
                                auxiliary[aux_name] = mx.ValueArray(
                                    values=own_text, unit=candidate.signal.unit
                                )
                            else:
                                auxiliary[aux_name] = candidate.signal
                            consumed.add(id(candidate))
                            break
                if auxiliary:
                    primary.signal.auxiliary = auxiliary

        return [e for e in effects if id(e) not in consumed]

    def to_substances(
        self,
        pa: mx.ProtocolApplication = None,
        aux_signals: dict = None,
        convert_to_arrays: bool = True,
        uuid_prefix: str = "XLSX",
    ) -> mx.Substances:
        """
        Convert parsed Excel to Substances with study data.

        Creates SubstanceRecord objects from the Materials sheet and attaches
        the protocol application as study data.

        Args:
            pa: Use this ProtocolApplication instead of building a fresh one
                via `to_protocol_application()`. Lets a caller merge several
                files' data (e.g. independent repeat experiments) into one PA
                first, then attach it to the Materials-sheet substances the
                normal way. Per-substance routing (by EffectRecord.sampleID)
                only works when `pa.effects` is still the flat EffectRecord
                form -- pass it as built by
                to_protocol_application(convert_to_arrays=False), not
                pre-converted, or every substance gets the whole file's data
                again (an EffectArray carries no sampleID to route by).
            aux_signals: {primary_endpoint: [aux_endpoint, ...]} -- fold each
                aux endpoint's array into the primary's as an auxiliary
                signal (one NXdata instead of two) when both share the same
                conditions and axes -- i.e. they are two views of the same
                measurement (e.g. SLS's Number/Volume distribution over the
                same Wavelength bins). No template field declares this
                relationship, so it cannot be inferred; it is a per-dataset
                override like `text_conditions`, applied after
                convert_effectrecords2array() has built the independent
                arrays. See _merge_auxiliary_signals. Ignored when
                convert_to_arrays is False (nothing to merge yet).
            convert_to_arrays: assemble each substance's own flat
                EffectRecords into EffectArrays (grid-building, categorical
                splitting -- see convert_effectrecords2array). Pass False to
                keep the flat, per-substance-ROUTED EffectRecord form -- the
                AMBIT interchange representation (see
                to_protocol_application's own convert_to_arrays), still
                correctly split by material, just not yet grid-built.

        Returns:
            Substances object containing all materials with study data

        Example:
            >>> parser = TemplateDesignerParser("template.xlsx")
            >>> substances = parser.to_substances()
            >>> print(f"Found {len(substances.substance)} substances")
        """
        substances = []

        # Get protocol application (shared across all materials)
        if pa is None:
            pa = self.to_protocol_application()

        # Parse materials from Materials sheet. Stripped on both sides before
        # matching -- the selector cell (Test_conditions) and the Materials
        # sheet's own "ERM identifier" column are two separately hand-filled
        # areas of the workbook, and incidental whitespace on either one
        # ("TiO2 " vs "TiO2") must not silently drop that material from the
        # file's substances entirely.
        _materials_used = [
            str(m).strip() for m in self.get_materials_used().iloc[0].to_numpy()
        ]
        # The selector cell ("Select item from Project Materials list")
        # only lists the materials under TEST -- it has no reason to also
        # list assay controls (vehicle, vehicle+prop, non exposed, a
        # cytokine-stimulant positive control, calibration standards, ...),
        # yet those routinely appear as real Material values in the row
        # data. Restricting to the selector alone silently dropped every
        # one of their EffectRecords (has_material_column routing below
        # keeps a record only for a material that got a SubstanceRecord)
        # -- real, correctly-recorded measurements, not noise. Every
        # distinct sampleID actually present in the data gets its own
        # substance, whether or not the selector or even the Materials
        # sheet itself mentions it -- the sheet is a hand-maintained master
        # list and can legitimately be missing an entry the data table
        # still names correctly.
        _materials_in_data = {
            str(getattr(effect, "sampleID", None)).strip()
            for effect in pa.effects
            if getattr(effect, "sampleID", None) is not None
        }
        _materials_used = list(dict.fromkeys(_materials_used).keys() | _materials_in_data)
        filtered_materials = self.materials[
            self.materials["ERM identifier"].astype(str).str.strip().isin(_materials_used)
        ]
        # sampleIDs with real data but no Materials-sheet row at all --
        # give each a minimal synthetic row (same "ERM identifier" shape
        # the loop below already reads) instead of dropping their records.
        _known_ids = set(
            filtered_materials["ERM identifier"].astype(str).str.strip()
        )
        _unmatched_ids = [m for m in _materials_in_data if m not in _known_ids]
        if _unmatched_ids:
            # A material with real data but no Materials sheet row at all
            # is a data-entry defect on the provider's side (the sheet is a
            # hand-maintained master list) -- fail loudly rather than
            # silently inventing a substance, same failure mode as "no
            # material matched the selector" below.
            raise Exception(
                "Material(s) with real data have no matching row in the "
                f"Materials sheet: {_unmatched_ids!r}. Add a row for each "
                "to the Materials sheet before converting this workbook."
            )

        # The project owns the substances; the partner that ran the assay is
        # who the study is cited to AND who nexus_writer records as the
        # sample's provider (papp.owner.company.name -> sample/provider) --
        # both read from the same cell (B8, "Partner", in Provider_
        # informations for pchem), same as citation.owner.
        owner_name = (
            self.get_project_name()
            or self.template_json.get("provenance_provider")
            or "Unknown"
        )
        provider_name = self.get_partner() or owner_name

        # True if ANY record carries a sampleID -- i.e. the source table had
        # a "Material" column at all. See the per-substance filtering below:
        # when it's False (e.g. Py-GC-MS, whose "materials" are reference
        # standards quantified in every run, not one per row), every record
        # stays available to every substance, since there is nothing to
        # route by.
        has_material_column = any(
            getattr(effect, "sampleID", None) is not None for effect in pa.effects
        )

        if filtered_materials is not None and not filtered_materials.empty:
            for idx, material_row in filtered_materials.iterrows():
                # Extract material ID - try different column names
                material_id = None
                for id_col in ['ID', 'ERM identifier' ]:
                    if id_col in material_row and pd.notna(material_row[id_col]):
                        # Stripped to match the row-level Material value in
                        # _parse_effects_from_dataframe's sampleID (also
                        # stripped) -- the Materials sheet and the raw/
                        # results table are two separately hand-filled
                        # areas of the same workbook, and incidental
                        # leading/trailing whitespace on one side ("CuO "
                        # vs "CuO") must not break routing a substance's
                        # own data to it.
                        material_id = str(material_row[id_col]).strip()
                        break

                if material_id is None:
                    material_id = str(uuid.uuid4())

                # Extract material TYPE (chemical class name, e.g. "Polystyrene",
                # is deliberately NOT used as the substance's name/publicname:
                # dozens of catalogue entries share one chemical class, so that
                # would collapse distinct materials -- different suppliers,
                # batches, surface treatments -- into one identity. material_id
                # (the catalogue ID/ERM identifier) is what is actually specific
                # to this experiment.
                material_type = str(material_row["type"]) if "type" in material_row and pd.notna(material_row["type"]) else None

                # Create SubstanceRecord
                substance = mx.SubstanceRecord(
                    i5uuid=material_id,
                    name=material_id,
                    publicname=material_id,
                    substanceType=material_type,  # Default, could be parameterized
                    ownerName=owner_name,
                    # Derived from the OWNER, not from the material: every
                    # substance a project owns has to resolve to the same
                    # owner, otherwise each material looks like its own
                    # separate owner downstream.
                    ownerUUID=str(uuid.uuid5(uuid.NAMESPACE_OID, owner_name))
                )
                
                # Clone protocol application for this substance -- with only
                # ITS OWN effects, not the whole file's. A row-level table
                # commonly reports several materials at once (a dose series,
                # its vehicle control, a shared calibration curve, ...); every
                # EffectRecord carries which one it is about in `sampleID`
                # (see _parse_effects_from_dataframe), so route on that
                # instead of attaching the same effects list to every
                # substance. `has_material_column` distinguishes "this record
                # is not about any one material" (no Material column in the
                # table at all -- keep it for every substance, e.g. Py-GC-MS
                # polymer-standard quantities that legitimately apply across
                # every run) from "this record belongs to a DIFFERENT
                # material" (drop it).
                own_effects = [
                    effect
                    for effect in pa.effects
                    if not has_material_column
                    or getattr(effect, "sampleID", None) in (None, material_id)
                ]
                pa_copy = mx.ProtocolApplication(
                    protocol=pa.protocol,
                    effects=own_effects,
                    parameters=pa.parameters,
                    # Deterministic, keyed by this assay + this material --
                    # re-running the pipeline over the same workbook must
                    # replace the previous NeXus entry for this substance
                    # instead of writing a fresh, unrelated one every time.
                    uuid=generate_uuid(uuid_prefix, f"{pa.assay_uuid}/{material_id}"),
                    investigation_uuid=pa.investigation_uuid,
                    assay_uuid=pa.assay_uuid,
                    citation=pa.citation,
                    # nexus_writer.to_nexus uses this directly for the
                    # written entry's group name and NXdata title in place of
                    # the default "{provider}_{uuid}" -- a readable material
                    # id there beats an opaque uuid, and disambiguates entries
                    # from different substances in the same corpus folder.
                    nx_name=material_id,
                    owner=mx.SampleLink(
                        substance=mx.Sample(uuid=material_id),
                        company=mx.Company(name=provider_name)
                    )
                )
                if any(isinstance(e, mx.EffectArray) for e in own_effects):
                    # Records were already assembled into arrays before this
                    # ran (convert_to_arrays=True on to_protocol_application) --
                    # an array no longer carries a single row's sampleID, so
                    # per-material filtering was not possible; only the
                    # flat-record form supports it (see
                    # to_protocol_application). This method's own
                    # convert_to_arrays applies to the ALREADY-routed records
                    # below, not this (already too late) case.
                    pass
                elif own_effects and convert_to_arrays:
                    pa_copy.effects, _ = pa_copy.convert_effectrecords2array()
                    if aux_signals:
                        pa_copy.effects = self._merge_auxiliary_signals(
                            pa_copy.effects, aux_signals
                        )

                # Add protocol application as study
                substance.study = [pa_copy]
                substances.append(substance)
        else:
            # This is reachable even when the Materials sheet exists and is
            # populated: `filtered_materials` is also empty when none of the
            # selector's values matches an "ERM identifier" row, e.g. a
            # workbook whose "Select item from Project Materials list" cell
            # still holds the unfilled column-header placeholder text
            # instead of an actual material -- a data-entry defect on the
            # provider's side, not a missing sheet. Report both possible
            # values so it is diagnosable from the message alone.
            raise Exception(
                "No material matched: 'Select item from Project Materials "
                f"list' = {list(_materials_used)!r}, but Materials sheet "
                f"has ERM identifiers {self.materials['ERM identifier'].tolist()!r}"
            )
        
        return mx.Substances(substance=substances)

    def _condition_units(self, conditions_df: pd.DataFrame) -> dict:
        """{condition name: declared unit or None} straight from the template.

        The template's own `conditions` block is the authority on what a
        condition is and what unit it carries -- not the data table's header
        row, which across this corpus is variously blank, a stray number, or
        a value that leaked out of a mis-shaped header.
        """
        units = {}
        if conditions_df is None or "name" not in conditions_df:
            return units
        for _, row in conditions_df.iterrows():
            unit = row.get("unit", None)
            units[row["name"]] = None if pd.isna(unit) else unit
        return units

    def _parse_effects_from_dataframe(
        self,
        df: pd.DataFrame,
        endpoints_df: pd.DataFrame,
        conditions_df: pd.DataFrame,
        endpoint_type: str = "RAW_DATA",
        text_conditions: List[str] = None,
        share_conditions: dict = None,
    ) -> List[mx.EffectRecord]:
        """
        Flatten a data table (raw or results) into plain EffectRecords -- one
        per data row per endpoint, carrying that row's declared conditions.

        Assembling these into nD EffectArrays (and splitting on categorical
        conditions) is deliberately NOT done here: that is
        ProtocolApplication.convert_effectrecords2array()'s job, called once
        by to_protocol_application(). See the comment there.

        Args:
            df: DataFrame with multi-level column headers (endpoint, unit)
            endpoints_df: DataFrame with endpoint metadata
            conditions_df: DataFrame with condition metadata
            endpoint_type: Type of endpoint ("RAW_DATA" or "AGGREGATED")

        Returns:
            List of EffectRecord objects
        """
        effects = []

        # Conditions are exactly the ones the template declares as such.
        condition_units = self._condition_units(conditions_df)

        # `text_conditions` names value_text endpoints to be treated as
        # conditions of the other endpoints in the same row instead.
        #
        # Some templates declare a column that QUALIFIES a row -- which gene
        # a Cq belongs to, which compartment was sampled -- as a value_text
        # endpoint rather than as a condition. Kept as an endpoint it is a
        # text "measurement", and a text signal is not plottable (h5web
        # rejects a non-numeric signal), while the numeric endpoints it
        # qualifies are left with nothing to index them by. Naming it here
        # moves it to the side of the model it belongs on, which also lets
        # the record->array conversion split on it and yield one numeric
        # array per value. This is a per-dataset override precisely because
        # it cannot be inferred from the template -- the template says the
        # opposite.
        promoted = set(text_conditions or [])

        # {borrower_name: primary_name} -- a borrower endpoint grid-builds
        # over the PRIMARY's own declared conditions instead of (typically)
        # none of its own. Two endpoints built over the same conditions from
        # the same table naturally come out with identical axes (same
        # pd.unique() input, same order) -- the same reason two endpoints
        # that independently declare the same real condition merge cleanly
        # via aux_signals (e.g. SLS's Number/Volume, both declaring
        # Wavelength). This is for the case neither declares it: real case,
        # a template where "Fraction"/"Leachate"/"Temperature" describe the
        # SAME row's "Concentration bacteria" measurement but declare no
        # conditions of their own at all, so aux_signals alone has no shared
        # axes to match them by.
        # Keyed by stripped borrower name -- looked up below via
        # endpoint_name.strip(), same whitespace tolerance as the primary
        # lookup itself (see the comment there).
        borrows_from = {}
        for primary_name, borrowers in (share_conditions or {}).items():
            for borrower_name in borrowers:
                borrows_from[borrower_name.strip()] = primary_name

        # Get endpoint columns from endpoints_df
        endpoint_col = "name" if "name" in endpoints_df else "endpoint"
        if endpoint_col not in endpoints_df:
            return effects
        
        endpoint_names = endpoints_df[endpoint_col].tolist()
        
        # For each endpoint, create an EffectArray
        promoted_cols = {}
        for name in promoted:
            col = self.pick_column(df, name)
            if col is not None:
                promoted_cols[name] = col

        # Which material each row is actually about. A row-level table
        # commonly reports on several materials at once (doses of one
        # material, its vehicle control, a shared calibration curve, ...);
        # without this, every record in the table would end up attached to
        # every one of those materials, not just its own -- to_substances()
        # uses it to route each record to its own substance. Not a
        # `conditions` entry: this identifies WHICH SAMPLE a record belongs
        # to, not a value the record was measured across, so it must not
        # become a grid axis when convert_effectrecords2array() runs.
        material_col = self.pick_column(df, "Material")

        for endpoint_name in endpoint_names:
            if endpoint_name in promoted:
                continue  # carried as a condition of the other endpoints
            # Find the column in df
            endpoint_col_tuple = self.pick_column(df, endpoint_name)
            if endpoint_col_tuple is None:
                continue
            
            # Get endpoint metadata
            endpoint_meta = endpoints_df[endpoints_df[endpoint_col] == endpoint_name]
            if endpoint_meta.empty:
                continue
            
            endpoint_meta = endpoint_meta.iloc[0]
            
            # Get unit. The second header level is sometimes NaN (float), not
            # "Unnamed: N" (str), when a workbook's column has no unit row at
            # all -- pd.isna() catches that case (str(nan) == "nan", which
            # does NOT start with "Unnamed", so a plain .startswith() guard
            # let it through). Same fix as df_to_nd_effectarray_multicol's
            # get_unit(), which already handles both forms correctly.
            unit = None
            if isinstance(endpoint_col_tuple, tuple) and len(endpoint_col_tuple) > 1:
                raw_unit = endpoint_col_tuple[1]
                # A real unit cell is always text; anything else (a stray
                # data value that leaked into the header row -- see
                # get_unit() in df_to_nd_effectarray_multicol for the same
                # fix) is not a unit either, same verdict as NaN.
                unit = (
                    None
                    if raw_unit is None
                    or pd.isna(raw_unit)
                    or not isinstance(raw_unit, str)
                    or raw_unit.startswith("Unnamed")
                    else raw_unit
                )
            
            # Conditions for this endpoint -- exactly the ones the template
            # declares for it, no more (unless share_conditions says this
            # endpoint borrows another's -- see borrows_from above).
            # Stripped before matching: real MOMENTUM endpoint names
            # routinely carry incidental trailing whitespace ("Concentration
            # bacteria " vs the "Concentration bacteria" a caller writes in
            # pipeline.yaml), and a share_conditions entry that silently
            # fails to match falls back to no borrowed conditions at all --
            # exactly the same class of mismatch fixed elsewhere for
            # material identifiers.
            if endpoint_name.strip() in borrows_from:
                primary_name = borrows_from[endpoint_name.strip()].strip()
                primary_meta = endpoints_df[
                    endpoints_df[endpoint_col].astype(str).str.strip()
                    == primary_name
                ]
                endpoint_conditions = (
                    primary_meta.iloc[0].get("conditions")
                    if not primary_meta.empty
                    else None
                )
            else:
                endpoint_conditions = endpoint_meta.get("conditions", [])
            if endpoint_conditions is None:
                endpoint_conditions = []
            if isinstance(endpoint_conditions, float) and np.isnan(endpoint_conditions):
                endpoint_conditions = []

            # The template says whether an endpoint is a number or text
            # ("value_num" / "value_text"); nothing here sniffs the data to
            # second-guess it -- except this one override: a value_text
            # endpoint whose recorded values are nearly all numbers anyway
            # (a real case: "Volume", declared value_text with unit "mL",
            # actually 0.2/0.022/... throughout) is trusted as numeric, since
            # the declared unit alone cannot tell a real unit from an enum
            # list packed into the same field ("Yes/No", "PA/PP/PVC") and the
            # data itself is decisive where that is ambiguous. Everything
            # else downstream of the record -- which conditions are
            # categorical enough to split on, stripping text that merely
            # wraps a number ("Replicate 1" -> 1) -- stays
            # convert_effectrecords2array()'s job.
            is_text_endpoint = endpoint_meta.get(
                "type", None
            ) == "value_text" and not self._column_looks_numeric(
                df[endpoint_col_tuple]
            )

            cond_cols = {}
            for cond_name in endpoint_conditions:
                cond_col = self.pick_column(df, cond_name)
                if cond_col is not None:
                    cond_cols[cond_name] = cond_col
            # Promoted columns qualify every endpoint in the row, whether or
            # not the template listed them among that endpoint's conditions
            # (it did not -- that is the defect being worked around).
            for cond_name, cond_col in promoted_cols.items():
                cond_cols.setdefault(cond_name, cond_col)

            for idx in df.index:
                value = df.at[idx, endpoint_col_tuple]
                if pd.isna(value):
                    continue

                conditions = {}
                for cond_name, cond_col in cond_cols.items():
                    raw = df.at[idx, cond_col]
                    if pd.isna(raw):
                        # This row has no value for that condition (e.g. a
                        # vehicle control with no concentration) -- omit it
                        # rather than inventing one.
                        continue
                    cond_unit = condition_units.get(cond_name)
                    numeric = pd.to_numeric(raw, errors="coerce")
                    if cond_unit is not None and not pd.isna(numeric):
                        # A condition the template gave a unit is a measured
                        # quantity, so carry it as a Value -- that is what
                        # keeps the declared unit attached to the axis the
                        # conversion builds from these records.
                        conditions[cond_name] = mx.Value(
                            loValue=float(numeric), unit=cond_unit
                        )
                    else:
                        conditions[cond_name] = raw

                if is_text_endpoint:
                    # Same fix as _parse_effects_from_pchem's text branch: a
                    # value_text endpoint's declared "unit" is routinely the
                    # field's enum options, not a physical unit (e.g.
                    # "Fraction" -> "Strainer/Flow-through/Total", "Leachate"
                    # -> "Yes/No") -- never carry it through as the result's
                    # unit.
                    result = mx.EffectResult(textValue=str(value), unit=None)
                else:
                    numeric_value = pd.to_numeric(value, errors="coerce")
                    if pd.isna(numeric_value):
                        # The template declares this endpoint numeric, so a
                        # cell that is not a number is a "not measured"
                        # marker ("-", "n.d."), not a result to record.
                        continue
                    result = mx.EffectResult(loValue=float(numeric_value), unit=unit)

                material = (
                    None
                    if material_col is None or pd.isna(df.at[idx, material_col])
                    else str(df.at[idx, material_col]).strip()
                )
                effects.append(
                    mx.EffectRecord(
                        endpoint=endpoint_name,
                        endpointtype=endpoint_type,
                        result=result,
                        conditions=conditions,
                        sampleID=material,
                    )
                )

        return effects
