import h5py,h5pyd
import traceback
from matplotlib.figure import Figure
import numpy as np
from pynanomapper.clients.authservice import QueryService
from pynanomapper.clients.h5service import H5BasicService
from pynanomapper.clients.datamodel_simple import StudyRaman, Substance
from ramanchada2.spectrum import from_chada
import os.path
import uuid
from numcompress import compress, decompress
import requests
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import io
from io import BytesIO
import base64

class H5Service(H5BasicService):
    def __init__(self,tokenservice):
        super().__init__(tokenservice)
        self.tags = ["sample","investigation","provider","instrument","wavelength","optical_path"]

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

    def create_domain_experiment(self,hsds_investigation,hsds_provider,hsds_instrument,hsds_wavelength):
        domain = "/{}/{}/{}/{}/".format(hsds_investigation,hsds_provider,hsds_instrument,hsds_wavelength)
        try:
            self.check_domain(domain)
            return domain
        except IOError as ioerr:
            try:
                self.check_domain("/{}/".format(hsds_investigation))
                try:
                    self.create_domain("/{}/{}/".format(hsds_investigation,hsds_provider))
                    self.create_domain("/{}/{}/{}/".format(hsds_investigation,hsds_provider,hsds_instrument))
                    self.create_domain(domain)
                    return domain
                except IOError as err:
                    traceback.print_exc()
                    raise(err)
            except Exception as err:
                traceback.print_exc()
                raise(err)

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

    @staticmethod
    def empty_figure(figsize,title,label):
        fig = Figure(figsize=figsize)
        axis = fig.add_subplot(1, 1, 1)
        axis.axis('off')
        #axis.set_xticks([])
        #axis.set_yticks([])
        axis.scatter([0,1],[0,0],s=0)
        axis.annotate(label,(0,0))
        axis.title.set_fontsize(8)
        axis.set_title(title)
        return fig

    @staticmethod
    def dict2figure(pm,figsize):
        fig = Figure(figsize=figsize)
        axis = fig.add_subplot(1, 1, 1)
        n = 0
        for key in pm:
            if key=="domain" or key=="id" or key=="score":
                continue
            if type(pm[key])==str:
                n=n+1
        score = float(pm["score"])
        #axis.bar(["score"],[score],width=0.1)
        #axis.bar(["score"],[1-score],width=0.1)
        y = np.arange(0,n)
        x = np.repeat(0,n)

        axis.scatter(x,y,s=0)
        axis.axis('off')
        i = 0
        clr = {"high" : "r", "medium" : "y", "low" : "g", "fulfilled" : "b", "not fulfilled" : "c"}
        for key in pm:
            if key=="domain" or key=="id" or key=="score":
                continue
            if type(pm[key])==str:
                try:
                    color = clr[pm[key]]
                except:
                    color="k"
                axis.annotate("{}: {}".format(key.replace("_s",""),pm[key]),(0,i),color=color)


                i = i+1
        axis.title.set_fontsize(8)
        axis.set_xlim(0,1)
        axis.set_title(pm["domain"])
        return fig

    def solrquery_get(self,solr_url, params):
        headers = {}
        headers["Authorization"] = "Bearer {}".format(self.tokenservice.api_key());
        return requests.get(solr_url, params = params, headers= headers)

    def solrquery_post(self,solr_url, json):
        headers = {}
        headers["Authorization"] = "Bearer {}".format(self.tokenservice.api_key());
        return requests.get(solr_url, json = json, headers= headers)

    def thumbnail(self,solr_url,domain,figsize=(6,4),extraprm=""):
        rs = None
        try:
            query="textValue_s:\"{}\"".format(domain.replace(" ","\ "))
            params = {"q": query, "fq" : ["type_s:study"], "fl" : "name_s,textValue_s,reference_s,reference_owner_s,spectrum_p1024"}
            rs =  self.solrquery_get(solr_url, params = params)
            if rs.status_code==200:
                x = StudyRaman.x4search()
                for doc in rs.json()["response"]["docs"]:
                    y = doc["spectrum_p1024"]
                    fig = Figure(figsize=figsize)
                    axis = fig.add_subplot(1, 1, 1)
                    axis.plot(x, y)
                    axis.set_ylabel("a.u.")
                    axis.set_xlabel("Raman shift [1/cm]")
                    axis.title.set_text("{} {} {} ({})".format(extraprm,doc["name_s"],doc["reference_owner_s"],doc["reference_s"]))
                    return fig
            else:
                return self.empty_figure(figsize,"{} {}".format(rs.status_code,rs.reason),"{}".format(domain.split("/")[-1]))

        except Exception as err:
            raise(err)
        finally:
            if not (rs is None):
                rs.close

    def image(self,domain,dataset="raw",figsize=(6,4),extraprm=""):
        try:
            with self.File(domain,mode="r") as h5:
                x = h5[dataset][0]
                y = h5[dataset][1]
                try:
                    _sample = h5["annotation_sample"].attrs["sample"]
                except:
                    _sample = None
                try:
                    _provider = h5["annotation_study"].attrs["provider"]
                except:
                    _provider = None
                try:
                    _wavelength = h5["annotation_study"].attrs["wavelength"]
                except:
                    _wavelength = None
                fig = Figure(figsize=figsize)
                axis = fig.add_subplot(1, 1, 1)
                axis.plot(x, y, color='black')
                axis.set_ylabel(h5[dataset].dims[1].label)
                axis.set_xlabel(h5[dataset].dims[0].label)
                axis.title.set_text("{} {} ({}) {}".format(extraprm,_sample,_provider,_wavelength))
                #domain.split("/")[-1],dataset))
                return fig
        except Exception as err:
            return self.empty_figure(figsize,"Error","{}".format(domain.split("/")[-1]))

    def knnquery(self,domain,dataset="raw"):
        try:
            with self.File(domain,mode="r") as h5:
                x = h5[dataset][0]
                y = h5[dataset][1]
                (cdf,pdf) = StudyRaman.h52embedding(h5,dataset="raw",xlinspace = StudyRaman.x4search())
                result_json = {}
                result_json["cdf"] = compress(cdf.tolist(),precision=6)
                #return ','.join(map(str, cdf))
                try:
                    px = 1/plt.rcParams['figure.dpi']  # pixel in inches
                    fig = Figure(figsize=(300*px, 200*px))
                    axis = fig.add_subplot(1, 1, 1)
                    axis.plot(x, y)
                    axis.set_ylabel(h5[dataset].dims[1].label)
                    axis.set_xlabel(h5[dataset].dims[0].label)
                    axis.title.set_text("query")
                    output = io.BytesIO()
                    FigureCanvas(fig).print_png(output)
                    base64_bytes = base64.b64encode(output.getvalue())
                    result_json["imageLink"] = "data:image/png;base64,{}".format(str(base64_bytes,'utf-8'))
                except Exception as err:
                    print(err)
                return result_json
        except Exception as err:
            raise(err)

    def filter_dataset(self,topdomain,domain,process_file,sample=None,wavelength=None,instrument=None,provider=None,investigation=None,kwargs={}):
        with self.File(domain) as dataset:
            if sample is None:
                process_file(topdomain,domain,**kwargs)
            elif dataset["annotation_sample"].attrs["sample"] == sample:
                process_file(topdomain,domain,**kwargs)

    def visit_domain(self,topdomain="/",process_dataset=None,kwargs={}):
        self.tokenservice.refresh_token()
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
            #tbd
        #    pass

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
                        #hsdel.deleteDomain(s["name"])
                        #deleted.append(s["name"])
                        pass
            return _deleted
        except Exception as err:
            raise err

    def load_h5stream(self,stream,destination_domain):
        try:
            f_in = h5py.File(stream,'r')
            self.load_h5file(f_in,destination_domain)
        except Exception as err:
            raise

    def load_h5file(self,h5file,destination_domain):
        try:
            with self.File(destination_domain, "w", retries=3) as fout:
                utillib.load_file(h5file, fout, verbose=False,dataload="ingest")
        except Exception as err:
            raise

    def load_annotation(self,domain) :
        _tmp = []
        with self.File(domain) as f:
            for _tag in self.tags:
                if _tag == "sample":
                    _key = "annotation_sample"
                else:
                    _key = "annotation_study"
                if _tag in f[_key].attrs:
                    _tmp.append(f[_key].attrs[_tag])
                else:
                    _tmp.append(None)
        _tmp.append(domain)
        return _tmp

    def download2folder(self,parentdomain,domain,results=[], folder = None):
        _tmp = self.load_annotation(domain)
        tmpfile = "{}.cha".format(os.path.join(folder,str(uuid.uuid3(uuid.NAMESPACE_OID, domain))))
        self.download(domain,tmpfile)
        _tmp.append(tmpfile)
        results.append(tuple(_tmp))

    def load_metadata(self,parentdomain,domain,results=[]):
        _tmp = self.load_annotation(domain)
        results.append(tuple(_tmp))

    def load_dataset(self,parentdomain,domain,results={}):
        _tmp = []
        self.load_annotation(parentdomain,domain,results,_tmp)
        spe = from_chada(domain,h5module=self)
        spe = spe - spe.moving_minimum(16)
        spe = spe.normalize()
        results[domain] = {"spectrum" : spe,
                "metadata": tuple(_tmp)}
