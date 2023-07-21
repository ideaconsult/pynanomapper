import numpy as np
from pydantic import validate_arguments

from . import measurements as mx
from . ambit_deco import add_ambitmodel_method
import nexusformat.nexus as nx
import pandas as pd
import re

# Usage
# from  pynanomapper.datamodel.nexus_utils import to_nexus
# from  pynanomapper.datamodel.measurements import ProtocolApplication
# pa = ProtocolApplication(**json_data)
# import nexusformat.nexus.tree as nx
# ne = pa.to_nexus(nx.NXroot())
# print(ne.tree)
@add_ambitmodel_method(mx.ProtocolApplication)
def to_nexus(papp : mx.ProtocolApplication, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    #https://manual.nexusformat.org/classes/base_classes/NXentry.html
    entry_id = "entry_{}".format(papp.uuid)
    nx_root[entry_id] = nx.tree.NXentry()
    nx_root['{}/entry_identifier_uuid'.format(entry_id)] = papp.uuid

    nx_root['{}/definition'.format(entry_id)] = papp.__class__.__name__
    #experiment_identifier
    #experiment_description
    #collection_identifier collection of related measurements or experiments.
    nx_root['{}/collection_identifier'.format(entry_id)] = papp.investigation_uuid
    nx_root['{}/experiment_identifier'.format(entry_id)] = papp.assay_uuid
    #collection_description

    #duration
    #program_name
    #revision
    #experiment_documentation (SOP)
    #notes
    #USER: (optional) NXuser
    #SAMPLE: (optional) NXsample
    #INSTRUMENT: (optional) NXinstrument
    #COLLECTION: (optional) NXcollection
    #MONITOR: (optional) NXmonitor
    #PARAMETERS: (optional) NXparameters Container for parameters, usually used in processing or analysis.
    #PROCESS: (optional) NXprocess
    #SUBENTRY: (optional) NXsubentry Group of multiple application definitions for “multi-modal” (e.g. SAXS/WAXS) measurements.

    if not (papp.protocol is None):
        instrument_id = '{}/protocol'.format(entry_id)
        #papp.protocol.endpoint
        #papp.protocol.topcategory
        #papp.protocol.category
        #papp.protocol.guideline
        #experiment_documentation
        experiment_documentation = nx.NXnote()
        nx_root['{}/experiment_documentation'.format(entry_id)] = experiment_documentation

        category = nx.NXgroup()
        experiment_documentation["category"] = category
        category.attrs["topcategory"] = papp.protocol.topcategory
        category.attrs["code"] = papp.protocol.category.code
        category.attrs["term"] = papp.protocol.category.term
        category.attrs["title"] = papp.protocol.category.title
        category.attrs["endpoint"] = papp.protocol.endpoint
        for guide in papp.protocol.guideline:
            experiment_documentation["guideline"] = papp.protocol.guideline
            break

    if not (papp.citation is None):
        citation_id = '{}/reference'.format(entry_id)
        nx_root[citation_id] = nx.NXcite()
        nx_root[citation_id]["title"] = papp.citation.title
        nx_root[citation_id]["year"] = papp.citation.year
        nx_root[citation_id]["owner"] = papp.citation.owner
        #url, doi, description

    if not (papp.parameters is None):
        instrument_id = '{}/instrument'.format(entry_id)
        params_id = '{}/parameters'.format(entry_id)
        env_id = '{}/environment'.format(entry_id)
        instrument = nx.NXinstrument()
        parameters = nx.NXcollection()
        environment = nx.NXenvironment()
        sample = nx.tree.NXsample()
        for prm in papp.parameters:
            value = papp.parameters[prm]
            target = environment
            if  "instrument" in prm.lower():
                target = instrument
            elif  "sample" in prm.lower():
                target = sample
            elif  "material" in prm.lower():
                target = sample
            elif ("ASSAY" == prm.upper()) or ("E.METHOD" == prm.upper()):
                target = instrument
            elif ("E.SOP_REFERENCE" == prm):
                target = instrument
            elif ("OPERATOR" == prm):
                target = instrument
            elif (prm.startswith("T.")):
                target = instrument
            if "EXPERIMENT_END_DATE" == prm:
                nx_root[entry_id]["end_time"] = value
            elif "EXPERIMENT_START_DATE" == prm:
                nx_root[entry_id]["start_time"] = value
            elif isinstance(value,str):
                target[prm] = nx.NXfield(str(value))
            elif isinstance(value,mx.Value):
                #tbd ranges?
                target[prm] = nx.NXfield(value.loValue,unit=value.unit)
        nx_root[instrument_id] = instrument
        nx_root[params_id] = parameters
        nx_root[env_id] = environment
        nx_root['{}/sample'.format(entry_id)] = sample

    if not (papp.owner is None):
        try:
            sample["uuid"] = papp.owner.substance.uuid
            sample["provider"] = papp.owner.company.name
        except:
            pass

    try:
        process_pa(papp,nx_root[entry_id])
    except Exception as err:
        print(err)
    return nx_root


@add_ambitmodel_method(mx.Study)
def to_nexus(study : mx.Study, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    for papp in study.study:
        print(papp.uuid)
        papp.to_nexus(nx_root);
    return nx_root

@add_ambitmodel_method(mx.SubstanceRecord)
def to_nexus(substance : mx.SubstanceRecord, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    if not (substance.study is None):
        for papp in substance.study:
            papp.to_nexus(nx_root);
    return nx_root

@add_ambitmodel_method(mx.Substances)
def to_nexus(substances : mx.Substances, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    for substance in substances.substance:
        substance.to_nexus(nx_root);
    return nx_root

import math

def format_name(name):
    return name if isinstance(name,str) else "" if math.isnan(name) else name

def nexus_data(selected_columns,group,group_df):
        meta_dict = dict(zip(selected_columns, group))
        #print(group)
        tmp = group_df.dropna(axis=1,how="all")
        ds_conc = []
        ds_response = None
        ds_time = None
        for c in ["CONCENTRATION","CONCENTRATION_loValue","CONCENTRATION_SURFACE_loValue"]:
            if c in tmp.columns:
                tmp = tmp.sort_values(by=[c])
                c_tag = c
                c_unittag = "{}_unit".format(c_tag.replace("_loValue",""))
                c_unit = meta_dict[c_unittag] if c_unittag in tmp.columns else ""
                ds_conc.append(nx.tree.NXfield(tmp[c].values, name=c_tag, units=c_unit))

        if "loValue" in tmp:
            unit = meta_dict["unit"] if "unit" in meta_dict else ""
            ds_response = nx.tree.NXfield(tmp["loValue"].values, name=meta_dict["endpoint"], units=unit)

        for t in ["E.EXPOSURE_TIME"]:
            tag_value = "{}_loValue".format(t)
            tag_unit = "{}_unit".format(t)
            if tag_value in tmp.columns:
                unit = meta_dict[tag_unit] if tag_unit in meta_dict else ""
                ds_time = nx.tree.NXfield(tmp[tag_value].values, name=meta_dict[tag_value], units=unit)
        return nx.tree.NXdata(ds_response, ds_conc ),meta_dict

def process_pa(pa: mx.ProtocolApplication,entry = nx.tree.NXentry()):
    df_samples, df_controls = papp2df(pa, _col="CONCENTRATION",drop_parsed_cols=True)
    grouped_dataframes, selected_columns = group_samplesdf(df_samples, cols_unique = None)

    index = 1
    for group, group_df in grouped_dataframes:
        nxdata,meta_dict = nexus_data(selected_columns,group,group_df)
        print(meta_dict)
        endpointtype = meta_dict["endpointtype"] if "endpointtype" in meta_dict else "DEFAULT"
        replicates = "{} {}".format(
                    format_name(meta_dict["EXPERIMENT"] if "EXPERIMENT" in meta_dict else "DEFAULT"),
                    format_name(meta_dict["REPLICATE"] if "REPLICATE" in meta_dict else "DEFAULT"))
        if replicates.strip() == "":
            replicates="DEFAULT"
        endpointtype_group = getattr(entry, endpointtype, None)
        if endpointtype_group is None:
            endpointtype_group = nx.tree.NXgroup()
            entry[endpointtype] = endpointtype_group
        replicates_group = getattr(endpointtype_group, replicates, None)
        if replicates_group is None:
            replicates_group = nx.tree.NXsubentry()
            endpointtype_group[replicates] = replicates_group
        nxdata.name = ""
        entryid = "data_{}".format(index)
        replicates_group[entryid] = nxdata

        index = index + 1
    return entry


def effects2df(effects,drop_parsed_cols=True):
    # Convert the list of EffectRecord objects to a list of dictionaries
    effect_records_dicts = [er.dict() for er in effects]
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(effect_records_dicts)
    _tag= "conditions"
    conditions_df = pd.DataFrame(df[_tag].tolist())
    # Drop the original 'conditions' column from the main DataFrame
    if drop_parsed_cols:
        df.drop(columns=[_tag], inplace=True)
    _tag= "result"
    result_df = pd.DataFrame(df[_tag].tolist())
    if drop_parsed_cols:
        df.drop(columns=[_tag], inplace=True)
    # Concatenate the main DataFrame and the result and conditions DataFrame
    return (pd.concat([df, result_df, conditions_df], axis=1),df.columns, result_df.columns, conditions_df.columns)


def papp_mash(df, dfcols, condcols, drop_parsed_cols=True):
    for _col in condcols:
        df_normalized = pd.json_normalize(df[_col])
        df_normalized = df_normalized.add_prefix(df[_col].name + '_')
        #print(_col,df.shape,df_normalized.shape)
        for col in df_normalized.columns:
            df.loc[:, col] = df_normalized[col]
        #if there are non dict values, leave the column, otherwise drop it, we have the values parsed
        if drop_parsed_cols and df[_col].apply(lambda x: isinstance(x, dict)).all():
            df.drop(columns=[_col], inplace=True)
        #print(_col,df.shape,df_normalized.shape,df_c.shape)
        #break
    df.dropna(axis=1,how="all",inplace=True)
    #df.dropna(axis=0,how="all",inplace=True)
    return df

# from  pynanomapper.datamodel.measurements import ProtocolApplication
# pa = ProtocolApplication(**json_data)
# from pynanomapper.datamodel import measurements2nexus as m2n
# df_samples, df_controls = m2n.papp2df(pa, _col="CONCENTRATION")
def papp2df(pa: mx.ProtocolApplication, _col="CONCENTRATION",drop_parsed_cols=True):
    df, dfcols,resultcols, condcols = effects2df(pa.effects,drop_parsed_cols)
    if _col in df.columns:
        df_samples = df.loc[df[_col].apply(lambda x: isinstance(x, dict))]
        df_controls = df.loc[df[_col].apply(lambda x: isinstance(x, str))]
    else:
        df_samples = df
        df_controls = None
    #df_string.dropna(axis=1,how="all",inplace=True)
    df_samples = papp_mash(df_samples.reset_index(drop=True), dfcols, condcols,drop_parsed_cols)
    if not (df_controls is None):
        cols_to_process = [col for col in condcols if col !=_col]
        df_controls = papp_mash(df_controls.reset_index(drop=True), dfcols, cols_to_process,drop_parsed_cols)
    return df_samples,df_controls

import re
#
# def cb(selected_columns,group,group_df):
#    display(group_df)
# grouped_dataframes = m2n.group_samplesdf(df_samples,callback=cb)
def group_samplesdf(df_samples, cols_unique=None,callback=None,_pattern = r'CONCENTRATION_.*loValue$'):
    if cols_unique is None:
        selected_columns = [col for col in df_samples.columns if col not in ["loValue","errQualifier"] and not bool(re.match(_pattern, col))]
    else:
        selected_columns = [col for col in cols_unique if col in df_samples.columns]
    #dropna is to include missing values
    grouped_dataframes = df_samples.groupby(selected_columns,dropna=False)
    if callback != None:
        for group, group_df in grouped_dataframes:
            callback(selected_columns,group,group_df)
    return grouped_dataframes,selected_columns
