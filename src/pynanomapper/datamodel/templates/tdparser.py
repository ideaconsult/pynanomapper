import json
import pyambit.datamodel as mx
import pandas as pd
import os
from pathlib import Path
from typing import IO
from openpyxl.utils import get_column_letter
import numpy as np
from pynanomapper.datamodel.templates.template_config import TemplateDesignerConfig
from typing import Dict
import uuid
from datetime import datetime


def create_parser(tdconfig: TemplateDesignerConfig, prefix=None):
    if tdconfig.get_layout() == "dose_response":
        raise Exception("note implemented")
    else:
        return TemplateParserPChem(tdconfig, prefix)


class TemplateParserPChem():
    """Parser to convert TemplateDesigner Excel files into AMBIT data model objects."""

    def __init__(self, tdconfig: TemplateDesignerConfig, prefix="XLSX"):
        # call base class __init__ first
        self.prefix = prefix
        self.tdconfig = tdconfig
        self.protocol_applications = {}
        self.citation = mx.Citation(
            owner=self.tdconfig.provider_info.iloc[7, 1],
            title=self.tdconfig.provider_info.iloc[6, 4],
            year=datetime.now().year)        
        self._parse_protocol_applications()


    def _parse_protocol_applications(self):
        for index, row in self.tdconfig.test_conditions.iterrows():
            
            protocol = mx.Protocol(
                topcategory=self.tdconfig.template_json["PROTOCOL_TOP_CATEGORY"],
                category=mx.EndpointCategory(code=self.tdconfig.template_json["PROTOCOL_CATEGORY_CODE"]),
                guideline=[row["Position_ID"]]
            )
            pa = mx.ProtocolApplication(protocol=protocol, effects=[])
            pa.citation = self.citation   
            #pa.parameters = self.get_parameters()
            self.protocol_applications[row["Position_ID"]] = pa
            pa.parameters = self.get_parameters(row)
    
    def get_parameters(self, row):
        params = {}
        params["/experiment_documentation/E.method"] = self.tdconfig.get_method()
        params["/experiment_type"] = self.tdconfig.get_method()
        if self.tdconfig.get_method().lower().startswith("raman"):
            params["/definition"] = "NXraman"
        # 5. Add metadata parameters
        for tag in ["METADATA_PARAMETERS", "METADATA_SAMPLE_PREP"]:
            for p in self.tdconfig.template_json.get(tag, []):
                p_name = p.get("param_name",None)
                if p_name is None:
                    continue
                value = row[p_name]
                if value is None:
                    continue
                p_group = p.get("param_group", "default")

                p_unit = p.get("param_unit", None)
                if p_unit is None:
                    params[f"{p_group.lower()}/{p_name.lower()}"] = value
                else:
                    _val, _unit = self.tdconfig.parse_value_unit(value, p_unit)
                    params[f"{p_group.lower()}/{p_name.lower()}"]  = mx.Value(loValue=_val, unit=_unit)
        return params
    
    def parse_spectrum(self, file_name, method=None):
        try:
            if method == "ATR-FTIR":
                # hardcoded for now, have t  get axis/signal indication in the template
                df = pd.read_csv(os.path.join(Path(self.tdconfig.template_file_name).parent, file_name), skiprows=1)
                    #papp.nx_name = "{} {}".format(material_id,material_name)
                
                data_dict: Dict[str, mx.ValueArray] = {
                    "wavenumber": mx.ValueArray(values=df["cm-1"].values, unit="cm-1")
                }
                ea = mx.EffectArray(
                        endpoint="Absorbance",
                        endpointtype="RAW_DATA",
                        signal=mx.ValueArray(values=df["A"].values, unit="a.u."),
                        axes=data_dict
                )
                return [ea]
            elif method == "Raman spectroscopy":
                spe_file = os.path.join(Path(self.tdconfig.template_file_name).parent, file_name)
                df = pd.read_csv(spe_file, sep="\t", header=None)
                data_dict: Dict[str, mx.ValueArray] = {
                    "wavenumber": mx.ValueArray(values=df.iloc[:, 0].values, unit="cm-1")
                }
                ea = mx.EffectArray(
                        endpoint="Raman intensity",
                        endpointtype="RAW_DATA",
                        signal=mx.ValueArray(values=df.iloc[:, 1].values, unit="a.u."),
                        axes=data_dict
                )
                return [ea]                
            elif method == "PiFM":
                # hardcoded for now, have t  get axis/signal indication in the template
                spe_file = os.path.join(Path(self.tdconfig.template_file_name).parent, file_name)
                if spe_file.endswith(".bmp"):
                    return None
                df = pd.read_csv(spe_file, sep="\t")
                    #papp.nx_name = "{} {}".format(material_id,material_name)
                data_dict: Dict[str, mx.ValueArray] = {
                    "wavenumber": mx.ValueArray(values=df.iloc[:, 0].values, unit="cm-1")
                }
                _pif = df.iloc[:, 1].values
                _attenuation = df["Attenuation"].values
                signal = mx.ValueArray(values=_pif, unit="V")            
                try:
                    signal.auxiliary = {}
                    for i in range(3, len(df.columns)):
                        signal.auxiliary[f"aux_{df.columns[i]}"] = df.iloc[:, i].values
                except Exception as err:
                    print(err)
                ea =[]
                ea.append(mx.EffectArray(
                        endpoint="PiF",
                        endpointtype="RAW_DATA",
                        signal=signal,
                        axes=data_dict))
                
                # scaled
                try:
                    df_valid = df[df["Valid:PiF"] != 0]
                    wavenumber = df_valid.iloc[:, 0].values       # Wavenumber
                    _pif = df_valid.iloc[:, 1].values             # PiF
                    _attenuation = df_valid["Attenuation"].values # Attenuation                
                    _pif_scaled = _pif / _attenuation
                    data_dict: Dict[str, mx.ValueArray] = {
                        "wavenumber": mx.ValueArray(values=wavenumber, unit="cm-1")
                    }
                    signal = mx.ValueArray(values=_pif_scaled, unit="V")
                    ea.append(mx.EffectArray(
                            endpoint="PiF",
                            endpointtype="VALID_SCALED",
                            signal=signal,
                            axes=data_dict
                    ))
                except Exception as err:
                    pass
                return ea
            return None
        except Exception as err:
            print(err)

    def make_uuid(self, identifier):
        return "{}-{}".format(self.prefix, uuid.uuid5(uuid.NAMESPACE_OID, identifier))

    def get_substance(self, mat_id, sample_provider):
        sample_uuid = self.make_uuid(mat_id)
        substance = mx.SubstanceRecord(
            i5uuid=sample_uuid, name=mat_id, publicname=mat_id,
            ownerName=sample_provider, substanceType="tbd")
        return substance

    def parse_results(self):
        substances = []

        sample_provider = self.tdconfig.template_json["provenance_project"]
        company = mx.Company(name=sample_provider)

        for mat, mat_group in self.tdconfig.results.groupby('Material ID'):
            substance = self.get_substance(mat, sample_provider)
            substance.study = []
            for papp, papp_group in mat_group.groupby('Position_ID'):
                pa = self.protocol_applications[papp].copy()
                sample = mx.Sample(uuid=substance.i5uuid)
                pa.owner = mx.SampleLink(substance=sample, company=company)
                pa.nx_name = f"{mat}_{papp}"
                pa.uuid = self.make_uuid(pa.nx_name)
                substance.study.append(pa)
                pa.effects = []
                for index, row in papp_group.iterrows():
                    raw_endpoints = self.tdconfig._get_endpoints_df(tag="raw_data_report")
                    for index, eprow in raw_endpoints.iterrows():
                        name = eprow["name"]
                        value = row[name]
                        if eprow["type"] == "value_file":
                            #ea.nx_name = papp.nx_name
                            ea = self.parse_spectrum(value, self.tdconfig.get_method())
                            if ea is not None:
                                pa.effects.extend(ea)
                        else:
                            er = mx.EffectResult(textValue=value)
                            ef = mx.EffectRecord(endpoint=name, unit=eprow.get("unit", None), result=er)
                            pa.effects.append(ef)
            substances.append(substance)
        return mx.Substances(substance=substances)