import pandas as pd
import os
import json
from datetime import datetime
from xlsxwriter.utility import xl_col_to_name

def iom_format(df,param_name="param_name",param_group="param_group"):
    df.fillna(" ",inplace=True)
    #print(df.columns)
    # Create a new DataFrame with one column
    result_df = pd.DataFrame(columns=['param_name'])
    result_df["type"] = "group"
    result_df["position"] = -1
    # Iterate through unique groups
    for group in df[param_group].unique():
        group_df = df[df[param_group] == group]
        # Get names for the group
        names = group_df[param_name].tolist()
        # Append group and names to the result DataFrame
        tmp = pd.DataFrame({'param_name': [group] + names })
        tmp["type"] = "names"
        tmp.at[0, "type"] = "group"
        tmp['position'] = -1
        result_df = pd.concat([result_df, tmp], ignore_index=True)
    return result_df

def json2frame(json_data,sortby=None):
    tmp = pd.DataFrame(json_data)
    if sortby is None:
        return tmp
    else:
        return tmp.sort_values(by=sortby)

def get_method_metadata(json_blueprint):
    _header = {
    "Project Work Package" : json_blueprint.get("provenance_workpackage",""),
    "Partner conducting test/assay" : json_blueprint.get("provenance_workpackage",""),
    "Test facility - Laboratory name" : json_blueprint.get("provenance_provider",""),
    "Lead Scientist & contact for test" : json_blueprint.get("provenance_contact",""),
    "Assay/Test work conducted by" : json_blueprint.get("provenance_operator",""),
    "Full name of test/assay" : json_blueprint.get("METHOD",""),
    "Short name or acronym for test/assay": json_blueprint.get("METHOD",""),
    "Type or class of experimental test as used here": json_blueprint.get("PROTOCOL_CATEGORY_CODE",""),
    "End-Point being investigated/assessed by the test" : [],
    "Raw data metrics" : [],
    "SOP(s) for test" : json_blueprint.get("EXPERIMENT",""),
    "Path/link to sop/protocol": json_blueprint.get("EXPERIMENT_PROTOCOL",""),
    "Test start date": json_blueprint.get("provenance_startdate",datetime.now()),
    "Test end date": json_blueprint.get("provenance_enddate",datetime.now()),
    }
    return _header

def get_materials_metadata(json_blueprint):
    sample_group_dict = {}
    for item in json_blueprint.get("METADATA_SAMPLE_INFO"):
        group = item["param_sample_group"]
        name = item["param_sample_name"]
        sample_group_dict.setdefault(group, []).append(name)    
    _header = {
    "Select item from Project Materials list" : sample_group_dict.get("ID",["ID"])[0],
    "Material Name" : sample_group_dict.get("NAME",["NAME"])[0],
    "Core chemistry" : sample_group_dict.get("CHEMISTRY",["CHEMISTRY"])[0],
    "CAS No" : sample_group_dict.get("CASRN",["CAS_RN"])[0],
    "Material Supplier" : sample_group_dict.get("SUPPLIER",["SUPPLIER"])[0],
    "Material State" : "",
    "Batch": sample_group_dict.get("BATCH",["BATCH"])[0],
    "Date of preparation" : datetime.now()
    }
    return _header

def get_materials_columns(nanomaterial = True):
    if nanomaterial:
        return ["","ERM identifier","ID","Name","CAS","type","Supplier","Supplier code","Batch","Core","BET surface in m²/g"]
    else:
        return ["","Material identifier","ID","Name","CAS","type","Supplier","Supplier code","Batch","Core"]

def get_treatment(json_blueprint):
    tmp  = []
    condition_type = None
    for item in json_blueprint["conditions"]:
        name = "conditon_name"
        isreplicate = item["condition_type"].startswith("c_replicate")
        isconcentration = item["condition_type"].startswith("c_concentration")
        if not isreplicate:
            tmp.append({'param_name': "TREATMENT {}".format(item[name].upper()), 'type': 'group', 'position' : '0', 'position_label' : 0,'datamodel' : item['condition_type']})
        else:
            if condition_type != isreplicate:
                tmp.append({'param_name': "CONTROLS", 'type': 'group', 'position' : '0', 'position_label' : 0,'datamodel' : "c_replicate"})
                tmp.append({'param_name': "Positive controls abbreviations", 'type': 'names', 'position' : '0', 'position_label' : 0,'datamodel' : "CONTROL"})
                tmp.append({'param_name': "Positive controls description", 'type': 'names', 'position' : '0', 'position_label' : 0,'datamodel' : "CONTROL"})
                tmp.append({'param_name': "Negative controls abbreviations", 'type': 'names', 'position' : '0', 'position_label' : 0,'datamodel' : "CONTROL"})
                tmp.append({'param_name': "Negative controls description", 'type': 'names', 'position' : '0', 'position_label' : 0,'datamodel' : "CONTROL"})
                tmp.append({'param_name': "REPLICATES", 'type': 'group', 'position' : '0', 'position_label' : 0,'datamodel' : "c_replicate"})
        if "condition_unit" in item:
            tmp.append({'param_name': "{} series unit".format(item[name]), 'type': 'names', 'position' : '0', 'position_label' : 0,'datamodel' : item['condition_type']})
        if not isreplicate:
            tmp.append({'param_name': "{} series labels".format(item[name]), 'type': 'names', 'position' : '0', 'position_label' : 0,'datamodel' : item['condition_type']})
        tmp.append({'param_name': "{}".format(item[name]), 'type': 'names', 'position' : '0', 'position_label' : 0,'datamodel' : item['condition_type']})
        if isconcentration:
            tmp.append({'param_name': "Treatment type series", 'type': 'names', 'position' : '0', 'position_label' : 0,'datamodel' : "c_treatment"})
        condition_type = isreplicate
    return pd.DataFrame(tmp)

def get_nmparser_config(json_blueprint):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(current_directory, "../../resource/nmparser/DEFAULT_TABLE.json")
    config = {}
    with open(json_file_path, 'r') as json_file:
        # Load the JSON data from the file
        config = json.load(json_file)
    return config

def get_template_frame(json_blueprint):
    if "METADATA_SAMPLE_INFO" in json_blueprint:
        df_sample = pd.DataFrame(list(get_materials_metadata(json_blueprint).items()), columns=['param_name', 'param_value'])
   
        #df_sample = json2frame(json_blueprint["METADATA_SAMPLE_INFO"],sortby=["param_sample_group"]).rename(columns={'param_sample_name': 'param_name'})
        df_sample["type"] = "names"
        df_sample["position"] = -1
        df_sample["datamodel"] = "METADATA_SAMPLE_INFO"
        df_sample = pd.concat([pd.DataFrame([{'param_name': "Test Material Details", 'type': 'group', 'position' : '0', 'position_label' : 0,'datamodel' : 'METADATA_SAMPLE_INFO'}],
                                            columns=df_sample.columns), df_sample], ignore_index=True)
    else:
        raise Exception("Missing METADATA_SAMPLE_INFO")

    if "METADATA_SAMPLE_PREP" in json_blueprint:
        df_sample_prep = json2frame(json_blueprint["METADATA_SAMPLE_PREP"],sortby=["param_sampleprep_group"]).rename(columns={'param_sampleprep_name': 'param_name'})
        result_df_sampleprep = iom_format(df_sample_prep,"param_name","param_sampleprep_group")
        result_df_sampleprep["datamodel"] = "METADATA_SAMPLE_PREP"
    else:
        raise Exception("Missing METADATA_SAMPLE_PREP")
    if "METADATA_PARAMETERS" in json_blueprint:
        df_params = json2frame(json_blueprint["METADATA_PARAMETERS"],sortby=["param_group"])
        result_df = iom_format(df_params)
        result_df["datamodel"] = "METADATA_PARAMETERS"
    else:
        raise Exception("Missing METADATA_PARAMETERS")

    #print(df_sample.columns,result_df.columns)
    #empty_row = pd.DataFrame({col: [""] * len(result_df.columns) for col in result_df.columns})

    df_method = pd.DataFrame(list(get_method_metadata(json_blueprint).items()), columns=['param_name', 'param_value'])
    df_method["type"] = "names"
    df_method["position"] = -1
    df_method["datamodel"] = "METHOD"
    df_info =  pd.concat([
        df_method[["param_name","type","position","datamodel"]],
        df_sample[["param_name","type","position","datamodel"]],
        result_df_sampleprep[["param_name","type","position","datamodel"]],
        result_df[["param_name","type","position","datamodel"]],
        get_treatment(json_blueprint)[["param_name","type","position","datamodel"]]
        ], ignore_index=True)
    #print(df_info)
#:END: Please do not add information below this line
#Template version	{{ || version }}
#Template authors	{{ || acknowledgements }}
#Template downloaded	{{ || downloaded }}


    df_info["position"] = range(1, 1 + len(df_info) )
    df_info["position_label"] = 0
    df_info = pd.concat([df_info,pd.DataFrame([{ "param_name" : "Linked exeriment identifier", "type" : "names", "position" : 1, "position_label" : 5 , "datamodel" : "INVESTIGATION_UUID"}])])

    df_result = pd.DataFrame(json_blueprint["question3"]) if 'question3' in json_blueprint else None
    df_raw =  pd.DataFrame(json_blueprint["raw_data_report"]) if "raw_data_report" in json_blueprint else None
    return df_info,df_result,df_raw

def results_table(df_result,result_name='result_name',results_conditions='results_conditions'):
    print(df_result)
    unique_result_names = df_result[result_name].unique()
    new_header = list(["Material"])
    if results_conditions in df_result.columns:
        unique_conditions = set(condition for conditions in df_result[results_conditions].dropna() for condition in conditions)
        new_header = new_header + list(unique_conditions)
    new_header = new_header + list(unique_result_names)
    return pd.DataFrame(columns=new_header)


def iom_format_2excel(file_path, df_info,df_result,df_raw=None):
    _SHEET_INFO =  "Test_conditions"
    _SHEET_RAW = "Raw_data_TABLE" 
    _SHEET_RESULT = "Results_TABLE"
    _SHEET_MATERIAL = "Materials"
    _guide = [
    "Please complete all applicable fields below as far as possible. Aim to familiarise yourself with the Introductory Guidance and Example Filled Templates.",
    "While aiming to standardise data recording as far as we can, flexibility may still be needed for some Test/Assay types and their results:",
    "Thus it may be necessary to add additional items e.g. for further replicates, concentrations, timepoints, or other variations on inputs, results outputs, etc.",
    "If so, please highlight changes & alterations e.g. using colour, and/or comments in notes, or adjacent to data/tables to flag items, fluctuations from norm, etc."
    ]
    _colors = { "top" : '#002060' , "orange" : '#FFC000', 'skyblue' : '#00B0F0' , 'grey' : '#C0C0C0', 'input' : '#FFF2CC'}
    with pd.ExcelWriter(file_path, engine='xlsxwriter', mode='w') as writer:

        startrow = 7
        _sheet = _SHEET_INFO
 
        workbook = writer.book
        worksheet = workbook.add_worksheet(_sheet)
        info_sheet = worksheet
        worksheet.set_column(1, 1, 20)
        #writer.sheets[_sheet]
        cell_format_def = {
                    "group" :  {'bg_color': _colors['grey'], 'font_color' : 'blue', 'text_wrap': True, 'bold': True},
                    "names" : {'bg_color': _colors['input'], 'text_wrap': True, 'align': 'right'},
                    "group_labels" : {'bg_color': _colors['grey'], 'font_color' : 'blue', 'text_wrap': True, 'bold': True},
                    "names_labels" : { 'align': 'right', 'bold': True},
                    "top1" : {'bg_color': _colors["top"], 'font_color' : 'white', 'text_wrap': False, 'font_size' : 14, 'bold': True},
                    "top7" : {'bg_color': _colors["top"], 'font_color' : 'white', 'text_wrap': False, 'font_size' : 11, 'bold': True},
                    "orange" : {'bg_color': _colors["orange"], 'font_color' : 'blue', 'text_wrap': False, 'font_size' : 12, 'bold': True},
                    "skyblue" : {'bg_color': _colors["skyblue"], 'text_wrap': False}
                    }
        cell_format = {}
        for cf in cell_format_def:
            cell_format[cf] = workbook.add_format(cell_format_def[cf])

        for p in df_info['position_label'].unique():
            max_length = df_info.loc[df_info["position_label"]==p]["param_name"].apply(lambda x: len(str(x))).max()
            worksheet.set_column(p,p, max_length + 1)
            worksheet.set_column(p+1, p+1, 20)

        for index, row in df_info.iterrows():
            cf = cell_format[row["type"]]
            cf_labels = cell_format["{}_labels".format(row["type"])]
            worksheet.write(startrow+row['position']-1,row['position_label'],row['param_name'],cf_labels)
            worksheet.write(startrow+row['position']-1,row['position_label']+1,row['position'],cf)
            if row["type"] == "group":
                worksheet.set_row(startrow+row['position']-1, None, cf_labels)
            else:
                try:
                    worksheet.write_comment(startrow+row['position']-1,row['position_label']+1, row["datamodel"])
                except:
                    print(row['param_name'],row["datamodel"])
                    pass

        worksheet.set_row(0, None, cell_format["top1"])

        for row in range(1, startrow-2):
            worksheet.set_row(row, None, cell_format["top7"])
            worksheet.write(row, 0, _guide[row-1])

        worksheet.set_row(startrow-2, None, cell_format["orange"])
        worksheet.set_row(startrow-1, None, cell_format["skyblue"])
        worksheet.write("A1","Project")
        worksheet.write("B1","Test Data Recording Form (TDRF)")
        worksheet.write("A6","TEST CONDITIONS")
        worksheet.write("B6","Please ensure you also complete a Test Method Description Form (TMDF) for this test type")
        if df_raw is None:
            pass
        else:
            _sheet = _SHEET_RAW
            new_df = results_table(df_raw,result_name='raw_endpoint',results_conditions='raw_conditions')
            new_df.to_excel(writer, sheet_name=_sheet, index=False)
            worksheet = writer.sheets[_sheet]
            for i, col in enumerate(new_df.columns):
                worksheet.set_column(i, i, len(col) + 1 )

        if df_result is None:
            pass
        else:
            _sheet = _SHEET_RESULT 
            new_df = results_table(df_result,result_name='result_name',results_conditions='results_conditions')
            new_df.to_excel(writer, sheet_name=_sheet, index=False)
            worksheet = writer.sheets[_sheet]
            for i, col in enumerate(new_df.columns):
                worksheet.set_column(i, i, len(col) + 1 )
        materials_sheet = create_materials_sheet(workbook,writer,
                                    materials=_SHEET_MATERIAL,
                                    info=_SHEET_INFO,results=[_SHEET_RAW,_SHEET_RESULT])


def create_materials_sheet(workbook,writer,materials,info,results):
    info_sheet = writer.sheets[info]
    materials_sheet = workbook.add_worksheet(materials)
    column_headers = get_materials_columns()
    table = pd.DataFrame(columns=column_headers)
    table.to_excel(writer, sheet_name=materials, startrow=0, startcol=0, index=False)
    erm_identifiers_range = "{}!$B:$B".format(materials)  # Entire column B
    workbook.define_name('ERM_Identifiers', erm_identifiers_range)
    validation_cell = 'B23'  # cell to apply validation
    validation = {
        'validate': 'list',
        'source': '=ERM_Identifiers'
    }
    info_sheet.data_validation(validation_cell, validation)
    vlookup = [('B24',3),('B25',9),('B26',4),('B27',6),('B29',8)]
    for v in vlookup:
        formula = '=VLOOKUP($B$23,Materials!B:J,"{}",FALSE)'.format(v[1])
        info_sheet.write_formula(v[0], formula)
    for result in results:
        result_sheet = writer.sheets[result]        
        result_sheet.data_validation("A2:A1048576", validation)
    return materials_sheet

