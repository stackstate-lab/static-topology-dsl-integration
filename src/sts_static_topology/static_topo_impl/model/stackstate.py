from typing import Any, Dict, List

from schematics import Model
from schematics.transforms import blacklist
from schematics.types import (BaseType, DictType, ListType, ModelType, StringType)


class AnyType(BaseType):
    def __init__(self, **kwargs):
        super(AnyType, self).__init__(**kwargs)


class Relation(Model):
    target_id: str = StringType(required=True)
    source_id: str = StringType(required=True)
    rel_type: str = StringType(required=True, default="uses")


class ComponentProperties(Model):
    name: str = StringType(required=True)
    layer: str = StringType(default="Unknown")
    domain: str = StringType(default="Unknown")
    environment: str = StringType(default="Unknown")
    labels: List[str] = ListType(StringType(), default=[])
    identifiers: List[str] = ListType(StringType(), default=[])
    custom_properties: Dict[str, Any] = DictType(AnyType(), default={})

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


class Health(Model):
    check_state_id: str = StringType(required=True)
    name: str = StringType(required=True)
    topology_element_identifier: str = StringType(required=True)
    health_value: str = StringType(required=True, choices=['CLEAR', 'DEVIATING', 'CRITICAL'])
    message: str = StringType(default="")


class Component(Model):
    uid: str = StringType(required=True)
    component_type: str = StringType(required=True)
    properties: ComponentProperties = ModelType(ComponentProperties, required=True, default=ComponentProperties())
    relations: List[Relation] = ListType(ModelType(Relation), default=[])

    def get_name(self) -> str:
        return self.properties.name

    def set_name(self, name: str):
        self.properties.name = name

    class Options:
        roles = {"public": blacklist("relations")}
