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
    entry_id = "entry_{}".format(papp.uuid)
    nx_root[entry_id] = nx.tree.NXentry()
    if not (papp.protocol is None):
        #papp.protocol.endpoint
        #papp.protocol.topcategory
        #papp.protocol.category
        #papp.protocol.guideline
        pass
    if not (papp.citation is None):
        #papp.citation.year
        #papp.citation.title
        #papp.citation.owner
        pass
    if not (papp.parameters is None):
        instrument_id = '{}/instrument'.format(entry_id)
        nx_root[instrument_id] = nx.NXinstrument();
        for prm in papp.parameters:
            value = papp.parameters[prm]
            if isinstance(value,str):
                pass
            elif isinstance(value,mx.Value):
                #tbd ranges?
                nx_root['{}/instrument/{}'.format(entry_id,prm)] = nx.NXfield(value.loValue,unit=value.unit)
    nx_root['{}/title'.format(entry_id)] = 'Nexus deco method test'
    if not (papp.owner is None):
        nx_root['{}/sample'.format(entry_id)] = nx.tree.NXsample()
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
