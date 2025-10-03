import json
import pyambit.datamodel as mx
import pandas as pd
import os
import re
from typing import IO
from openpyxl.utils import get_column_letter
import numpy as np


class TemplateDesignerParser:
    """Parser to convert TemplateDesigner Excel files into AMBIT data model objects."""

    def __init__(self, xlsx_file: IO):
        self.template_json = self.parse_hidden(xlsx_file)
        tc = pd.read_excel(xlsx_file, sheet_name="Test_conditions", header=None)
        tc.columns = [get_column_letter(i+1) for i in range(tc.shape[1])]
        self.test_conditions = tc
        self.materials = pd.read_excel(xlsx_file, sheet_name="Materials") 
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
        
    def get_endpoints(self):
        return pd._get_rows_from_match(self.test_conditions, "End-Point being investigated/assessed by the test", n_rows=2)

    def parse_hidden(self, xlsx_file: IO):
        template_df = pd.read_excel(xlsx_file, sheet_name="TemplateDesigner")
        #template["uuid"] = template_df.iloc[0]["uuid"]
        #template["json"] = template_df.iloc[0]["surveyjs"]
        #assert template_df.iloc[1]["uuid"] == "version"
        #template["version"] = template_df.iloc[1]["surveyjs"]
        return json.loads(template_df.iloc[0]["surveyjs"])
        
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
        return self._get_rows_from_match(self.test_conditions, "Select item from Project Materials list", n_rows=1)

    def get_protocol_application(self):
        # Define Protocol from template metadata
        protocol = mx.Protocol(
            topcategory=self.template_json["PROTOCOL_TOP_CATEGORY"],
            category=mx.EndpointCategory(code=self.template_json["PROTOCOL_CATEGORY_CODE"]),
            guideline=["tbd"]
        )
        pa = mx.ProtocolApplication(protocol=protocol, effects=[])
        pa.parameters = self.get_parameters()
        return pa

    def get_condition_df(self):
        df = pd.DataFrame(self.template_json["conditions"])
        df = df.rename(columns=lambda x: x.replace("condition_", "", 1))
        return df.rename(columns=lambda x: x.replace("conditon_", "", 1))

    def get_parameters(self):
        params = {}
        # 5. Add metadata parameters
        for tag in ["METADATA_PARAMETERS", "METADATA_SAMPLE_PREP"]:
            for p in self.template_json.get(tag, []):
                p_name = p.get("param_name",None)
                if p_name is None:
                    continue
                value = self._get_rows_from_match(self.test_conditions, p_name, n_rows=1)
                if value.empty:
                    continue
                value = value.iloc[0,0]
                p_group = p.get("param_group", None)
                p_unit = p.get("param_unit", None)
                if p_unit is None:
                    params[f"{p_group}/{p_name}"] = value
                else:
                    _val, _unit = self.parse_value_unit(value, p_unit)
                    params[f"{p_group}/{p_name}"]  = mx.Value(loValue=_val, unit=_unit)
        return params

    def df_to_nd_effectarray_multicol(
        self,
        df: pd.DataFrame,
        axes_names: list,
        main_signal: str,
        aux_signals: list = None,
        endpoint: str = None,
        endpointtype: str = None,
        unit: str = 'counts'
    ):
        """
        Build an nD EffectArray from a DataFrame with MultiIndex columns.

        Parameters
        ----------
        df : pd.DataFrame
            MultiIndex columns: (endpoint, unit)
        axes_names : list
            Names of columns to use as axes
        main_signal : str
            Name of main signal (level 0 of MultiIndex)
        aux_signals : list, optional
            Names of auxiliary signals (level 0 of MultiIndex)
        endpoint : str, optional
            Name of EffectArray endpoint (default = main_signal)
        endpointtype : str, optional
            Type of endpoint
        unit : str
            Unit for signals

        Returns
        -------
        EffectArray
        """

        # --- Detect actual columns in MultiIndex ---
        def pick_column(df, name):
            """
            Return the first matching column tuple for level 0 == name.
            Returns None if column not found.
            """
            for c in df.columns:
                if isinstance(c, tuple) and c[0] == name:
                    return c
                elif c == name:
                    return c
            return None  # skip missing columns

        axis_cols = {ax: col for ax, col in ((ax, pick_column(df, ax)) for ax in axes_names) if col is not None}
        main_col = pick_column(df, main_signal)
        if main_col is None:
            raise ValueError(f"Main signal column '{main_signal}' not found in DataFrame")        
        # Filter auxiliary signals: include only those that exist
        aux_cols = {aux: col for aux, col in ((aux, pick_column(df, aux)) for aux in (aux_signals or [])) if col is not None}

        # --- Build axes ValueArrays dynamically ---
        axes_dict = {}
        for ax, col in axis_cols.items():
            values = pd.unique(df[col])
            axes_dict[ax] = mx.ValueArray(values=values, unit='tbd')

        # --- Prepare nD shape ---
        axes_list = list(axes_dict.keys())
        shape = tuple(len(axes_dict[ax].values) for ax in axes_list)

        # Build index maps
        idx_map = {ax: {val: i for i, val in enumerate(axes_dict[ax].values)} for ax in axes_list}

        # --- Initialize main signal and auxiliary matrices ---
        signal_matrix = np.full(shape, np.nan)
        aux_matrices = {name: np.full(shape, np.nan) for name in aux_cols}

        # --- Fill matrices ---
        for _, row in df.iterrows():
            idx = tuple(idx_map[ax][row[axis_cols[ax]]] for ax in axes_list)
            signal_matrix[idx] = row[main_col]
            for aux_name, aux_col in aux_cols.items():
                aux_matrices[aux_name][idx] = row[aux_col]

        # --- Build auxiliary ValueArrays ---
        auxiliary = {k: mx.ValueArray(values=v, unit=unit) for k, v in aux_matrices.items()} if aux_matrices else None

        # --- Build main signal ValueArray ---
        signal_va = mx.ValueArray(
            values=signal_matrix,
            unit=unit,
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
            df = pd.DataFrame(self.template_json["raw_data_report"])
            df = df.rename(columns=lambda x: x.replace("raw_", "", 1))
            df = df.rename(columns={"endpoint": "name"})
            return self._parse_data(self.raw, df)

    def parse_processed_data(self):
        if self.results is None:
            return None, None
        else:
            df = pd.DataFrame(self.template_json["question3"])
            df = df.rename(columns=lambda x: x.replace("result_", "", 1))
            df = df.rename(columns=lambda x: x.replace("results_", "", 1))
            return self._parse_data(self.results, df)

    def parse_calibration(self):
        pass