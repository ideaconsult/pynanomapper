from typing import List, TypeVar, Generic
from pydantic import BaseModel
from enum import Enum
from pydantic import BaseModel

import typing
from typing import Dict, Optional, Union

 #The Optional type is used to indicate that a field can have a value of either the specified type or None.
class Value(BaseModel):
    units: Optional[str] = None
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
    topcategory: str
    category: EndpointCategory
    endpoint: str
    guideline: List[str] = None

class EffectRecord(BaseModel):
    endpoint: str
    unit: Optional[str] = None
    loQualifier: Optional[str] = None
    loValue: Optional[float] = None
    upQualifier: Optional[str] = None
    upValue: Optional[float] = None
    conditions: Dict[str, Union[str, Value]]
    textValue: Optional[str] = None
    errQualifier: Optional[str] = None
    errValue: Optional[float] = None
    idresult: Optional[int] = -1
    endpointGroup: Optional[int] = None
    endpointSynonyms: List[str] = None
    sampleID: Optional[str] = None
    def addEndpointSynonym(self, endpointSynonym: str):
        if self.endpointSynonyms is None:
            self.endpointSynonyms = []
        self.endpointSynonyms.append(endpointSynonym)

    def formatSynonyms(self, striplinks: bool) -> str:
        if self.endpointSynonyms:
            return ", ".join(self.endpointSynonyms)
        return ""

    @classmethod
    def from_dict(cls, data: dict):
        if 'conditions' in data:
            parameters = data['conditions']
            for key, value in parameters.items():
                if isinstance(value, dict):
                    parameters[key] = Value(**value)
        return cls(**data)

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

class Substance(BaseModel):
    uuid: str

class Owner(BaseModel):
    substance: Substance
    company: Company

class ProtocolApplication(BaseModel):
    uuid: str
    #reliability: Optional[ReliabilityParams]
    interpretationResult: Optional[str] = None
    interpretationCriteria: Optional[str] = None
    parameters: Dict[str, Union[str, Value]]
    citation: Optional[Citation]
    effects: List[EffectRecord]
    owner : Optional[Owner]
    protocol: Protocol
    investigation_uuid: Optional[str] = None
    assay_uuid: Optional[str] = None
    updated: Optional[str]
    @classmethod
    def from_dict(cls, data: dict):
        if 'parameters' in data:
            parameters = data['parameters']
            for key, value in parameters.items():
                if isinstance(value, dict):
                    parameters[key] = Value(**value)
        return cls(**data)

# parsed_json["substance"][0]
# s = Study(**sjson)
class Study(BaseModel):
    study: List[ProtocolApplication]

class ReferenceSubstance(BaseModel):
    i5uuid : Optional[str] = None
    uri: Optional[str] = None

class SubstanceRecord(BaseModel):
    URI : Optional[str] = None
    ownerUUID : str
    ownerName : str
    i5uuid  : str
    name : str
    publicname : Optional[str] = None
    format: Optional[str] = None
    substanceType: str
    referenceSubstance: Optional[ReferenceSubstance] = None
    # composition : List[]
    # externalIdentifiers : List[]
    study: List[ProtocolApplication]

# s = Substances(**parsed_json)
class Substances(BaseModel):
    substance: List[SubstanceRecord]
