import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import attr
from asteval import Interpreter
from six import string_types
from static_topo_impl.model.factory import TopologyFactory
from static_topo_impl.model.stackstate import (Component, Event,
                                               HealthCheckState, Relation,
                                               SourceLink)
from textx import metamodel_from_str, textx_isinstance
from textx.metamodel import TextXMetaModel
from textx.model import TextXSyntaxError


@attr.s(kw_only=True)
class TopologyContext:
    factory: TopologyFactory = attr.ib()
    repeat_index: int = attr.ib(default=0)
    component: Component = attr.ib(default=None)
    event: Event = attr.ib(default=None)


class PropertyInterpreter:
    def __init__(
            self,
            properties: Dict[str, Any],
            defaults: Dict[str, Any],
            source_name: str,
            ctx: TopologyContext,
            topology_meta: TextXMetaModel,
    ):
        self.source_name = source_name
        self.defaults = defaults
        self.properties = properties
        self.ctx = ctx
        self.topology_meta = topology_meta
        self.PropertyObjectClass = self.topology_meta["PropertyObject"]
        self.PropertyListClass = self.topology_meta["PropertyList"]
        self.PropertyCodeClass = self.topology_meta["PropertyCode"]
        self.PropertyClass = self.topology_meta["Property"]
        self.default_source = "default"

    def get_int_property(self, name: str, default=None) -> int:
        value = self.get_property_value(name, self.properties, self.source_name, default=None)
        if value is None:
            value = self.get_property_value(name, self.defaults, self.default_source, default=default)
        return self._assert_int(value, name, self.source_name)

    def get_string_property(self, name: str, default=None) -> str:
        value = self.get_property_value(name, self.properties, self.source_name, default=None)
        if value is None:
            value = self.get_property_value(name, self.defaults, self.default_source, default=default)
        return self._assert_string(value, name, self.source_name)

    def get_map_property(self, name: str, default=None) -> Dict[str, Any]:
        value = self.get_property_value(name, self.properties, self.source_name, default=default)
        return self._assert_dict(value, name, self.source_name)

    def get_list_property(self, name: str, default=None) -> List[Any]:
        value = self.get_property_value(name, self.properties, self.source_name, default=default)
        return self._assert_list(value, name, self.source_name)

    def get_property(self, name: str, default=None) -> Any:
        value = self.get_property_value(name, self.properties, self.source_name, default=None)
        if value is None:
            value = self.get_property_value(name, self.defaults, self.default_source, default=default)
        return value

    def merge_map_property(self, name: str) -> Dict[str, Any]:
        default_value = self.get_property_value(name, self.defaults, self.default_source, default={})
        self._assert_dict(default_value, name, self.default_source)
        map_value = self.get_property_value(name, self.properties, self.source_name, default=None)
        self._assert_dict(map_value, name, self.source_name)
        if map_value is None:
            return default_value
        else:
            default_value.update(map_value)
            return default_value

    def merge_list_property(self, name: str):
        default_value = self.get_property_value(name, self.defaults, self.default_source, default=[])
        self._assert_list(default_value, name, self.default_source)
        list_value = self.get_property_value(name, self.properties, self.source_name, default=None)
        self._assert_list(list_value, name, self.source_name)
        if list_value is None:
            return default_value
        else:
            list_value.extend(default_value)
            return list_value

    def run_processors(self, defaults_name="processor"):
        name = "processor"
        if self._is_code(name, self.properties):
            self._run_code(self.properties[name].code, name, self.source_name)
        if self._is_code(name, self.defaults):
            self._run_code(self.defaults[defaults_name].code, defaults_name, self.default_source)

    def get_property_value(self, name: str, properties: Dict[str, Any], source_name: str, default: Any = None) -> Any:
        value_ast = properties.get(name, default)
        return self._convert_value(value_ast, name, source_name)

    def _is_code(self, name: str, properties: Dict[str, Any]) -> bool:
        value_ast = properties.get(name, None)
        return textx_isinstance(value_ast, self.PropertyCodeClass)

    def _convert_value(self, value_ast: Any, property_name: str, source_name: str) -> Any:
        if value_ast is None:
            return None
        elif textx_isinstance(value_ast, self.PropertyObjectClass):
            value = {}
            for member in value_ast.members:
                value[member.key] = self._convert_value(member.value, property_name, source_name)
            return value
        elif textx_isinstance(value_ast, self.PropertyListClass):
            value_list = []
            for v in value_ast.values:
                value_list.append(self._convert_value(v, property_name, source_name))
            return value_list
        elif textx_isinstance(value_ast, self.PropertyCodeClass):
            return self._run_code(value_ast.code, property_name, source_name)
        else:
            return value_ast

    @staticmethod
    def _assert_string(value: Any, name: str, source_name: str) -> str:
        if value is not None:
            if not isinstance(value, string_types):
                raise Exception(f"Expected string type for '{name}', but was {type(value)} on `{source_name}`")
        return value

    @staticmethod
    def _assert_int(value: Any, name: str, source_name: str) -> int:
        if value is not None:
            try:
                return int(value)
            except Exception:
                raise Exception(f"Expected int type for '{name}', but was {type(value)} on `{source_name}`")
        else:
            value = 0
        return value

    @staticmethod
    def _assert_dict(value: Any, name: str, source_name: str) -> Dict[str, Any]:
        if value is not None:
            if not isinstance(value, dict):
                raise Exception(f"Expected dict type for '{name}', but was {type(value)} on `{source_name}`")
        return value

    @staticmethod
    def _assert_list(value: Any, name: str, source_name: str) -> List[Any]:
        if value is not None:
            if not isinstance(value, list):
                raise Exception(f"Expected list type for '{name}', but was {type(value)} on `{source_name}`")
        return value

    def _run_code(self, code: str, property_name, source_name: str) -> Any:
        aeval = self._get_asteval_interpreter(self.ctx)
        code = code.strip()
        if code.endswith("```"):
            code = code[:-3]
        code_lines = code.split("\n")
        # Fix first line indentation
        if len(code_lines) > 1:
            padding_count = 0
            second_line = code_lines[1]
            for i in range(0, len(second_line)):
                if second_line[i] != " ":
                    break
                padding_count += 1
            for i in range(1, len(code_lines)):
                code_lines[i] = code_lines[i][padding_count:]
        code = "\n".join(code_lines)
        value = self._eval_expression(code, aeval, property_name, source_name)
        return value

    @staticmethod
    def _get_asteval_interpreter(ctx: TopologyContext) -> Interpreter:
        aeval = Interpreter()
        aeval.symtable["factory"] = ctx.factory
        aeval.symtable["component"] = ctx.component
        aeval.symtable["event"] = ctx.event
        aeval.symtable["repeat_index"] = ctx.repeat_index
        return aeval

    @staticmethod
    def _eval_expression(
            expression: str, aeval: Interpreter, eval_property: str, source_name: str, fail_on_error: bool = True
    ):
        existing_errs = len(aeval.error)
        result = aeval.eval(expression)
        if len(aeval.error) > existing_errs and fail_on_error:
            error_messages = []
            for err in aeval.error:
                error_messages.append(err.get_error())
            raise Exception(
                f"Failed to evaluate property '{eval_property}' on `{source_name}`. "
                f"Expression |\n {expression} \n |.\n Errors:\n {error_messages}"
            )
        return result


class TopologyInterpreter:
    def __init__(self, factory: TopologyFactory):
        self.factory = factory
        self.topology_meta = metamodel_from_str(TOPOLOGY_TX)
        self.ElementPropertiesChangedClass = self.topology_meta["ElementPropertiesChanged"]
        self.link_pattern = re.compile("\\[([\\s\\w-]*)\\]\\((.*)\\)")

    def model_from_file(self, model_file_name: str):
        try:
            return self.topology_meta.model_from_file(model_file_name)
        except TextXSyntaxError as e:
            raise Exception(e.message)

    def interpret(self, model) -> TopologyFactory:
        defaults: Dict[str, Any] = {}
        if hasattr(model, "defaults") and model.defaults is not None:
            defaults = self._index_properties(model.defaults.properties)
        if hasattr(model, "components") and model.components is not None:
            components_ast = model.components
            for component_ast in components_ast.components:
                self._interpret_component(component_ast, defaults)
            self._resolve_relations()
        if hasattr(model, "events") and model.events is not None:
            events_ast = model.events
            for event_ast in events_ast.events:
                self._interpret_event(event_ast, defaults)

        return self.factory

    def _interpret_event(self, event_ast, defaults):
        event = Event()
        properties = self._index_properties(event_ast.properties)
        ctx = TopologyContext(factory=self.factory, event=event)
        property_interpreter = PropertyInterpreter(properties, defaults, "event", ctx, self.topology_meta)

        event.msg_title = property_interpreter.get_string_property("title", "Unknown")
        property_interpreter.source_name = f"Event with title '{event.msg_title}"
        event.msg_text = property_interpreter.get_string_property("message", "")
        event.tags.extend(property_interpreter.merge_list_property("tags"))
        event.timestamp = datetime.now()
        identifiers = property_interpreter.get_list_property("identifiers", [])
        if len(identifiers) == 0:
            raise Exception(f"Event must have at least 1 identifier '{event.msg_title}'.")
        event.context.element_identifiers = self._resolve_identifiers(identifiers)

        links = property_interpreter.get_list_property("links", [])
        for link in links:
            match = self.link_pattern.match(link)
            if not match:
                raise Exception(f"Link '{link}' must have the format '[description](url)'")
            source_link = SourceLink()
            source_link.title = match.group(1)
            source_link.url = match.group(2)
            event.context.source_links.append(source_link)

        if textx_isinstance(event_ast, self.ElementPropertiesChangedClass):
            event.context.category = "Changes"
            event.event_type = "Element Properties Changed"
            previous = property_interpreter.get_map_property("previous", {})
            current = property_interpreter.get_map_property("current", {})
            event.context.data = {"old": previous, "new": current}

        property_interpreter.run_processors(defaults_name="eventProcessor")
        self.factory.add_event(event)

    def _resolve_identifiers(self, identifiers):
        resolved_identifiers = []
        for identifier in identifiers:
            if self.factory.component_exists(identifier):
                resolved_identifiers.append(identifier)
            else:
                target_component = self.factory.get_component_by_name(identifier, raise_not_found=False)
                if target_component:
                    resolved_identifiers.append(target_component.uid)
                else:
                    # Reference to another component on StackState Server
                    resolved_identifiers.append(identifier)
        return resolved_identifiers

    def _interpret_component(self, component_ast, defaults):
        properties = self._index_properties(component_ast.properties)
        ctx = TopologyContext(factory=self.factory)
        property_interpreter = PropertyInterpreter(properties, defaults, component_ast.component_type, ctx,
                                                   self.topology_meta)

        repeat = range(0, 1)
        if "repeat" in properties:
            repeat = range(0, property_interpreter.get_int_property("repeat"))

        for index in repeat:
            component = Component()
            component.set_type(component_ast.component_type)
            ctx.component = component
            ctx.repeat_index = index
            component.set_name(property_interpreter.get_property("name"))
            if component.get_name() is None:
                raise Exception(f"Component name is required for '{component.get_type()}'.")

            property_interpreter.source_name = component.get_name()
            component.properties.update_properties(property_interpreter.merge_map_property("data"))
            component.properties.layer = property_interpreter.get_string_property("layer", "Unknown")
            component.properties.domain = property_interpreter.get_string_property("domain", "Unknown")
            component.properties.environment = property_interpreter.get_string_property("environment", "Unknown")
            component.properties.labels.extend(property_interpreter.merge_list_property("labels"))
            component.uid = property_interpreter.get_string_property("id", None)
            component.properties.identifiers.extend(property_interpreter.merge_list_property("identifiers"))
            property_interpreter.run_processors()

            if component.uid is None:
                component.uid = f"urn:{component.get_type().lower()}:{component.get_name().lower()}"

            if len(component.properties.identifiers) == 0:
                component.properties.identifiers.append(component.uid)

            self._interpret_health(component, property_interpreter)
            self._interpret_relations(component, property_interpreter)
            self.factory.add_component(component)

    def _resolve_relations(self):
        components: List[Component] = self.factory.components.values()
        for source in components:
            for relation in source.relations:
                if self.factory.component_exists(relation.target_id):
                    self.factory.add_relation(relation.source_id, relation.target_id, relation.get_type())
                else:
                    target_component = self.factory.get_component_by_name(relation.target_id, raise_not_found=False)
                    if target_component:
                        self.factory.add_relation(relation.source_id, target_component.uid, relation.get_type())
                    else:
                        raise Exception(
                            f"Failed to find related component '{relation.target_id}'. "
                            f"Reference from component {source.uid}."
                        )
            source.relations = []

    @staticmethod
    def _interpret_relations(component: Component, property_interpreter: PropertyInterpreter):
        relations: List[str] = property_interpreter.merge_list_property("relations")
        for relation in relations:
            rel_parts = relation.split("|")
            rel_type = "uses"
            if len(rel_parts) == 2:
                rel_type = rel_parts[1]
            reverse = False
            if rel_parts[0].startswith("<"):
                reverse = True
                rel_parts[0] = rel_parts[0][1:]

            if reverse:
                rel_id = f"{rel_parts[0]} --> {component.uid}"
                relation = Relation({"source_id": rel_parts[0], "target_id": component.uid, "external_id": rel_id})
            else:
                rel_id = f"{component.uid} --> {rel_parts[0]}"
                relation = Relation({"source_id": component.uid, "target_id": rel_parts[0], "external_id": rel_id})
            relation.set_type(rel_type)
            component.relations.append(relation)

    def _interpret_health(self, component: Component, property_interpreter: PropertyInterpreter):
        cid = component.uid
        if len(component.properties.identifiers) > 0 and cid not in component.properties.identifiers:
            cid = component.properties.identifiers[0]
        health_info = property_interpreter.get_string_property("health", "HealthCheck|CLEAR")
        health_parts = health_info.split("|")
        health_name = "HealthCheck"
        if len(health_parts) == 2:
            health_name = health_parts[0]
            health_state = health_parts[1]
        else:
            health_state = health_parts[0]
        health_msg = property_interpreter.get_string_property("healthMessage", "")
        health = HealthCheckState()
        health.check_name = health_name
        health.check_id = f"{component.get_name()}_static_states"
        health.topo_identifier = cid
        health.health = health_state.upper()
        health.message = health_msg
        health.validate()
        self.factory.health[health.check_id] = health

    @staticmethod
    def _index_properties(properties) -> Dict[str, Any]:
        index: Dict[str, Any] = {}
        for p in properties:
            index[p.name] = p.value
        return index


TOPOLOGY_TX = """
TopologyModel:
    defaults=Defaults?
    components=Components
    events=Events?
;

Defaults:
    'defaults' '{'
        properties*=DefaultProperty
    '}'
;

Components:
    'components' '{'
        components*=Component
    '}'
;

Events:
    'events' '{'
        events*=Event
    '}'
;

Event:
    ElementPropertiesChanged
;

ElementPropertiesChanged:
    "ElementPropertiesChanged" "(" properties*=ElementPropertiesChangedProperty ")"
;

ElementPropertiesChangedProperty:
  name=ElementPropertiesChangedPropertyKeyword value=PropertyValue
;

ElementPropertiesChangedPropertyKeyword:
     EventPropertyKeyword | 'previous' | 'current'
;

Component:
    ComponentMultiline | ComponentInline
;

ComponentMultiline:
   component_type=ComponentType "(" properties*=Property ")"
;

ComponentInline:
   component_type=ComponentType "(" properties*=Property[','] ")"
;

ComponentType:
    /[^\\d\\W][\\w.\\s]*\\b/

;

Property:
  name=PropertyKeyword value=PropertyValue
;

PropertyKeyword:
     'identifiers' | 'id' | 'name' | 'layer' | 'domain' | 'environment' | 'labels' | 'processor' | 'data' |
     'relations' | 'healthMessage' |'health' | 'repeat'
;

DefaultProperty:
  name=DefaultPropertyKeyword value=PropertyValue
;

DefaultPropertyKeyword:
     PropertyKeyword | 'eventProcessor' | 'tags'
;

EventPropertyKeyword:
     'title' | 'message' | 'identifiers' | 'tags' | 'links' | 'processor'
;

PropertyString:
    ID | STRING
;

PropertyValue:
    PropertyString | FLOAT | INT | BOOL | PropertyObject | PropertyList | PropertyCode
;

PropertyList:
    '[' values*=PropertyValue[','] ']'
;

PropertyObject:
    "{" members*=PropertyMember[','] "}"
;

PropertyCode:
   "```" code=/(?ms)(.*?)[`]{3}/
;

PropertyMember:
    key=ID  value=PropertyValue
;

Comment:
  /#.*$/
;
"""
