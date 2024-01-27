import pandas as pd


def iom_format(df,param_name="param_name",param_group="param_group"):
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

def json2frame(json_data,sortby):
    return pd.DataFrame(json_data).sort_values(by=sortby)

def get_template_frame(json_blueprint):
    df_sample = json2frame(json_blueprint["METADATA_SAMPLE_INFO"],sortby=["param_sample_group"]).rename(columns={'param_sample_name': 'param_name'})

    df_sample_prep = json2frame(json_blueprint["METADATA_SAMPLE_PREP"],sortby=["param_sampleprep_group"]).rename(columns={'param_sampleprep_name': 'param_name'})
    result_df_sampleprep = iom_format(df_sample_prep,"param_name","param_sampleprep_group")

    #df_sample["param_sample_name"]
    df_params = json2frame(json_blueprint["METADATA_PARAMETERS"],sortby=["param_group"])
    result_df = iom_format(df_params)

    #print(df_sample.columns,result_df.columns)
    empty_row = pd.DataFrame({col: [""] * len(result_df.columns) for col in result_df.columns})
    return pd.concat([df_sample[["param_name"]],empty_row,result_df_sampleprep,empty_row,result_df], ignore_index=True)

def iom_format_2excel(df,file_path):
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Test_conditions', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Test_conditions']
        cell_format = workbook.add_format({'bold': True, 'font_color': 'red'})
                    # Apply the formatting to the header row
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, cell_format)

        cell_format_header = workbook.add_format({'bold': True, 'font_color': 'black'})
        cell_format_right_align = workbook.add_format({'align': 'right'})

        # Apply the formatting to the header row
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, cell_format_header)
        for row_num in range(1, len(df) + 1):
            worksheet.write(row_num, 0, df.iloc[row_num - 1, 0], cell_format_right_align)
