from typing import Any, Dict, List

import attr
from asteval import Interpreter
from six import string_types
from static_topo_impl.model.factory import TopologyFactory
from static_topo_impl.model.stackstate import Component, Health, Relation
from textx import metamodel_from_str, textx_isinstance
from textx.metamodel import TextXMetaModel
from textx.model import TextXSyntaxError


@attr.s(kw_only=True)
class TopologyContext:
    factory: TopologyFactory = attr.ib()
    component: Component = attr.ib()


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

    def get_string_property(self, name: str, default=None) -> str:
        value = self.get_property_value(name, self.properties, self.source_name, default=None)
        if value is None:
            value = self.get_property_value(name, self.defaults, self.default_source, default=default)

        return self._assert_string(value, name, self.source_name)

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

    def run_processors(self):
        name = "processor"
        if self._is_code(name, self.properties):
            self._run_code(self.properties[name].code, name, self.source_name)
        if self._is_code(name, self.defaults):
            self._run_code(self.defaults[name].code, name, self.default_source)

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

    def model_from_file(self, model_file_name: str):
        try:
            return self.topology_meta.model_from_file(model_file_name)
        except TextXSyntaxError as e:
            raise Exception(e.message)

    def interpret(self, model) -> TopologyFactory:
        defaults: Dict[str, Any] = {}
        if hasattr(model, "defaults"):
            defaults = self._index_properties(model.defaults.properties)
        components_ast = model.components
        for component_ast in components_ast.components:
            self._interpret_component(component_ast, defaults)
        self._resolve_relations()
        return self.factory

    def _resolve_relations(self):
        components: List[Component] = self.factory.components.values()
        for source in components:
            for relation in source.relations:
                if self.factory.component_exists(relation.target_id):
                    self.factory.add_relation(relation.source_id, relation.target_id, relation.rel_type)
                else:
                    target_component = self.factory.get_component_by_name(relation.target_id, raise_not_found=False)
                    if target_component:
                        self.factory.add_relation(relation.source_id, target_component.uid, relation.rel_type)
                    else:
                        raise Exception(
                            f"Failed to find related component '{relation.target_id}'. "
                            f"Reference from component {source.uid}."
                        )

    def _interpret_component(self, component_ast, defaults):
        component = Component()
        component.component_type = component_ast.component_type
        properties = self._index_properties(component_ast.properties)
        ctx = TopologyContext(factory=self.factory, component=component)
        property_interpreter = PropertyInterpreter(
            properties, defaults, component.component_type, ctx, self.topology_meta
        )

        component.set_name(property_interpreter.get_property("name"))
        if component.get_name() is None:
            raise Exception(f"Component name is required for '{component.component_type}'.")

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
            raise Exception(
                "Component id is required for " f"'{property_interpreter.source_name}({component.component_type})'."
            )

        self._interpret_health(component, property_interpreter)
        self._interpret_relations(component, property_interpreter)
        self.factory.add_component(component)

    @staticmethod
    def _interpret_relations(component: Component, property_interpreter: PropertyInterpreter):
        relations: List[str] = property_interpreter.merge_list_property("relations")
        for relation in relations:
            rel_parts = relation.split("|")
            rel_type = "uses"
            if len(rel_parts) == 2:
                rel_type = rel_parts[1]
            component.relations.append(
                Relation({"source_id": component.uid, "target_id": rel_parts[0], "rel_type": rel_type})
            )

    def _interpret_health(self, component: Component, property_interpreter: PropertyInterpreter):
        health_info = property_interpreter.get_string_property("health", "HealthCheck|CLEAR")
        health_parts = health_info.split("|")
        health_name = "HealthCheck"
        if len(health_parts) == 2:
            health_name = health_parts[0]
            health_state = health_parts[1]
        else:
            health_state = health_parts[0]
        health_msg = property_interpreter.get_string_property("healthMessage", "")
        health = Health()
        health.name = health_name
        health.check_state_id = f"{component.get_name()}_static_states"
        health.topology_element_identifier = component.uid
        health.health_value = health_state.upper()
        health.message = health_msg
        health.validate()
        self.factory.health[health.check_state_id] = health

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
;

Defaults:
    'defaults' '{'
        properties*=Property
    '}'
;

Components:
    'components' '{'
        components*=Component
    '}'
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
     'relations' | 'healthMessage' |'health'
;

PropertyString:
    ID | STRING
;

PropertyValue:
    PropertyString | FLOAT | BOOL | PropertyObject | PropertyList | PropertyCode
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
"""
