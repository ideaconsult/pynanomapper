
import json

import os.path
from pprint import pprint
import glob
import pandas as pd

import traceback
import numpy as np
import ramanchada2 as rc2
import uuid
from datetime import date
import scipy.stats as stats

def prefixed_uuid(value, prefix="CRMA"):
    return prefix+"-"+str(uuid.uuid3(uuid.NAMESPACE_OID, value))

def ramanshift2wavelength(shift,laser):
    return 1/((1/laser)-shift/10**7)

def wavelength2ramanshift(wavelength,laser):
    return 10**7/laser-10**7/wavelength

class StudyRaman:
    def __init__(self, investigation, provider, parameters, filename, spectrum_embedding = (None,None)):
        self.topcategory = "P-CHEM"
        self.endpointcategory = "ANALYTICAL_METHODS_SECTION"
        self.investigation = investigation
        self.method = "Raman spectroscopy"
        self.provider = provider
        self.parameters = parameters
        self.filename = filename
        self.spectrum_embedding = spectrum_embedding

    @staticmethod
    def x4search():
        return np.linspace(140,3*1024+140,num=1024)
        #return np.linspace(140,140+2048,num=1024)

    @staticmethod
    def spectra2dist(spe,xcrop = None,remove_baseline=True,window=16):

        # else assume it's a Spectrum object for now
        #baseline removal is important
        #if remove_baseline:
        #    spe = spe - spe.moving_minimum(16)

        #no need to normalize, we'll generate probability distribution, it will self normalize!
        counts = spe.y # a spectrum is essentially a histogram :)
        x = spe.x
        #crop
        xcrop_right = max(x) if xcrop is None else xcrop[1]
        xcrop_left = 100 if xcrop is None else xcrop[0]
        index = np.where((x>=xcrop_left) & (x<=xcrop_right))
        index = index[0]
        x = x[index]
        counts = counts[index]

        if remove_baseline:
            spe.x = x
            spe.y = counts
            spe = spe - spe.moving_minimum(window)
            x = spe.x
            counts = spe.y

        bins =  np.concatenate((
            [(3*x[0] - x[1])/2],
            (x[1:] + x[:-1])/2,
            [(3*x[-1] - x[-2])/2]
        ))
        #crop until wavenumber 100
        #and now derive a probability distribution, from which we are going to sample
        hist_dist = stats.rv_histogram((counts,bins))
        return (spe,hist_dist,index)

    @staticmethod
    def xy2embedding(x,y,xlinspace = None,remove_baseline=True,window=16):
        if xlinspace is None:
            xlinspace = StudyRaman.x4search()
        spe = rc2.spectrum.Spectrum(x=x, y=y, metadata={})
        (spe,hist_dist,index) = StudyRaman.spectra2dist(spe,xcrop = [xlinspace[0],xlinspace[-1]],remove_baseline=True,window=window)
        return (hist_dist.cdf(xlinspace),hist_dist.pdf(xlinspace))

    @staticmethod
    def h52embedding(h5,dataset="raw",xlinspace = None):
        if xlinspace is None:
            xlinspace = StudyRaman.x4search()
        x = h5[dataset][0]
        y = h5[dataset][1]
        return StudyRaman.xy2embedding(x,y,xlinspace)

    def to_solr_json(self):
        _solr = {}
        id = prefixed_uuid(self.filename)
        _solr["id"] = id
        _solr["investigation_uuid_s"] = prefixed_uuid(self.investigation)
        _solr["assay_uuid_s"] = prefixed_uuid(self.investigation)

        _solr["type_s"] = "study"
        _solr["document_uuid_s"] = id

        _solr["topcategory_s"] = self.topcategory
        _solr["endpointcategory_s"] = self.endpointcategory
        _solr["guidance_s"] = "CHARISMA"
        _solr["guidance_synonym_ss"] = ["FIX_0000058"]
        _solr["E.method_synonym_ss"] = ["FIX_0000058"]
        _solr["endpoint_s"] = "Raman spectrum"
        _solr["effectendpoint_s"] = "RAMAN_CHADA_FILE"
        _solr["effectendpoint_synonym_ss"] = ["CHMO_0000823"]
        _solr["reference_owner_s"] = self.provider
        _solr["reference_year_s"] = date.today().strftime("%Y")
        _solr["reference_s"] = self.investigation
        _solr["textValue_s"] = self.filename
        _solr["updated_s"] = date.today().strftime("%Y-%m-%d")
        _solr["E.method_s"] = self.method

        _params = self.parameters
        _params["document_uuid_s"] = id
        _params["id"] = id + "/prm"
        _params["topcategory_s"] = self.topcategory
        _params["endpointcategory_s"] = self.endpointcategory
        _params["E.method_s"] = self.method
        _params["type_s"] = "params"
        _solr["_childDocuments_"] = [_params]
        _solr["spectrum_c1024"] = self.spectrum_embedding[0]
        _solr["spectrum_p1024"] = self.spectrum_embedding[1]
        return _solr


class Substance:
    def __init__(self, name, publicname, owner_name, substance_type=None):
        self.name = name
        self.publicname = publicname
        self.owner_name = owner_name
        self.substance_type = substance_type
        self.studies = []

    def add_study(self, study):
        self.studies.append(study)

    def to_solr_json(self):
        _solr = {}
        _solr["content_hss"] = []
        _solr["dbtag_hss"] = "CRMA"
        _solr["name_hs"] = self.name
        _solr["publicname_hs"] = self.publicname
        _solr["owner_name_hs"] = self.owner_name
        _solr["substanceType_hs"] = self.substance_type
        _solr["type_s"] = "substance"
        _suuid = prefixed_uuid(self.name)

        _solr["s_uuid_hs"] = _suuid
        _solr["id"] = _suuid
        _studies = []
        _solr["SUMMARY.RESULTS_hss"] = []
        for _study in self.studies:
            _study_solr = _study.to_solr_json()
            _study_solr["s_uuid_s"] = _suuid
            _study_solr["type_s"] = "study"
            _study_solr["name_s"] = self.name
            _study_solr["publicname_s"] = self.publicname
            _study_solr["substanceType_s"] = self.substance_type
            _study_solr["owner_name_s"] = self.owner_name
            _studies.append(_study_solr)
            _summary = "{}.{}".format(
                _study.topcategory, _study.endpointcategory)
            if not (_summary in _solr["SUMMARY.RESULTS_hss"]):
                _solr["SUMMARY.RESULTS_hss"].append(_summary)
        _solr["_childDocuments_"] = _studies
        _solr["SUMMARY.REFS_hss"] = []
        _solr["SUMMARY.REFOWNERS_hss"] = []

        return _solr
