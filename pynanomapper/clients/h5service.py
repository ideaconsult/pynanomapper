from pynanomapper.clients.authservice import QueryService
import h5py
import h5pyd
import traceback

class H5BasicService(QueryService):
    def __init__(self,tokenservice):
        super().__init__(tokenservice)

    def File(self,name, mode='r',retries=1):
        return h5pyd.File(name, mode=mode, retries=retries, api_key=self.tokenservice.api_key());

    def Folder(self,name,mode = 'r'):
        return h5pyd.Folder(name, mode=mode,  api_key=self.tokenservice.api_key());

    def check_folder(self,domain="/",create=False,owner=None):
        #cfg = hsinfo.cfg
        try:
            return self.Folder(domain)
        except IOError as err:
            if create:
                return self.Folder(domain, mode='x',  owner=owner)
            else:
                raise err


    def copy_h5layer(self,fin,fout):
        for key in fin.keys():
            dest = None
            if isinstance(fin[key], h5pyd.Dataset):
                dest = fout.create_dataset(key,data=fin[key].value)
                for idx in range(0,fin[key].ndim):
                    fout[key].dims[idx].label = fin[key].dims[idx].label
            else:
                fout.require_group(key)
                for a in fin[key].attrs:
                    if isinstance(fin[key].attrs[a], str):
                        fout[key].attrs[a] = fin[key].attrs[a]
                self.copy_h5layer(fin[key],fout[key])

    def download(self,domain,tmpfile):
        try:
            with h5py.File(tmpfile,"w") as fout:
                with self.File(domain,mode="r") as fin:
                    #load_file(fin, fout,dataload="ingest")
                    self.copy_h5layer(fin,fout)

        except Exception as err:
            raise(err)

    def check_paths(self,params,paths,skip_paths,create_folders):

        folder = ""
        h5folder=None
        for p in paths:
            if p in skip_paths:
                continue;
            folder = "{}/{}".format(folder,params[p])
            domain="{}/".format(folder)
            try:
                h5folder = self.check_folder(domain,create=create_folders)
                h5folder.close()
            except Exception as err:
                raise(err)

        return domain,folder;



    def filter_dataset(self,topdomain,domain,process_file,sample=None,wavelength=None,instrument=None,provider=None,investigation=None,kwargs={}):
        with self.File(domain) as dataset:
            if sample is None:
                process_file(topdomain,domain,**kwargs)
            elif dataset["annotation_sample"].attrs["sample"] == sample:
                process_file(topdomain,domain,**kwargs)

    def visit_domain(self,topdomain="/",process_dataset=None,kwargs={}):
        if topdomain.endswith("/"):
            with self.Folder(topdomain) as domain:
                n = domain._getSubdomains()
                for domain in domain._subdomains:
                    #print(domain)
                    if domain["class"]=="folder":
                        self.visit_domain("{}/".format(domain["name"]),process_dataset,kwargs)
                    else:
                        if not (process_dataset is None):
                            process_dataset(topdomain,domain["name"],**kwargs)
        else:
            if not (process_dataset is None):
                process_dataset(None,topdomain,**kwargs)         #def delete_datasets(self,folder):

    def create_domain(self,domain):
        try:
            return self.Folder(domain)
        except IOError as err:
            traceback.print_exc()
            try:
                return self.Folder(domain, mode='x')
            except IOError as err:
                raise(err)

    def check_domain(self,domain):
        return self.Folder(domain)

    #def delete_domain_recursive(self,fname):
    #    self.visit_domain(fname,process_folder=self.delete_datasets)


    def delete_datasets(self,domain):
        try:
            f = self.Folder(domain)
            n = f._getSubdomains()
            _deleted = []
            if n>0:
                for s in f._subdomains:

                    if not s["name"].endswith("metadata.h5"):
                        hsdel.deleteDomain(s["name"])
                        _deleted.append(s["name"])
            return _deleted
        except Exception as err:
            raise err

    def create_domain(self,domain):
        try:
            return self.Folder(domain)
        except IOError as err:
            traceback.print_exc()
            try:
                return self.Folder(domain, mode='x')
            except IOError as err:
                raise(err)

    def check_domain(self,domain):
        return self.Folder(domain)
