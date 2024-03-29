from pynanomapper.datamodel.templates import blueprint as bp
from pathlib import Path
import json
import os.path 

TEST_JSON_PATH = Path(__file__).parent / "resources/templates/dose_response.json"
TEMPLATE_UUID = "3c22a1f0-a933-4855-848d-05fcc26ceb7a"
TEMPLATE_DIR = Path(__file__).parent / "resources/templates"

def test_doseresponse_template():
    with open(TEST_JSON_PATH, "r") as file:
        json_blueprint = json.load(file)
        _path = get_template_xlsx(TEMPLATE_UUID,json_blueprint)
        assert(Path(_path).exists())

def test_doseresponse_nmparser():
    with open(TEST_JSON_PATH, "r") as file:
        json_blueprint = json.load(file)
        _path = get_nmparser_config(TEMPLATE_UUID,json_blueprint)
        assert(Path(_path).exists())

def get_template_xlsx(uuid,json_blueprint):
    try:
        file_path_xlsx = os.path.join(TEMPLATE_DIR, f"{uuid}.xlsx")   
        df_info,df_result,df_raw, df_conditions =bp.get_template_frame(json_blueprint)
        bp.iom_format_2excel(file_path_xlsx,df_info,df_result,df_raw,df_conditions)
        return file_path_xlsx  
    except Exception as err:
        raise err

def get_nmparser_config(uuid,json_blueprint):
    file_path = os.path.join(TEMPLATE_DIR, f"{uuid}.json.nmparser")      
    json_config = bp.get_nmparser_config(json_blueprint)
    with open(file_path, 'w') as json_file:
        json.dump(json_config, json_file, indent=2)            
        return file_path           