import h5py
import numpy as np
import json
import traceback
import pandas as pd

class AmbitParser:

    _cols = [ "unit", "loQualifier","loValue", "upQualifier","upValue","errQualifier","err","textValue"]
    _cols_param = [ "unit", "loValue"]

    @staticmethod
    def split_results(row,cols,indexcols=None):
        if indexcols is None:
            indexcols=cols
        r = []
        for col in cols:
            if row is None or pd.isna(row) or row=="":
                r.append(pd.NA)
                continue
            if isinstance(row,str):
                if col=="loValue":
                    r.append(row)
                else:
                    r.append(pd.NA)
            else:
                try:
                    if col in row:
                        if row[col] == "":
                            r.append(pd.NA)
                        else:
                            r.append(row[col])
                    else:
                        r.append(pd.NA)
                except Exception as err:
                    r.append(str(err))
        #print(r,indexcols)
        return pd.Series(r, index=indexcols)

    @staticmethod
    def write_attributes(h5file, h5path, ambitobj, props=['ownerName', "substanceType", "name", "publicname"]):
        for a in props:
            try:
                h5file.require_group(h5path)
                try:
                    h5file[h5path].attrs[a] = ambitobj[a]
                except Exception as err:
                    # print(a,err)
                    h5file[h5path].attrs[a] = str(ambitobj[a])
            except Exception as err:
                print(err, h5path, ambitobj, props)

    @staticmethod
    def parse_attribute_value(attr_value):
        if isinstance(attr_value, np.ndarray):
            return attr_value.tolist()
        elif attr_value.startswith("{"):
            try:
                return json.loads(attr_value.replace("'","\""))
            except:
                return str(attr_value)
        else:
            return attr_value

    @staticmethod
    def read_attributes(h5file, h5path, ambitobj, props=['ownerName', "substanceType", "name", "publicname"]):
        for a in props:
            try:
                ambitobj[a] = AmbitParser.parse_attribute_value(h5file[h5path].attrs[a])
            except Exception as err:
                print(err, h5path, ambitobj, props)




    @staticmethod
    def effects2df(study_effects, conditions = ["concentration","E.exposure_time","Material","replicate","Replicate","Technical replicate","Biological replicate"]):
        df = pd.DataFrame(study_effects)
        cols = AmbitParser._cols
        cols_param = AmbitParser._cols_param
        df[cols] = df["result"].apply(AmbitParser.split_results,cols=cols)
        df.drop(columns=["result"],inplace=True)
        prefix="c_"
        c_cols = list(map(lambda x : prefix+x,conditions))

        df[c_cols] = df["conditions"].apply(AmbitParser.split_results,cols=conditions)
        for c in c_cols:
            prefix= c
            v_cols = list(map(lambda x : prefix+("" if x=="loValue" else ("_"+x)),cols_param))
            try:
                df[v_cols] = df[c].apply(AmbitParser.split_results,cols=cols_param,indexcols=v_cols)
            except Exception as err:
                print(traceback.format_exc())
        for c in df.columns:
            if c.find("replicate")>=0:
                cc = c.replace("c_","")
                df[c] = df[c].apply(lambda x : pd.NA if pd.isna(x) else x.replace(cc,""))
        df.drop(columns=["conditions"],axis=1,inplace=True)
        df = df[df['loValue'].notna() | df['textValue'].notna()]
        df.dropna(axis=1,how="all",inplace=True)

        return df

    @staticmethod
    def make_dataset(df):
        df.fillna("",inplace=True)
        gcols = list(df.columns.values)
        values = ["loValue","upValue","textValue"]
        for v in values:
            if v in df.columns:
                gcols.remove(v)

        endpoints = ["endpoint",'endpointtype', 'unit']
        for e in endpoints:
            gcols.remove(e)
        gcols.sort()
        tmp = df.pivot_table(columns=endpoints,values=["loValue"],index=gcols,dropna=False).reset_index()
        tmp.dropna(axis=1,how="all",inplace=True)
        tmp.columns = tmp.columns.map('_'.join)
        nonempty = False
        value_cols = [c for c in tmp if c.startswith('loValue')]
        for c in value_cols:
            nonempty = nonempty | tmp[c].notna()
        return tmp.loc[nonempty]


    @staticmethod
    def hdf52ambit(h5file):
        substances = {}
        for _uuid in h5file["substance"]:
            substance = {}
            substance['i5uuid'] = _uuid
            substance['study'] = []
            AmbitParser.read_attributes(h5file, "/substance/{}".format(_uuid), substance,
                        props=["ownerName", "substanceType", "name", "publicname"])
            substances[_uuid] = substance

        for _uuid in h5file["study"]:
            study = { "owner" : { "substance" : {} , "company" : {}}, "citation" : {}, "protocol" : { "category": {}} , "parameters" : [], "effects" : []}
            study['uuid'] = _uuid
            h5path = "/study/{}".format(study['uuid'])
            AmbitParser.read_attributes(h5file, "{}/owner/substance".format(h5path), study['owner']['substance'], props=['uuid'])
            substances[study['owner']['substance']["uuid"]]["study"].append(study)
            AmbitParser.read_attributes(h5file, h5path, study, props=['investigation_uuid', "assay_uuid"])
            AmbitParser.read_attributes(h5file, "{}/owner/company".format(h5path), study['owner']['company'], props=['uuid', 'name'])

            AmbitParser.read_attributes(h5file, "{}/citation".format(h5path), study['citation'], props=['title', 'year', 'owner'])
            AmbitParser.read_attributes(h5file, "{}/protocol".format(h5path), study['protocol'], props=['topcategory', 'endpoint','guideline'])
            AmbitParser.read_attributes(h5file, "{}/protocol".format(h5path), study['protocol']['category'], props=['code', 'title', 'term'])
            params = h5file["{}/parameters".format(h5path)].attrs
            for attr in params:
                param = {}
                param[attr] = AmbitParser.parse_attribute_value(params[attr])
                study['parameters'].append(param)
            results = h5file["{}/results".format(h5path)]
            effects = []
            for endpointtype in results:
                for key in results[endpointtype]:
                    effect = {"endpoint" : "","unit" : "","conditions" : []}
                    effect["endpointtype"] = endpointtype
                    dataset = results[endpointtype][key]
                    for attr in dataset.attrs:
                        value = dataset.attrs[attr]
                        if "endpoint" == attr:
                            effect[attr] = value
                        elif "endpoint.unit" == attr:
                            effect[attr] = value
                        else:

                            effect["conditions"].append({attr : AmbitParser.parse_attribute_value(value)});
                    study["effects"].append(effect)


        datamodel = {"substance" : [] }
        for _uuid in substances:
            datamodel["substance"].append(substances[_uuid])
        return datamodel


    @staticmethod
    def ambit2hdf5(datamodel, h5file):
        for substance in datamodel['substance']:

            # print(substance['ownerName'], substance["substanceType"], substance["name"], substance["publicname"])
            AmbitParser.write_attributes(h5file, "/substance/{}".format(
                        substance['i5uuid']), substance,
                        props=["ownerName", "substanceType", "name", "publicname"])
            results = {}
            for study in substance['study']:
                AmbitParser.write_attributes(h5file, "/study/{}".format(study['uuid']), study, props=['investigation_uuid', "assay_uuid"])
                AmbitParser.write_attributes(h5file, "/study/{}/owner/substance".format(study['uuid']), study['owner']['substance'], props=['uuid'])
                AmbitParser.write_attributes(h5file, "/study/{}/owner/company".format(study['uuid']), study['owner']['company'], props=['uuid', 'name'])
                AmbitParser.write_attributes(h5file, "/study/{}/citation".format(study['uuid']), study['citation'], props=['title', 'year', 'owner'])
                AmbitParser.write_attributes(h5file, "/study/{}/protocol".format(study['uuid']), study['protocol'], props=['topcategory', 'endpoint','guideline'])
                AmbitParser.write_attributes(h5file, "/study/{}/protocol".format(study['uuid']), study['protocol']['category'], props=['code', 'title', 'term'])
                for param in study['parameters']:
                    AmbitParser.write_attributes(h5file, "/study/{}/parameters".format(study['uuid']), study['parameters'], props= [ param])



                # print(study['reliability'])
                dt_effects = np.dtype([("endpoint", np.float), ("concentration", np.float), ("time", np.integer)])
                for effect in study['effects']:
                    AmbitParser.effects2df(study['effects'], conditions = ["concentration","E.exposure_time","Material","Replicate","Technical replicate","Biological replicate"])
                    if "unit" in effect:
                        _unit = effect["unit"]
                    else:
                        _unit = "None"
                    try:
                        if "concentration" in effect["conditions"]:
                            if "unit" in effect["conditions"]["concentration"]:
                                concentration_unit = str(effect["conditions"]["concentration"]["unit"])
                                control = None
                            else:
                                control = effect["conditions"]["concentration"]
                                concentration_unit = "None"
                    except Exception as err:
                        # no concentration
                        concentration_unit = "None"
                        control = None
                        pass

                    _tag = "/study/{}/results/{}".format(study['uuid'],effect["endpointtype"])
                    _tag_endpoint = "{}/{}({})".format(_tag, effect["endpoint"],_unit)
                    if not (_tag_endpoint in results):
                        results[_tag_endpoint] = {"dataset": np.array([], dtype=dt_effects), "properties": {}}
                    # print(_tag_endpoint,_tmp)
                    try:
                        _tmp = results[_tag_endpoint]["dataset"]
                        results[_tag_endpoint]["properties"] = {
                                    "endpoint": effect["endpoint"],
                                    "endpoint.unit": _unit, "concentration.unit": concentration_unit}
                        # results[_tag_endpoint]["properties"]["unit"] = _unit

                        try:
                            results[_tag_endpoint]["properties"]["E.exposure_time"] = str(effect["conditions"]["E.exposure_time"])
                        except Exception as err:
                            pass
                            # print("!!!",err,effect["conditions"]["E.exposure_time"])
                        results[_tag_endpoint]["dataset"]=  np.append(_tmp,
                            np.array([(effect["result"]["loValue"],
                                    effect["conditions"]["concentration"]["loValue"],
                                    int(effect["conditions"]["E.exposure_time"]["loValue"])
                                    )], dtype=dt_effects))

                        # print(effect["endpoint"]["loValue"],effect["conditions"]["concentration"]["loValue"])
                    except Exception as err:
                        # print(err)
                        pass
                    #
                    # print(effect["endpoint"])
                    # print(effect["endpointtype"])
                    # for condition in effect["conditions"]:
                    #    print(condition,effect["conditions"][condition])
                    #  print(">>result")
                    # for result in effect["result"]:
                        #print(result,effect["result"][result])
            #print(results)
            for _tag in results:
                result_dataset = h5file.require_dataset(_tag, data=results[_tag]["dataset"], shape=(len(results[_tag]["dataset"]), ), dtype=dt_effects)
                for prop in results[_tag]["properties"]:
                    result_dataset.attrs[prop] = results[_tag]["properties"][prop]
