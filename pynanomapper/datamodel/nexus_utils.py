import numpy as np
from pydantic import validate_arguments

from . import measurements as mx
from . ambit_deco import add_ambitmodel_method
import nexusformat.nexus as nx

# Usage
# from  pynanomapper.datamodel.nexus_utils import to_nexus
# from  pynanomapper.datamodel.measurements import ProtocolApplication
# pa = ProtocolApplication(**json_data)
# import nexusformat.nexus.tree as nx
# ne = pa.to_nexus(nx.NXroot())
# print(ne.tree)
@add_ambitmodel_method(mx.ProtocolApplication)
def to_nexus(papp : mx.ProtocolApplication, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    #https://manual.nexusformat.org/classes/base_classes/NXentry.html
    entry_id = "entry_{}".format(papp.uuid)
    nx_root[entry_id] = nx.tree.NXentry()
    nx_root['{}/entry_identifier_uuid'.format(entry_id)] = papp.uuid

    nx_root['{}/definition'.format(entry_id)] = papp.__class__.__name__
    #experiment_identifier
    #experiment_description
    #collection_identifier collection of related measurements or experiments.
    nx_root['{}/collection_identifier'.format(entry_id)] = papp.investigation_uuid
    nx_root['{}/experiment_identifier'.format(entry_id)] = papp.assay_uuid
    #collection_description

    #duration
    #program_name
    #revision
    #experiment_documentation (SOP)
    #notes
    #USER: (optional) NXuser
    #SAMPLE: (optional) NXsample
    #INSTRUMENT: (optional) NXinstrument
    #COLLECTION: (optional) NXcollection
    #MONITOR: (optional) NXmonitor
    #PARAMETERS: (optional) NXparameters Container for parameters, usually used in processing or analysis.
    #PROCESS: (optional) NXprocess
    #SUBENTRY: (optional) NXsubentry Group of multiple application definitions for “multi-modal” (e.g. SAXS/WAXS) measurements.

    if not (papp.protocol is None):
        instrument_id = '{}/protocol'.format(entry_id)
        #papp.protocol.endpoint
        #papp.protocol.topcategory
        #papp.protocol.category
        #papp.protocol.guideline
        #experiment_documentation
        experiment_documentation = nx.NXnote()
        nx_root['{}/experiment_documentation'.format(entry_id)] = experiment_documentation

        category = nx.NXgroup()
        experiment_documentation["category"] = category
        category.attrs["topcategory"] = papp.protocol.topcategory
        category.attrs["code"] = papp.protocol.category.code
        category.attrs["term"] = papp.protocol.category.term
        category.attrs["title"] = papp.protocol.category.title
        category.attrs["endpoint"] = papp.protocol.endpoint
        for guide in papp.protocol.guideline:
            experiment_documentation["guideline"] = papp.protocol.guideline
            break

    if not (papp.citation is None):
        citation_id = '{}/reference'.format(entry_id)
        nx_root[citation_id] = nx.NXcite()
        nx_root[citation_id]["title"] = papp.citation.title
        nx_root[citation_id]["year"] = papp.citation.year
        nx_root[citation_id]["owner"] = papp.citation.owner
        #url, doi, description

    if not (papp.parameters is None):
        instrument_id = '{}/instrument'.format(entry_id)
        params_id = '{}/parameters'.format(entry_id)
        env_id = '{}/environment'.format(entry_id)
        instrument = nx.NXinstrument()
        parameters = nx.NXcollection()
        environment = nx.NXenvironment()
        sample = nx.tree.NXsample()
        for prm in papp.parameters:
            value = papp.parameters[prm]
            target = environment
            if  "instrument" in prm.lower():
                target = instrument
            elif  "sample" in prm.lower():
                target = sample
            elif  "material" in prm.lower():
                target = sample
            elif ("ASSAY" == prm.upper()) or ("E.METHOD" == prm.upper()):
                target = instrument
            elif ("E.SOP_REFERENCE" == prm):
                target = instrument
            elif ("OPERATOR" == prm):
                target = instrument
            elif (prm.startswith("T.")):
                target = instrument
            if "EXPERIMENT_END_DATE" == prm:
                nx_root[entry_id]["end_time"] = value
            elif "EXPERIMENT_START_DATE" == prm:
                nx_root[entry_id]["start_time"] = value
            elif isinstance(value,str):
                target[prm] = nx.NXfield(str(value))
            elif isinstance(value,mx.Value):
                #tbd ranges?
                target[prm] = nx.NXfield(value.loValue,unit=value.unit)
        nx_root[instrument_id] = instrument
        nx_root[params_id] = parameters
        nx_root[env_id] = environment
        nx_root['{}/sample'.format(entry_id)] = sample

    if not (papp.owner is None):
        try:
            sample["uuid"] = papp.owner.substance.uuid
            sample["provider"] = papp.owner.company.name
        except:
            pass
    return nx_root


@add_ambitmodel_method(mx.Study)
def to_nexus(study : mx.Study, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    for papp in study.study:
        print(papp.uuid)
        papp.to_nexus(nx_root);
    return nx_root

@add_ambitmodel_method(mx.SubstanceRecord)
def to_nexus(substance : mx.SubstanceRecord, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    if not (substance.study is None):
        for papp in substance.study:
            papp.to_nexus(nx_root);
    return nx_root

@add_ambitmodel_method(mx.Substances)
def to_nexus(substances : mx.Substances, nx_root: nx.NXroot() = None ):
    if nx_root == None:
        nx_root = nx.NXroot()
    for substance in substances.substance:
        substance.to_nexus(nx_root);
    return nx_root
