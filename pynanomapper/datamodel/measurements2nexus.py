import nexusformat
from . import measurements
import pandas as pd
import numpy as np

#https://github.com/nexusformat/definitions/issues/807
#

import pandas as pd

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
        if drop_parsed_cols:
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
    df, dfcols,resultcols, condcols = effects2df(pa.effects)
    df_samples = df.loc[df[_col].apply(lambda x: isinstance(x, dict))]
    df_controls = df.loc[df[_col].apply(lambda x: isinstance(x, str))]
    #df_string.dropna(axis=1,how="all",inplace=True)
    df_samples = papp_mash(df_samples.reset_index(drop=True), dfcols, condcols,drop_parsed_cols)
    cols_to_process = [col for col in condcols if col !=_col]
    df_controls = papp_mash(df_controls.reset_index(drop=True), dfcols, cols_to_process,drop_parsed_cols)
    return df_samples,df_controls


