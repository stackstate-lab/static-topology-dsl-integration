from datetime import datetime
from typing import Any, Dict, List

import pytz
from schematics import Model
from schematics.transforms import blacklist, wholelist
from schematics.types import (BaseType, DictType, ListType, ModelType,
                              StringType)
from schematics.types import TimestampType as DefaultTimestampType
from schematics.types import URLType


class AnyType(BaseType):
    def __init__(self, **kwargs):
        super(AnyType, self).__init__(**kwargs)


class TimestampType(DefaultTimestampType):
    def to_primitive(self, value, context=None):
        value.astimezone(pytz.UTC)
        return int(round(value.timestamp()))  # seconds


class ComponentType(Model):
    name: str = StringType(required=True)

    class Options:
        roles = {"public": wholelist()}


class Relation(Model):
    external_id: str = StringType(required=True, serialized_name="externalId")
    relation_type: ComponentType = ModelType(ComponentType, serialized_name="type")
    source_id: str = StringType(required=True, serialized_name="sourceId")
    target_id: str = StringType(required=True, serialized_name="targetId")
    properties: Dict[str, Any] = DictType(AnyType(), required=True, default={"labels": []}, serialized_name="data")

    class Options:
        roles = {"public": wholelist()}

    def set_type(self, name: str):
        if self.relation_type is None:
            self.relation_type = ComponentType({"name": name})
        else:
            self.relation_type.name = name

    def get_type(self) -> str:
        if self.relation_type is None:
            return ""
        else:
            return self.relation_type.name


class ComponentProperties(Model):
    name: str = StringType(required=True)
    layer: str = StringType(default="Unknown")
    domain: str = StringType(default="Unknown")
    environment: str = StringType(default="Unknown")
    labels: List[str] = ListType(StringType(), default=[])
    identifiers: List[str] = ListType(StringType(), default=[])
    custom_properties: Dict[str, Any] = DictType(AnyType(), default={})

    class Options:
        roles = {"public": wholelist()}

    def add_label(self, label: str):
        self.labels.append(label)

    def add_label_kv(self, key: str, value: str):
        self.labels.append(f"{key}:{value}")

    def add_identifier(self, identifier: str):
        if identifier not in self.identifiers:
            self.identifiers.append(identifier)

    def update_properties(self, properties: Dict[str, Any]):
        self.custom_properties.update(properties)

    def add_property(self, name: str, value: Any):
        self.custom_properties[name] = value

    def get_property(self, name: str):
        return self.custom_properties[name]

    def dedup_labels(self):
        labels = set(self.labels)
        self.labels = list(labels)


class Component(Model):
    uid: str = StringType(required=True, serialized_name="externalId")
    component_type: ComponentType = ModelType(ComponentType, serialized_name="type")
    properties: ComponentProperties = ModelType(
        ComponentProperties, required=True, default=ComponentProperties(), serialized_name="data"
    )
    relations: List[Relation] = ListType(ModelType(Relation), default=[])

    class Options:
        roles = {"public": blacklist("relations")}

    def set_type(self, name: str):
        if self.component_type is None:
            self.component_type = ComponentType({"name": name})
        else:
            self.component_type.name = name

    def get_type(self) -> str:
        return self.component_type.name

    def get_name(self) -> str:
        return self.properties.name

    def set_name(self, name: str):
        self.properties.name = name


class HealthCheckState(Model):
    check_id: str = StringType(required=True, serialized_name="checkStateId")
    check_name: str = StringType(required=True, serialized_name="name")
    topo_identifier: str = StringType(required=True, serialized_name="topologyElementIdentifier")
    message: str = StringType(required=False)
    health: str = StringType(required=True, choices=["CLEAR", "DEVIATING", "CRITICAL"])

    class Options:
        roles = {"public": wholelist()}


class SourceLink(Model):
    title = StringType(required=True)
    url = URLType(fqdn=False, required=True)

    class Options:
        roles = {"public": wholelist()}


class EventContext(Model):
    category: str = StringType(required=True, choices=["Activities", "Alerts", "Anomalies", "Changes", "Others"])
    data: Dict[str, Any] = DictType(AnyType, default={})
    element_identifiers: List[str] = ListType(StringType, required=False, default=[])
    source: str = StringType(required=True, default="StaticTopology")
    source_links: List[SourceLink] = ListType(ModelType(SourceLink), required=False, default=[])

    class Options:
        roles = {"public": wholelist()}
        serialize_when_none = False


class Event(Model):
    context: EventContext = ModelType(EventContext, required=True, default=EventContext())
    event_type: str = StringType(required=True)
    msg_title: str = StringType(required=True)
    msg_text: str = StringType(required=True)
    source_type_name: str = StringType(required=True, default="StaticTopology")
    tags: List[str] = ListType(StringType, required=False, default=[])
    timestamp: datetime = TimestampType(required=True)

    class Options:
        roles = {"public": wholelist()}
