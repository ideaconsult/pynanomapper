from pynanomapper.datamodel.templates import blueprint as bp
from pathlib import Path
import json
import os.path
import pandas as pd


TEMPLATE_DIR = Path(__file__).parent / "resources/templates"
TEST_JSON_PATH = f"{TEMPLATE_DIR}/dose_response.json"
TEST_PCHEM_PATH = f"{TEMPLATE_DIR}/tga.json"
TEST_FRAS_PATH = f"{TEMPLATE_DIR}/fras.json"
TEST_CALIBRATION_PATH = f"{TEMPLATE_DIR}/calibration.json"

TEST_EXCEL_ERROR_UUID = "015690ac-b26a-4845-826e-c479a62eef62"
TEST_EXCEL_ERROR = f"{TEMPLATE_DIR}/{TEST_EXCEL_ERROR_UUID}.json"
TEMPLATE_UUID = "3c22a1f0-a933-4855-848d-05fcc26ceb7a"


def test_doseresponse_template():
    with open(TEST_JSON_PATH, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        _path = get_template_xlsx(TEMPLATE_UUID, json_blueprint)
        assert(Path(_path).exists())
        xls = pd.ExcelFile(_path)
        assert "Raw_data_TABLE" in xls.sheet_names
        assert "Results_TABLE" in xls.sheet_names
        assert "Test_conditions" in xls.sheet_names
        assert "Materials" in xls.sheet_names
        read_hidden_json(xls)


def test_doseresponse_rawonly_template():
    with open(TEST_JSON_PATH, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        json_blueprint["data_sheets"] = ["data_raw", "data_platelayout"]
        json_blueprint["plate_format"] = 384
        _path = get_template_xlsx(TEMPLATE_UUID, json_blueprint)
        assert Path(_path).exists()
        xls = pd.ExcelFile(_path)
        assert "Raw_data_TABLE" in xls.sheet_names
        assert "Results_TABLE" not in xls.sheet_names
        assert "Test_conditions" in xls.sheet_names
        assert "Materials" in xls.sheet_names
        assert "plate_table" in xls.sheet_names
        assert "plate_metadata" in xls.sheet_names
        assert "plate_readout" in xls.sheet_names
        assert "plate_materials" in xls.sheet_names
        read_hidden_json(xls)


def test_doseresponse_fras_template():
    with open(TEST_FRAS_PATH, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        _path = get_template_xlsx(TEMPLATE_UUID, json_blueprint)
        assert Path(_path).exists()
        xls = pd.ExcelFile(_path)
        assert "Raw_data_TABLE" in xls.sheet_names
        assert "Results_TABLE" in xls.sheet_names  
        assert "Test_conditions" in xls.sheet_names
        assert "Materials" in xls.sheet_names
        read_hidden_json(xls)
      

def test_doseresponse_fras_template_aspchem():
    with open(TEST_FRAS_PATH, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        json_blueprint["template_layout"] = "pchem"
        _path = get_template_xlsx(TEMPLATE_UUID, json_blueprint)
        assert Path(_path).exists()
        xls = pd.ExcelFile(_path)
        assert "Experimental_setup" in xls.sheet_names
        assert "Results_TABLE" in xls.sheet_names  
        assert "Provider_informations" in xls.sheet_names
        assert "Materials" in xls.sheet_names
        read_hidden_json(xls)
              

def test_doseresponse_error_template():
    with open(TEST_EXCEL_ERROR, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        json_blueprint["data_sheets"] = ["data_raw"]
        _path = get_template_xlsx(TEST_EXCEL_ERROR_UUID, json_blueprint)
        assert Path(_path).exists()
        xls = pd.ExcelFile(_path)
        assert "Raw_data_TABLE" in xls.sheet_names
        assert "Results_TABLE" not in xls.sheet_names  
        assert "Test_conditions" in xls.sheet_names
        assert "Materials" in xls.sheet_names
        read_hidden_json(xls)


def test_doseresponse_resultsonly_template():
    with open(TEST_JSON_PATH, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        json_blueprint["data_sheets"] = ["data_processed"]
        _path = get_template_xlsx(TEMPLATE_UUID, json_blueprint)
        assert Path(_path).exists()
        xls = pd.ExcelFile(_path)
        assert "Raw_data_TABLE" not in xls.sheet_names
        assert "Results_TABLE" in xls.sheet_names        
        assert "Test_conditions" in xls.sheet_names
        assert "Materials" in xls.sheet_names
        read_hidden_json(xls)


def test_doseresponse_calibration_template():
    with open(TEST_CALIBRATION_PATH, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        assert("calibration_report" in json_blueprint)
        _path = get_template_xlsx(TEMPLATE_UUID, json_blueprint)
        assert(Path(_path).exists())
        xls = pd.ExcelFile(_path)
        assert "Raw_data_TABLE" in xls.sheet_names
        assert "Results_TABLE" in xls.sheet_names
        assert "Calibration_TABLE" in xls.sheet_names
        assert "Test_conditions" in xls.sheet_names
        assert "Materials" in xls.sheet_names
        read_provenance(xls,"dose_response","Project",
                        json_blueprint.get("provenance_workpackage",None))
        read_hidden_json(xls)


def read_provenance(xls, layout="pchem", project=None, wp=None):
    info_sheet = "Provider_informations" if layout == "pchem" else "Test_conditions"
    assert info_sheet in xls.sheet_names
    df = pd.read_excel(xls, sheet_name=info_sheet, header=None)
    # pchem b6 else a1
    project_content = df.iloc[12,1] if layout == "pchem"  else df.iloc[0,0] 
    assert project == project_content
    # pchem B7 else B8 
    wp_content = df.iloc[6,1] if layout == "pchem" else df.iloc[7,1]  #B8
    assert wp == wp_content


def read_hidden_json(xls):
    assert "TemplateDesigner" in xls.sheet_names
    # Load B2 from TemplateDesigner
    df = pd.read_excel(xls, sheet_name="TemplateDesigner", header=None)
    b2_content = df.iloc[1, 1]  # B2 is (1,1) with zero-based indexing
    assert isinstance(b2_content, str), "Cell B2 content should be a string"
    try:
        template_dict = json.loads(b2_content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"B2 content is not valid JSON: {e}")
    assert isinstance(template_dict, dict), "Parsed B2 content should be a dictionary"    


def test_pchem_template():
    with open(TEST_PCHEM_PATH, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        json_blueprint["template_layout"] = ["pchem"]
        json_blueprint["data_sheets"] = ["data_processed"]
        _path = get_template_xlsx(TEMPLATE_UUID, json_blueprint)
        assert Path(_path).exists()
        xls = pd.ExcelFile(_path)
        #assert not "Raw_data_TABLE" in xls.sheet_names
        assert "Results_TABLE" in xls.sheet_names
        assert "Provider_informations" in xls.sheet_names
        assert "Experimental_setup" in xls.sheet_names
        assert "Materials" in xls.sheet_names
        read_provenance(xls,"pchem",
                        json_blueprint.get("provenance_project",None),
                        json_blueprint.get("provenance_workpackage",None))
        read_hidden_json(xls)


def test_doseresponse_nmparser():
    with open(TEST_JSON_PATH, "r", encoding='utf-8') as file:
        json_blueprint = json.load(file)
        _path = get_nmparser_config(TEMPLATE_UUID, json_blueprint)
        assert Path(_path).exists()


def get_template_xlsx(uuid, json_blueprint):
    try:
        file_path_xlsx = os.path.join(TEMPLATE_DIR, f"{uuid}.xlsx")   
        layout = json_blueprint.get("template_layout","dose_response")
        if layout == "dose_response": 
            df_info, df_result, df_raw, df_conditions, df_calibrate = bp.get_template_frame(
                json_blueprint)
            bp.iom_format_2excel(file_path_xlsx, df_info, df_result, df_raw, df_conditions, df_calibrate)
            bp.add_plate_layout(file_path_xlsx, json_blueprint)
            json_blueprint["template_uuid"] = uuid            
            bp.add_hidden_jsondef(file_path_xlsx, json_blueprint)
        else:
            json_blueprint["template_uuid"] = uuid
            bp.pchem_format_2excel(file_path_xlsx, json_blueprint)
        return file_path_xlsx
    except Exception as err:
        raise err


def get_nmparser_config(uuid, json_blueprint):
    file_path = os.path.join(TEMPLATE_DIR, f"{uuid}.json.nmparser")
    json_config = bp.get_nmparser_config(json_blueprint)
    with open(file_path, 'w') as json_file:
        json.dump(json_config, json_file, indent=2)
        return file_path