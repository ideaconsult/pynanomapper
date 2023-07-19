from typing import List, TypeVar, Generic
from pydantic import BaseModel, create_model
from enum import Enum

import typing
from typing import Dict, Optional, Union
import json

 #The Optional type is used to indicate that a field can have a value of either the specified type or None.
class Value(BaseModel):
    unit: Optional[str] = None
    loValue: Optional[float] = None
    upValue: Optional[float] = None
    loQualifier: Optional[str] = None
    upQualifier: Optional[str] = None
    annotation: Optional[str] = None
    errQualifier: Optional[str] = None
    errValue: Optional[float] = None

class EndpointCategory(BaseModel):
    code: str
    term: Optional[str]
    title: Optional[str]

class Protocol(BaseModel):
    topcategory: Optional[str] = None
    category: Optional[EndpointCategory] = None
    endpoint: Optional[str] = None
    guideline: List[str] = None

class EffectResults(BaseModel):
    loQualifier: Optional[str] = None
    loValue: Optional[float] = None
    upQualifier: Optional[str] = None
    upValue: Optional[float] = None
    textValue: Optional[str] = None
    errQualifier: Optional[str] = None
    errValue: Optional[float] = None

class EffectRecord(BaseModel):
    endpoint: str
    endpointtype: Optional[str] = None
    unit: Optional[str] = None
    result: EffectResults = None
    conditions: Optional[Dict[str, Union[str, Value, None]]] = None
    idresult: Optional[int] = None
    endpointGroup: Optional[int] = None
    endpointSynonyms: List[str] = None
    sampleID: Optional[str] = None

    @classmethod
    def create(cls, endpoint: str = None, conditions: Dict[str, Union[str, Value, None]] = None):
        if conditions is None:
            conditions = {}
        return cls(endpoint=endpoint, conditions=conditions)

    def addEndpointSynonym(self, endpointSynonym: str):
        if self.endpointSynonyms is None:
            self.endpointSynonyms = []
        self.endpointSynonyms.append(endpointSynonym)

    def formatSynonyms(self, striplinks: bool) -> str:
        if self.endpointSynonyms:
            return ", ".join(self.endpointSynonyms)
        return ""

    def to_json(self):
        def effect_record_encoder(obj):
            if isinstance(obj, List):
                return [item.__dict__ for item in obj]
            return obj

        return json.dumps(self.__dict__, default=effect_record_encoder)


    @classmethod
    def from_dict(cls, data: dict):
        if 'conditions' in data:
            parameters = data['conditions']
            for key, value in parameters.items():
                if isinstance(value, dict):
                    parameters[key] = Value(**value)
        return cls(**data)

    class Config:
        allow_population_by_field_name = True

EffectRecord = create_model('EffectRecord', __base__=EffectRecord)

class ProtocolEffectRecord(EffectRecord):
    protocol: Protocol
    documentUUID: str
    studyResultType: Optional[str] = None
    interpretationResult: Optional[str] = None


class STRUC_TYPE(str, Enum):
    NA = 'NA'
    MARKUSH = 'MARKUSH'
    D1 = 'SMILES'
    D2noH = '2D no H'
    D2withH = '2D with H'
    D3noH = '3D no H'
    D3withH = '3D with H'
    optimized = 'optimized'
    experimental = 'experimental'
    NANO = 'NANO'
    PDB = 'PDB'



class ReliabilityParams(BaseModel):
    r_isRobustStudy: Optional[str] = None
    r_isUsedforClassification: Optional[str] = None
    r_isUsedforMSDS: Optional[str] = None
    r_purposeFlag: Optional[str] = None
    r_studyResultType: Optional[str] = None
    r_value: Optional[str] = None

class Citation(BaseModel):
    year: Optional[str] = None
    title: str
    owner: str

class Company(BaseModel):
    uuid: Optional[str] = None
    name: str

class Sample(BaseModel):
    uuid: str

class SampleLink(BaseModel):
    substance: Sample
    company: Company = Company(name="Default company")

    class Config:
        allow_population_by_field_name = True


class ProtocolApplication(BaseModel):
    uuid: Optional[str] = None
    #reliability: Optional[ReliabilityParams]
    interpretationResult: Optional[str] = None
    interpretationCriteria: Optional[str] = None
    parameters: Optional[Dict[str, Union[str, Value, None]]] = None
    citation: Optional[Citation]
    effects: List[EffectRecord]
    owner : Optional[SampleLink]
    protocol: Optional[Protocol] = None
    investigation_uuid: Optional[str] = None
    assay_uuid: Optional[str] = None
    updated: Optional[str]

    class Config:
        allow_population_by_field_name = True

    @classmethod
    def create(cls,  protocol: Protocol = None , effects: List[EffectRecord] = None,**kwargs):
        if protocol is None:
            protocol = Protocol()
        if effects is None:
            effects = []
        return cls(protocol = protocol,effects=effects, **kwargs)

    @classmethod
    def from_dict(cls, data: dict):
        if 'parameters' in data:
            parameters = data['parameters']
            for key, value in parameters.items():
                if isinstance(value, dict):
                    parameters[key] = Value(**value)
        return cls(**data)

    def to_json(self):
        def protocol_application_encoder(obj):
            if isinstance(obj, Value):
                return obj.__dict__
            return obj

        return json.dumps(self.__dict__, default=protocol_application_encoder)

ProtocolApplication = create_model('ProtocolApplication', __base__=ProtocolApplication)

# parsed_json["substance"][0]
# s = Study(**sjson)
class Study(BaseModel):
    """
    Example:
        # Creating an instance of Substances, with studies
        # Parse json retrieved from AMBIT services
        from  pynanomapper.datamodel.measurements import Study
        import requests
        url = https://apps.ideaconsult.net/gracious/substance/GRCS-7bd6de68-a312-3254-8b3f-9f46d6976ce6/study?media=application/json
        response = requests.get(url)
        parsed_json = response.json()
        papps = Study(**parsed_json)
        for papp in papps:
            print(papp)
    """
    study: List[ProtocolApplication]

class ReferenceSubstance(BaseModel):
    i5uuid : Optional[str] = None
    uri: Optional[str] = None

class SubstanceRecord(BaseModel):
    URI : Optional[str] = None
    ownerUUID : Optional[str] = None
    ownerName : Optional[str] = None
    i5uuid  : Optional[str] = None
    name : str
    publicname : Optional[str] = None
    format: Optional[str] = None
    substanceType: Optional[str] = None
    referenceSubstance: Optional[ReferenceSubstance] = None
    # composition : List[]
    # externalIdentifiers : List[]
    study: Optional[List[ProtocolApplication]] = None

    def to_json(self):
        def substance_record_encoder(obj):
            if isinstance(obj, List):
                return [item.__dict__ for item in obj]
            return obj.__dict__

        return json.dumps(self, default=substance_record_encoder)

# s = Substances(**parsed_json)

class Substances(BaseModel):
    """
    Example:
        # Creating an instance of Substances, with studies
        # Parse json retrieved from AMBIT services
        from  pynanomapper.datamodel.measurements import Substances
        _p = Substances(**parsed_json)
        for substance in _p.substance:
            papps = substance.study
            for papp in papps:
                print(papp.protocol)
                print(papp.parameters)
                for e in papp.effects:
                    print(e)

    """
    substance: List[SubstanceRecord]
    def to_json(self):
        def substances_encoder(obj):
            if isinstance(obj, Substances):
                return obj.substance
            return obj.__dict__

        return json.dumps(self, default=substances_encoder)
