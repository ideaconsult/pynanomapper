import numpy as np
from pydantic import validate_arguments

from . import measurements as mx
from . ambit_deco import add_ambitmodel_method
import nexusformat.nexus as nx
import pandas as pd
import re
import traceback
import numbers

"""
    ProtocolApplication to nexus entry (NXentry)

    Args:
        papp (ProtocolApplication): The object to be written into nexus format.
        nx_root (nx.NXroot()): Nexus root (or None).

    Returns:
        nx_root: Nexus root

    Raises:
        Exception: on parse

    Examples:
        from  pynanomapper.datamodel.nexus_utils import to_nexus
        from  pynanomapper.datamodel.measurements import ProtocolApplication
        pa = ProtocolApplication(**json_data)
        import nexusformat.nexus.tree as nx
        ne = pa.to_nexus(nx.NXroot())
        print(ne.tree)
"""
@add_ambitmodel_method(mx.ProtocolApplication)
def to_nexus(papp : mx.ProtocolApplication, nx_root: nx.NXroot() = None ) :
    if nx_root == None:
        nx_root = nx.NXroot()

    #https://manual.nexusformat.org/classes/base_classes/NXentry.html
    try:
        if not papp.protocol.topcategory in nx_root:
            nx_root[papp.protocol.topcategory] = nx.NXgroup()
        if not papp.protocol.category.code in nx_root[papp.protocol.topcategory]:
            nx_root[papp.protocol.topcategory][papp.protocol.category.code] = nx.NXgroup()
        provider = "" if papp.citation.owner is None else papp.citation.owner.replace("/","_").upper()
        entry_id = "{}/{}/entry_{}_{}".format(papp.protocol.topcategory,papp.protocol.category.code,provider,papp.uuid)
    except Exception as err:
        #print(err,papp.citation.owner)
        entry_id = "entry_{}".format(papp.uuid)

    nxentry = nx.tree.NXentry()
    nx_root[entry_id] = nxentry

    nx_root['{}/entry_identifier_uuid'.format(entry_id)] = papp.uuid

    nx_root['{}/definition'.format(entry_id)] = papp.__class__.__name__
    nxmap = nx_root['{}/definition'.format(entry_id)]
    nxmap.attrs["PROTOCOL_APPLICATION_UUID"]="entry_identifier_uuid"
    nxmap.attrs["INVESTIGATION_UUID"]="collection_identifier"
    nxmap.attrs["ASSAY_UUID"]="experiment_identifier"
    nxmap.attrs["Protocol"]= "experiment_documentation"
    nxmap.attrs["Citation"]= "reference"
    nxmap.attrs["Substance"]= "sample"
    nxmap.attrs["Parameters"]= ["instrument","environment","parameters"]
    nxmap.attrs["EffectRecords"] = "datasets"
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

    try:
        if not (papp.protocol is None):
            experiment_documentation = nx.NXnote()
            nx_root['{}/experiment_documentation'.format(entry_id)] = experiment_documentation
            experiment_documentation["date"] = papp.updated
            #category = nx.NXgroup()
            #experiment_documentation["category"] = category
            experiment_documentation.attrs["topcategory"] = papp.protocol.topcategory
            experiment_documentation.attrs["code"] = papp.protocol.category.code
            experiment_documentation.attrs["term"] = papp.protocol.category.term
            experiment_documentation.attrs["title"] = papp.protocol.category.title
            experiment_documentation.attrs["endpoint"] = papp.protocol.endpoint
            experiment_documentation.attrs["guideline"] = papp.protocol.guideline
            for tag in ["E.method","ASSAY"]:
                if tag in papp.parameters:
                    experiment_documentation.attrs["method"]  = papp.parameters[tag]

    except Exception as err:
        raise Exception("ProtocolApplication: protocol parsing error " + str(err)) from err

    try:
        citation_id = '{}/reference'.format(entry_id)
        nx_root[citation_id] = nx.NXcite()
        if papp.citation != None:
            nx_root[citation_id]["title"] = papp.citation.title
            nx_root[citation_id]["year"] = papp.citation.year
            nx_root[citation_id].attrs["owner"] = papp.citation.owner
            doi = extract_doi(papp.citation.title)
            if not doi is None:
                nx_root[citation_id]["doi"] = doi
            if papp.citation.title.startswith("http"):
                nx_root[citation_id]["url"] = papp.citation.title

        #url, doi, description
    except Exception as err:
        raise Exception("ProtocolApplication: citation data parsing error " + str(err)) from err

    instrument = nx.NXinstrument()
    parameters = nx.NXcollection()
    environment = nx.NXenvironment()

    if not "substance" in nx_root:
        nx_root["substance"] = nx.NXgroup()
    substance_id = 'substance/{}'.format(papp.owner.substance.uuid)
    if not substance_id in nx_root:
        nx_root[substance_id] = nx.NXsample()
    #now the actual sample
    sample = nx.NXsample()
    nx_root['{}/sample'.format(entry_id)] = sample
    nx_root['{}/sample/substance'.format(entry_id)] = nx.NXlink(substance_id)

    #parameters
    nx_root['{}/instrument'.format(entry_id)] = instrument
    nx_root['{}/parameters'.format(entry_id)] = parameters
    nx_root['{}/environment'.format(entry_id)] = environment

    if not (papp.parameters is None):
        for prm in papp.parameters:
            try:
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
            except Exception as err:
                raise Exception("ProtocolApplication: parameters parsing error " + str(err)) from err

    if not (papp.owner is None):
        try:
            sample["uuid"] = papp.owner.substance.uuid
            sample["provider"] = papp.owner.company.name
        except Exception as err:
            raise Exception("ProtocolApplication owner (sample) parsing error " + str(err)) from err

    try:
        process_pa(papp,nx_root[entry_id])
    except Exception as err:
        raise Exception("ProtocolApplication: effectrecords parsing error " + str(err)) from err

    return nx_root


@add_ambitmodel_method(mx.Study)
def to_nexus(study : mx.Study, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    x = 1
    for papp in study.study:

        papp.to_nexus(nx_root);
        #x = x+1
        #if x>22:
        #    print(papp.uuid)
        #    papp.to_nexus(nx_root)
        #    break
    return nx_root

"""
    SubstanceRecord to nexus entry (NXentry)

    Args:
        substance record (SubstanceRecord): The object to be written.
        nx_root (nx.NXroot()): Nexus root (or None).

    Returns:
        nx_root: Nexus root

    Raises:
        Exception: on parse

    Examples:
        import  pynanomapper.datamodel.measurements as m2n
        from pynanomapper.datamodel.nexus_utils import to_nexus
        import nexusformat.nexus.tree as nx
        import traceback

        nxroot = nx.NXroot()
        substances = m2n.Substances(**pjson)
        for substance in substances.substance:
            print(type(substance))
            url = "{}/study?media=application/json".format(substance.URI)
            response = requests.get(url)
            sjson = response.json()
        substance.study = m2n.Study(**sjson).study
        try:
            ne = substance.to_nexus(nxroot)
        except Exception as err:
            print(substance.URI)
            print(err)
        nxroot.save("example.nxs",mode="w")
"""
@add_ambitmodel_method(mx.SubstanceRecord)
def to_nexus(substance : mx.SubstanceRecord, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()

    if not (substance.study is None):
        for papp in substance.study:
            papp.to_nexus(nx_root);

    if not "substance" in nx_root:
        nx_root["substance"] = nx.NXgroup()
    substance_id = 'substance/{}'.format(substance.i5uuid)
    if not substance_id in nx_root:
        nx_root[substance_id] = nx.NXsample()
    print(substance.name)
    nx_root[substance_id].attrs["uuid"] = substance.i5uuid
    nx_root[substance_id].name = substance.name
    nx_root[substance_id].attrs["publicname"] = substance.publicname
    nx_root[substance_id].attrs["substanceType"] = substance.substanceType
    nx_root[substance_id].attrs["ownerName"] = substance.ownerName
    nx_root[substance_id].attrs["ownerUUID"] = substance.ownerUUID
    return nx_root

@add_ambitmodel_method(mx.Substances)
def to_nexus(substances : mx.Substances, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    for substance in substances.substance:
        substance.to_nexus(nx_root);
    return nx_root

import math

def format_name(meta_dict,key, default = ""):
    name = meta_dict[key] if key in meta_dict else default
    return name if isinstance(name,str) else default if math.isnan(name) else name

def nexus_data(selected_columns,group,group_df,condcols,debug=False):
    try:
        meta_dict = dict(zip(selected_columns, group))
        #print(group_df.columns)
        tmp = group_df.dropna(axis=1,how="all")
        if debug:
            display(tmp)

        ds_conc = []
        ds_conditions = []
        ds_response = None
        ds_aux = []
        ds_aux_tags = []
        ds_errors = None

        #for c in ["CONCENTRATION","CONCENTRATION_loValue","CONCENTRATION_SURFACE_loValue","CONCENTRATION_MASS_loValue"]:
        #    if c in tmp.columns:
        #        tmp = tmp.sort_values(by=[c])
        #        c_tag = c
        #        c_unittag = "{}_unit".format(c_tag.replace("_loValue",""))
        #        c_unit = meta_dict[c_unittag] if c_unittag in tmp.columns else ""
        #        ds_conc.append(nx.tree.NXfield(tmp[c].values, name=c_tag, units=c_unit))


        if "loValue" in tmp:
            unit = meta_dict["unit"] if "unit" in meta_dict else ""
            ds_response = nx.tree.NXfield(tmp["loValue"].values, name=meta_dict["endpoint"], units=unit)

        if "upValue" in tmp:
            unit = meta_dict["unit"] if "unit" in meta_dict else ""
            name = "{}_upValue".format(meta_dict["endpoint"])
            ds_aux.append(nx.tree.NXfield(tmp["upValue"].values, name= name, units= unit))
            ds_aux_tags.append(name)

        if "errorValue" in tmp:
            unit = meta_dict["unit"] if "unit" in meta_dict else ""
            ds_errors = nx.tree.NXfield(tmp["errorValue"].values, name="{}_errors".format(meta_dict["endpoint"]), units=unit)

        for tag in ["loQualifier","upQualifier","textValue","errQualifier"]:
            if tag in tmp:
                vals = tmp[tag].unique()
                if len(vals)==1 and (vals[0]=="" or vals[0]=="="):
                    #skip if all qualifiers are empty or '=' tbd also for nans
                    continue
                str_array = np.array(['='.encode('ascii', errors='ignore') if (x is None) else x.encode('ascii', errors='ignore') for x in tmp[tag].values])
                #nxdata.attrs[tag] =str_array
                #print(str_array.dtype,str_array)
                ds_aux.append(nx.tree.NXfield(str_array, name= tag))
                ds_aux_tags.append(tag)

        primary_axis = None
        for tag in condcols:
            if tag in tmp.columns:
                if tag in ["REPLICATE","BIOLOGICAL_REPLICATE","TECHNICAL_REPLICATE","EXPERIMENT"]:
                    unit = None
                    int_array = np.array([int(x) if isinstance(x,str) and x.isdigit() else np.nan if (x is None) or math.isnan(x) or (not isinstance(x, numbers.Number)) else int(x) for x in tmp[tag].values])
                    #ds_aux.append(nx.tree.NXfield(int_array, name= tag))
                    #ds_aux_tags.append(tag)
                    ds_conditions.append(nx.tree.NXfield(int_array, name= tag))
                else:
                    try:
                        str_array = np.array(['='.encode('ascii', errors='ignore') if (x is None) else x.encode('ascii', errors='ignore') for x in tmp[tag].values])
                        #add as axis
                        ds_conditions.append(nx.tree.NXfield(str_array, name= tag))
                        #ds_aux.append(nx.tree.NXfield(str_array, name= tag))
                        #ds_aux_tags.append(tag)
                    except Exception as err_condition:
                        print(err_condition,tag,tmp[tag].values)
            else:
                tag_value = "{}_loValue".format(tag)
                tag_unit = "{}_unit".format(tag)
                if tag_value in tmp.columns:
                    unit = tmp[tag_unit].unique()[0] if tag_unit in tmp.columns else None
                    axis = nx.tree.NXfield(tmp[tag_value].values, name=tag, units=unit)
                    ds_conc.append(axis)
                    if tag == "CONCENTRATION":
                        primary_axis = tag

        ds_conc.extend(ds_conditions)

        nxdata = nx.tree.NXdata(ds_response, ds_conc, errors=ds_errors)
        nxdata.name = meta_dict["endpoint"]
        nxdata.attrs["endpoint"] = meta_dict["endpoint"]
        if not primary_axis is None:
            nxdata.attrs["{}_indices".format(primary_axis)] = 0
        if "endpointtype" in meta_dict:
            nxdata.attrs["endpointtype"] = meta_dict["endpointtype"]
        if "unit" in meta_dict and not (meta_dict["unit"] is None):
            nxdata.attrs["unit"] = meta_dict["unit"]


        if len(ds_aux) > 0:
            for index, a in enumerate(ds_aux_tags):
                nxdata[a] = ds_aux[index]
            nxdata.attrs["auxiliary_signals"] = ds_aux_tags
        if debug:
            print(nxdata.tree)
        return nxdata,meta_dict
    except Exception as err:
        raise Exception("EffectRecords: grouping error {} {} {}".format(selected_columns,group,err)) from err

def process_pa(pa: mx.ProtocolApplication,entry = nx.tree.NXentry()):
    df_samples,df_controls,resultcols, condcols = papp2df(pa, _col="CONCENTRATION",drop_parsed_cols=True)

    index = 1
    df_titles = ["data","controls"]
    for num,df in enumerate([df_samples,df_controls]):
        if df is None:
            continue
        grouped_dataframes, selected_columns = group_samplesdf(df, cols_unique = None)
        try:
            for group, group_df in grouped_dataframes:
                try:
                    #print(group_df.info())
                    nxdata,meta_dict = nexus_data(selected_columns,group,group_df,condcols)
                    try:
                        method = entry["experiment_documentation"].attrs["method"]
                    except:
                        method = ""
                    nxdata.title = "{} ({} by {})".format(meta_dict["endpoint"],method,pa.citation.owner)
                    #print(meta_dict)

                    endpointtype = format_name(meta_dict,"endpointtype","DEFAULT")

                    endpointtype_group = getattr(entry, endpointtype, None)
                    if endpointtype_group is None:
                        endpointtype_group = nx.tree.NXgroup()
                        endpointtype_group.name = "endpointtype"
                        endpointtype_group.attrs["endpointtype"] = endpointtype
                        entry[endpointtype] = endpointtype_group
                    nxdata.name = df_titles[num]
                    entryid = "{}_{}_{}".format(df_titles[num],index,meta_dict["endpoint"])
                    endpointtype_group[entryid] = nxdata
                    index = index + 1

                except Exception as xx:
                    print(traceback.format_exc().print_exc())
        except Exception as err:
            raise Exception("ProtocolApplication: data parsing error {} {}".format(selected_columns,err)) from err

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
    return df_samples,df_controls,resultcols, condcols


#
# def cb(selected_columns,group,group_df):
#    display(group_df)
# grouped_dataframes = m2n.group_samplesdf(df_samples,callback=cb)
def group_samplesdf(df_samples, cols_unique=None,callback=None,_pattern = r'CONCENTRATION_.*loValue$'):
    if cols_unique is None:
        _pattern_c_unit = r'^CONCENTRATION.*_unit$'
        #selected_columns = [col for col in df_samples.columns if col not in ["loValue","upValue","loQualifier","upQualifier","errQualifier","errorValue","textValue","REPLICATE","EXPERIMENT"] and not bool(re.match(_pattern, col))]

        selected_columns = [col for col in df_samples.columns if col in ["endpoint","endpointtype","unit"] or bool(re.match(_pattern_c_unit, col))]

    else:
        selected_columns = [col for col in cols_unique if col in df_samples.columns]
    #dropna is to include missing values
    try:
        grouped_dataframes = df_samples.groupby(selected_columns,dropna=False)
    except Exception as err:
        raise Exception("group_samplesdf: {} {}".format(selected_columns,err)) from err
    if callback != None:
        for group, group_df in grouped_dataframes:
            callback(selected_columns,group,group_df)
    return grouped_dataframes,selected_columns

def extract_doi(input_str):
    # Regular expression pattern to match DOI
    doi_pattern = r"(10\.\d{4,}(?:\.\d+)*\/\S+)"
    # Search for the DOI pattern in the input string
    match = re.search(doi_pattern, input_str)
    if match:
        return match.group(1)  # Return the matched DOI
    else:
        return None  # Return None if DOI not found
