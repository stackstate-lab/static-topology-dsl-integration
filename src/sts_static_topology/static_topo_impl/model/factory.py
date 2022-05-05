from typing import Dict, Optional

from static_topo_impl.model.stackstate import Component, HealthCheckState, Relation


class TopologyFactory:
    def __init__(self):
        self.components: Dict[str, Component] = {}
        self.relations: Dict[str, Relation] = {}
        self.health: Dict[str, HealthCheckState] = {}

    def add_component(self, component: Component):
        if component.uid in self.components:
            raise Exception(f"Component '{component.uid}' already exists.")
        self.components[component.uid] = component

    def get_component(self, uid: str) -> Component:
        return self.components[uid]

    def get_component_by_name_and_type(
            self, component_type: str, name: str, raise_not_found: bool = True
    ) -> Optional[Component]:
        result = [c for c in self.components.values() if c.component_type == component_type and c.get_name() == name]
        if len(result) == 1:
            return result[0]
        elif len(result) == 0:
            if raise_not_found:
                raise Exception(f"Component ({component_type}, {name}) not found.")
            return None
        else:
            raise Exception(f"More than 1 result found for Component ({component_type}, {name}) search.")

    def get_component_by_name(self, name: str, raise_not_found: bool = True) -> Optional[Component]:
        result = [c for c in self.components.values() if c.get_name() == name]
        if len(result) == 1:
            return result[0]
        elif len(result) == 0:
            if raise_not_found:
                raise Exception(f"Component ({name}) not found.")
            return None
        else:
            raise Exception(f"More than 1 result found for Component ({name}) search.")

    def component_exists(self, uid: str) -> bool:
        return uid in self.components

    def add_relation(self, source_id: str, target_id: str, rel_type: str = "uses") -> Relation:
        rel_id = f"{source_id} --> {target_id}"
        if rel_id in self.relations:
            raise Exception(f"Relation '{rel_id}' already exists.")
        relation = Relation({"source_id": source_id, "target_id": target_id, "external_id": rel_id})
        relation.set_type(rel_type)
        self.relations[rel_id] = relation
        return relation
