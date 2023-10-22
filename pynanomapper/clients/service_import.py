import traceback
from pynanomapper.clients.service_charisma import H5Service
import glob
import os
import json
import pandas as pd

class ImportService(H5Service):
    def __init__(self,tokenservice,ramandb_api,hsds_investigation,dry_run=False):
        super().__init__(tokenservice)
        self.ramandb_api = ramandb_api
        self.hsds_investigation = hsds_investigation
        self.dry_run = dry_run


    def submit2hsds(self,_file,
                    hsds_provider,hsds_instrument,hsds_wavelength,optical_path,sample,laser_power):

        domain = self.create_domain_experiment(self.hsds_investigation,hsds_provider,hsds_instrument,hsds_wavelength)
        api_dataset = "{}dataset?domain={}".format(self.ramandb_api,domain)
        formData = {"investigation" : self.hsds_investigation,
                    "provider":hsds_provider,
                    "instrument": hsds_instrument,
                    "wavelength": hsds_wavelength,
                    "optical_path" : optical_path,
                    "sample" : sample,
                    "laser_power" : laser_power}

        formFiles = {"file[]" :  _file}
                #formData.append("optical_path",$("#optical_path").val());
                #formData.append("laser_power",$("#laser_power").val());
        self.tokenservice.refresh_token()
        response = self.post(api_dataset, data=formData,files=formFiles)
        return response.json()



    def delete_datasets(self,hsds_provider,hsds_instrument,
                        hsds_wavelength):
        api_dataset = "{}dataset".format(self.ramandb_api);
        formData = {"investigation" :self.hsds_investigation,
                    "provider":hsds_provider,
                    "instrument": hsds_instrument,
                    "wavelength": hsds_wavelength
                }
        try:
            response = self.post(api_dataset, data=formData)
        except Exception as err:
            print(err)
            pass

    def import2hsds(self,metadata_file,logs_folder):
        meta_files = pd.read_excel(metadata_file, sheet_name="files",index_col=0)
        meta_path = pd.read_excel(metadata_file, sheet_name="paths",index_col=0)
        root = meta_path.loc["path","value"]
        if not os.path.exists(logs_folder):
            os.mkdir(logs_folder)
        log_file = os.path.join(logs_folder,"log.json")
        log = { 'results' : {}, 'errors' : {}, 'delete' : {}}
        for index, row in meta_files.iterrows():
            file_name = os.path.join(root,index)
            try:
                if row["enabled"]:
                    hsds_provider = row["hsds_provider"]
                    hsds_instrument = row["hsds_instrument"]
                    hsds_wavelength = row["wavelength"]
                    metadata = row.to_dict()
                    metadata["provider"] = row["hsds_provider"]
                    metadata["instrument"] = row["hsds_instrument"]

                    if row["delete"]:
                        try:
                            self.delete_datasets(hsds_provider,hsds_instrument,
                                hsds_wavelength)
                        except Exception as err:
                            log["delete"][file_name]  = err

                    try:

                        print(file_name)
                        with  open(file_name,'rb') as _file:
                            if self.dry_run:
                                log["results"][file_name] = "dry run"
                            else:
                                log["results"][file_name]  = "start"
                                response = self.submit2hsds(_file,
                                    hsds_provider,hsds_instrument,hsds_wavelength,
                                    row["op_id"] if "op_id" in row else "",
                                    row["sample"] if "sample" in row else "",
                                    row["laser_power"] if "laser_power" in row else "")
                                log["results"][file_name]  = response
                    except Exception as err:
                            log["errors"][file_name]  = str(err)
                else:
                    log["errors"][file_name]  =  "disabled"
            except Exception as err:
                log["errors"][file_name]  = str(err)
                traceback.print_exc()

        with open(log_file, "w",encoding="utf-8") as write_file:
            json.dump(log, write_file, sort_keys=False, indent=4)
