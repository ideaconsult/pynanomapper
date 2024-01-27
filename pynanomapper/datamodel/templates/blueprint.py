import pandas as pd


def iom_format_old(df,param_name="param_name",param_group="param_group"):
    df.fillna(" ",inplace=True)
    # Create a new DataFrame with one column
    result_df = pd.DataFrame(columns=['param_name'])
    # Iterate through unique groups
    for group in df[param_group].unique():
        group_df = df[df[param_group] == group]
        # Get names for the group
        names = group_df[param_name].tolist()
        # Append group and names to the result DataFrame
        result_df = pd.concat([result_df, pd.DataFrame({'param_name': [group] + names + ['']})], ignore_index=True)
    return result_df

def iom_format(df,param_name="param_name",param_group="param_group"):
    df.fillna(" ",inplace=True)
    # Create a new DataFrame with one column
    result_df = pd.DataFrame(columns=['param_name'])
    result_df["type"] = "group"
    # Iterate through unique groups
    for group in df[param_group].unique():
        group_df = df[df[param_group] == group]
        # Get names for the group
        names = group_df[param_name].tolist()
        print(names)
        # Append group and names to the result DataFrame
        tmp = pd.DataFrame({'param_name': [group] + names })
        tmp["type"] = "names"
        tmp.at[0, "type"] = "group"
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
    "Project Work Package" : "",
    "Partner conducting test/assay" : "",
    "Test facility - Laboratory name" : "",
    "Lead Scientist & contact for test" : "",
    "Assay/Test work conducted by" : "",
    "Full name of test/assay" : json_blueprint.get("EXPERIMENT",""),
    "Short name or acronym for test/assay": json_blueprint.get("METHOD",""),
    "Type or class of experimental test as used here": json_blueprint.get("PROTOCOL_CATEGORY_CODE",""),
    "End-Point being investigated/assessed by the test" : [],
    "Raw data metrics" : [],
    "SOP(s) for test" : "",
    "Path/link to sop/protocol": "",
    "Test start date": None,
    "Test end date": None
    }
    return _header

def get_materials_df():
    _header = ["","ERM identifiers","ID","Name","CAS","type","Supplier","Supplier code","Batch","Core","BET surface in m²/g"]
    return pd.DataFrame(columns=_header)


def get_template_frame(json_blueprint):
    df_sample = json2frame(json_blueprint["METADATA_SAMPLE_INFO"],sortby=["param_sample_group"]).rename(columns={'param_sample_name': 'param_name'})
    df_sample["type"] = "names"
    df_sample = pd.concat([pd.DataFrame([{'param_name': "Test Material Details", 'type': 'group'}], columns=df_sample.columns), df_sample], ignore_index=True)


    df_sample_prep = json2frame(json_blueprint["METADATA_SAMPLE_PREP"],sortby=["param_sampleprep_group"]).rename(columns={'param_sampleprep_name': 'param_name'})
    result_df_sampleprep = iom_format(df_sample_prep,"param_name","param_sampleprep_group")

    #df_sample["param_sample_name"]
    df_params = json2frame(json_blueprint["METADATA_PARAMETERS"],sortby=["param_group"])
    result_df = iom_format(df_params)

    #print(df_sample.columns,result_df.columns)
    #empty_row = pd.DataFrame({col: [""] * len(result_df.columns) for col in result_df.columns})

    df_method = pd.DataFrame(list(get_method_metadata(json_blueprint).items()), columns=['param_name', 'param_value'])
    df_method["type"] = "names"
    df_info =  pd.concat([
        df_method[["param_name","type"]],
     #   empty_row,
        df_sample[["param_name","type"]],
     #   empty_row,
        result_df_sampleprep[["param_name","type"]],
     #   empty_row,
        result_df[["param_name","type"]]
        ], ignore_index=True)
    df_result = pd.DataFrame(json_blueprint["question3"]) if 'question3' in json_blueprint else None
    df_raw =  pd.DataFrame(json_blueprint["raw_data_report"]) if "raw_data_report" in json_blueprint else None
    return df_info,df_result,df_raw

def results_table(df_result,result_name='result_name',results_conditions='results_conditions'):
    unique_result_names = df_result[result_name].unique()
    unique_conditions = set(condition for conditions in df_result[results_conditions] for condition in conditions)
    new_header = list(["Material"]) + list(unique_conditions) + list(unique_result_names)
    return pd.DataFrame(columns=new_header)

def iom_format_2excel(file_path, df_info,df_result,df_raw=None):
    with pd.ExcelWriter(file_path, engine='xlsxwriter', mode='w') as writer:
        startrow = 7
        df_info[["param_name"]].to_excel(writer, sheet_name='Test_conditions', index=False, startrow=startrow, startcol = 0, header=False)
        workbook = writer.book
        worksheet = writer.sheets['Test_conditions']
        cell_format = workbook.add_format({'bg_color': '#002060', 'text_wrap': True})
        for row in range(0, startrow-2):
            worksheet.set_row(row, None, cell_format)
        cell_format = workbook.add_format({'bg_color': '#FFC000', 'text_wrap': True})
        worksheet.set_row(startrow-2, None, cell_format)
        cell_format = workbook.add_format({'bg_color': '#00B0F0', 'text_wrap': True})
        worksheet.set_row(startrow-1, None, cell_format)

        rows_with_condition = df_info.loc[df_info["type"] == "group"].index.tolist()
        cell_format = workbook.add_format({'bg_color': '#C0C0C0', 'text_wrap': True})
        for row in rows_with_condition:
            worksheet.set_row(row+startrow, None, cell_format)
        # Apply the formatting to the header row
        #for col_num, value in enumerate(df_info.columns.values):
        #    worksheet.write(0, col_num, value, cell_format_header)
        #for row_num in range(1, len(df_info) + 1):
        #    worksheet.write(row_num, 0, df_info.iloc[row_num - 1, 0], cell_format_right_align)
        cell_format = workbook.add_format({'align': 'right','text_wrap': True,'bold': True})
        # Apply the formatting to a specific column (e.g., Column2)
        max_length = df_info["param_name"].apply(lambda x: len(str(x))).max()
        #worksheet.set_column(0, 0, max_length + 1 )
        worksheet.set_column(0,0, max_length + 1 , cell_format)


        cell_format = workbook.add_format({'bg_color': '#FFF2CC', 'text_wrap': True})
        worksheet.set_column(1, 1, 20, cell_format)
        #worksheet = writer.sheets['Raw_data']

        #worksheet = writer.sheets['Results']
        if df_raw is None:
            pass
        else:
            new_df = results_table(df_raw,result_name='raw_endpoint',results_conditions='raw_conditions')
            new_df.to_excel(writer, sheet_name='Raw_data', index=False)
            worksheet = writer.sheets['Raw_data']
            for i, col in enumerate(new_df.columns):
                worksheet.set_column(i, i, len(col) + 1 )

        if df_result is None:
            pass
        else:
            new_df = results_table(df_result,result_name='result_name',results_conditions='results_conditions')
            new_df.to_excel(writer, sheet_name='Results', index=False)
            worksheet = writer.sheets['Results']
            for i, col in enumerate(new_df.columns):
                worksheet.set_column(i, i, len(col) + 1 )

        df_material = get_materials_df()
        df_material.to_excel(writer, sheet_name='Materials', index=False)
        worksheet = writer.sheets['Materials']
        # Set column widths to fit the header text
        for i, col in enumerate(df_material.columns):
            worksheet.set_column(i, i, len(col) + 1 )

