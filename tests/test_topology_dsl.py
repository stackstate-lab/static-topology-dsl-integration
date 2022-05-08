from static_topo_impl.dsl.interpreter import TopologyInterpreter
from static_topo_impl.model.factory import TopologyFactory


def test_topology_dsl():
    topo_factory = TopologyFactory()
    interpreter = TopologyInterpreter(topo_factory)
    model = interpreter.model_from_file("tests/resources/conf.d/static_topology_dsl.d/sample.topo")
    factory = interpreter.interpret(model)
    assert len(factory.components.keys()) == 3
