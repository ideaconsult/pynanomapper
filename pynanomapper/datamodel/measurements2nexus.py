import nexusformat
from . import measurements
import pandas as pd
import numpy as np

#https://github.com/nexusformat/definitions/issues/807
#

import pandas as pd
import nexusformat.nexus.tree as nx

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
def papp2df(pa, _col="CONCENTRATION",drop_parsed_cols=True):
    df, dfcols,resultcols, condcols = effects2df(pa.effects,drop_parsed_cols)
    df_samples = df.loc[df[_col].apply(lambda x: isinstance(x, dict))]
    df_controls = df.loc[df[_col].apply(lambda x: isinstance(x, str))]
    #df_string.dropna(axis=1,how="all",inplace=True)
    df_samples = papp_mash(df_samples.reset_index(drop=True), dfcols, condcols,drop_parsed_cols)
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

def cb_example(selected_columns,group,group_df):
    x = None
    tmp = group_df.dropna(axis=1,how="all")
    if "CONCENTRATION_loValue" in tmp.columns:
        tmp = tmp.sort_values(by=["CONCENTRATION_loValue"])
        x = tmp["CONCENTRATION_loValue"].values
    elif "CONCENTRATION" in tmp.columns:
        tmp = tmp.sort_values(by=["CONCENTRATION"])
        x = tmp["CONCENTRATION"].values
    y = tmp["loValue"].values
    print(x,y)
    if "E.EXPOSURE_TIME_loValue" in tmp.columns:
        t = tmp["E.EXPOSURE_TIME_loValue"].values
        print(t)



def cb(selected_columns,group,group_df):
    meta_dict = dict(zip(selected_columns, group))
    print(meta_dict)
    tmp = group_df.dropna(axis=1,how="all")
    ds_conc= None
    ds_response = None
    ds_time = None
    for c in ["CONCENTRATION","CONCENTRATION_loValue"]:
        if c in tmp.columns:
            tmp = tmp.sort_values(by=[c])
            c_tag = c
            c_unittag = "{}_unit".format(c_tag)
            c_unit = meta_dict[c_unittag] if c_unittag in tmp.columns else ""
            ds_conc = nx.NXfield(tmp[c].values, name=c_tag, units=c_unit)

    if "loValue" in tmp:
        unit = meta_dict["unit"] if "unit" in meta_dict else ""
        ds_response = nx.NXfield(tmp["loValue"].values, name=meta_dict["endpoint"], units=unit)

    for t in ["E.EXPOSURE_TIME"]:
        tag_value = "{}_loValue".format(t)
        tag_unit = "{}_unit".format(t)
        if tag_value in tmp.columns:
            unit = meta_dict[tag_unit] if tag_unit in meta_dict else ""
            ds_time = nx.NXfield(tmp[tag_value].values, name=meta_dict[tag_value], units=unit)
    print(ds_conc,ds_response,ds_time)


import nexusformat.nexus as nx
import re

class Study2Nexus:

    def __init__(self):
        self._root = nx.NXroot()

    def save(self,filename="test.nxs",mode='w'):
        self._root.save(filename,mode=mode)

    def nexus_data(self,selected_columns,group,group_df):
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

        #print(ds_conc,ds_response,ds_time)

    def process_pa(self,pa: measurements.ProtocolApplication):
        entry = nx.tree.NXentry()

        entry.name = ""
        df_samples, df_controls = m2n.papp2df(pa, _col="CONCENTRATION",drop_parsed_cols=True)
        grouped_dataframes, selected_columns = m2n.group_samplesdf(df_samples, cols_unique = None,
        # callback=m2n.cb_example
        )

        index = 1
        for group, group_df in grouped_dataframes:
            nxdata,meta_dict = self.nexus_data(selected_columns,group,group_df)
            nxdata.name = ""
            entryid = "data_{}".format(index)
            entry["data_{}".format(index)] = nxdata

            index = index + 1
        #grouped_dataframes = m2n.group_samplesdf(df_controls, callback=cb)
        return entry

    def process(self,pa: measurements.ProtocolApplication):
        self._root['entry'] = self.process_pa(pa)
        self._root['entry/title'] = 'Example NeXus Data (nexusformat)'
        self._root['entry/sample'] = nx.tree.NXsample()
        self._root['entry/sample/temperature'] = nx.tree.NXfield(40.0, units='K')
        self._root['entry/sample/mass'] = nx.tree.NXfield(10.0, units='g')
        self._root['instrument'] = nx.tree.NXinstrument()
        self._root['instrument/energy'] = nx.tree.NXfield(87.1, units='keV')


#s2n = Study2Nexus()
#s2n.process(pa)
#s2n.save('test_ambit.nxs',mode='w')
