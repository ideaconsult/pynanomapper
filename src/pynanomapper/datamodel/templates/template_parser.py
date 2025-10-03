import json
import pyambit.datamodel as mx
import pandas as pd
import os
import re
from typing import IO
from openpyxl.utils import get_column_letter


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