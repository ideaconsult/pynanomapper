import traceback
from services.service_charisma import H5Service
import glob
import os
import json

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


    def files2hsds(self,metadata,hsds_provider,hsds_instrument,hsds_wavelength,log_file):
        folder_input = metadata["folder_input"]
        log = {"results" : {}}
        spectra_files = glob.glob(os.path.join(folder_input,"**","*"), recursive=True)
        file_lookup = {}
        for file_name in spectra_files:
            if file_name.endswith(".xlsx"):
                continue
            if file_name.endswith(".html"):
                continue
            if file_name.endswith(".ipynb"):
                continue
            if file_name.endswith(".l6s"): # not supported spectrum file
                continue
            if os.path.isdir(file_name):
                continue
            basename = os.path.basename(file_name)
            (base,ext) = os.path.splitext(basename)
            file_lookup[basename] = [file_name]
            if base in file_lookup:
                file_lookup[base].append(file_name)
            else:
                file_lookup[base]  = [file_name]
        #print(file_lookup)

        _notfound = []
        for op in metadata["optical_path"]:
            for files in op["files"]:
                for file in files["file"]:

                    if file in file_lookup:

                        for file_name in file_lookup[file]:
                            if file_name.endswith(".cha"):
                                continue
                            laser_power = "" if pd.isna(files["laser_power"]) else files["laser_power"]
                            sample = files["sample"]
                            op_id = op["id"]

                            if self.dry_run:
                                pass
                            else:
                                try:
                                    with  open(file_name,'rb') as _file:
                                        response = self.submit2hsds(_file,
                                        hsds_provider,hsds_instrument,hsds_wavelength,
                                        op_id,sample,laser_power)
                                        log["results"][file_name]  = response
                                except Exception as err:
                                    print(err,sample,op_id,laser_power,file_name)
                    else:
                        _notfound.append(file)


        log["files"] = file_lookup
        log["not_found"] = _notfound
        with open(log_file, "w",encoding="utf-8") as write_file:
            json.dump(log, write_file, sort_keys=True, indent=4)

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

    def import2hsds(self,config_input,metadata_root,logs_folder):
        if not os.path.exists(logs_folder):
            os.mkdir(logs_folder)
        with open(config_input, 'r') as infile:
            config = json.load(infile)
        for entry in config:
            try:
                if entry["enabled"]:
                    hsds_provider = entry["hsds_provider"]
                    hsds_instrument = entry["hsds_instrument"]
                    hsds_wavelength = entry["hsds_wavelength"]
                    json_metadata = os.path.join(metadata_root,"metadata_{}_{}_{}.json".
                        format(hsds_provider,hsds_instrument,hsds_wavelength))
                    log_file = os.path.join(logs_folder,"log_{}_{}_{}.json".
                        format(hsds_provider,hsds_instrument,hsds_wavelength))
                    with open(json_metadata, 'r') as infile:
                        metadata = json.load(infile)
                    if entry["delete"]:
                        try:
                            self.delete_datasets(hsds_provider,hsds_instrument,
                                hsds_wavelength)
                        except Exception as err:
                            print(err)
                    self.files2hsds(metadata,
                            hsds_provider,hsds_instrument,
                            hsds_wavelength,log_file)
            except Exception as err:
                traceback.print_exc()
