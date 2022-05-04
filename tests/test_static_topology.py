from static_topology_dsl import StaticTopologyDslCheck
from static_topo_impl.model.instance import InstanceInfo
from stackstate_checks.stubs import topology
import yaml
from typing import List, Dict, Any
import logging

logging.basicConfig()
logging.getLogger("stackstate_checks.base.checks.base.static_topology_dsl").setLevel(logging.INFO)


def test_static_topology():

    topology.reset()
    instance_dict = setup_test_instance()
    instance = InstanceInfo(instance_dict)
    instance.validate()

    check = StaticTopologyDslCheck("static", {}, {}, instances=[instance_dict])
    check._init_health_api()
    check.check(instance)

    snapshot = topology.get_snapshot("")
    components = snapshot["components"]
    relations = snapshot["relations"]
    host_id = "urn:host:test"
    host2_id = "test2"
    host3_id = "test3"
    assert len(components) == 3
    assert_component(components, host_id)
    assert_component(components, host2_id)
    assert_component(components, host3_id)
    assert len(relations) == 2
    assert_relation(relations, host_id, host2_id)
    assert_relation(relations, host_id, host3_id)


def setup_test_instance() -> Dict[str, Any]:
    with open("tests/resources/conf.d/static_topology_dsl.d/conf.yaml.example") as f:
        config = yaml.load(f)
        instance = config["instances"][0]
    return instance


def assert_component(components: List[dict], cid: str) -> Dict[str, Any]:
    component = next(iter(filter(lambda item: (item["id"] == cid), components)), None)
    assert component is not None
    return component


def assert_relation(relations: List[dict], sid: str, tid: str) -> Dict[str, Any]:
    relation = next(
        iter(
            filter(
                # fmt: off
                lambda item: item["source_id"] == sid and item["target_id"] == tid,
                # fmt: on
                relations,
            )
        ),
        None,
    )
    assert relation is not None
    return relation
