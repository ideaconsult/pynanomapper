import ramanchada2 as rc2
import matplotlib.pyplot as plt
import pynanomapper.datamodel.ambit as mx
import numpy as np
from typing import Dict, Optional, Union, List
from pynanomapper.datamodel.nexus_utils import to_nexus
import numpy.typing as npt
import json
import nexusformat.nexus.tree as nx
import pprint
import uuid


def spe2effect(x: npt.NDArray, y: npt.NDArray):
    data_dict: Dict[str, mx.ValueArray] = {
        'x': mx.ValueArray(values = x, unit="cm-1")
    }
    return mx.EffectArray(endpoint="Raman spectrum",
                                    signal = mx.ValueArray(values = y,unit="count"),
                                    axes = data_dict)

def configure_papp(papp: mx.ProtocolApplication,
              instrument=None, wavelength=None, provider="FNMT",
              sample = "PST",
              sample_provider = "CHARISMA",
              investigation="Round Robin 1",
              prefix="CRMA"):
    papp.citation = mx.Citation(owner=provider,title=investigation,year=2022)
    papp.investigation_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID,investigation))
    papp.assay_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID,"{} {}".format(investigation,provider)))
    papp.parameters = {"E.method" : "Raman spectrometry" ,
                       "wavelength" : wavelength,
                       "T.instrument_model" : instrument
                }

    papp.uuid = "{}-{}".format(prefix,uuid.uuid5(uuid.NAMESPACE_OID,"RAMAN {} {} {} {} {} {}".format(
                "" if investigation is None else investigation,
                "" if sample_provider is None else sample_provider,
                "" if sample is None else sample,
                "" if provider is None else provider,
                "" if instrument is None else instrument,
                "" if wavelength is None else wavelength)))
    company=mx.Company(name = sample_provider)
    substance = mx.Sample(uuid = "{}-{}".format(prefix,uuid.uuid5(uuid.NAMESPACE_OID,sample)))
    papp.owner = mx.SampleLink(substance = substance,company=company)

def spe2ambit(x: npt.NDArray, y: npt.NDArray, meta: Dict,
              instrument=None, wavelength=None,
              provider="FNMT",
              investigation="Round Robin 1",
              sample = "PST",
              sample_provider = "CHARISMA",
              prefix="CRMA"):
    effect_list: List[Union[mx.EffectRecord,mx.EffectArray]] = []

    effect_list.append(spe2effect(x,y))

    papp = mx.ProtocolApplication(protocol=mx.Protocol(topcategory="P-CHEM",
                            category=mx.EndpointCategory(code="ANALYTICAL_METHODS_SECTION")),
                            effects=effect_list)

    configure_papp(papp,
              instrument=instrument, wavelength=wavelength, provider=provider,
              sample = sample,
              sample_provider = sample_provider,
              investigation=investigation,
              prefix=prefix)
    return papp
