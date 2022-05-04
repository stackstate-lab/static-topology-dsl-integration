import os
from typing import List

from stackstate_checks.base import AgentCheck, Health
from static_topo_impl.dsl.interpreter import TopologyInterpreter
from static_topo_impl.model import Component
from static_topo_impl.model import Health as ComponentHealth
from static_topo_impl.model import InstanceInfo, TopologyFactory


class Processor:
    def __init__(self, instance: InstanceInfo, agent_check: AgentCheck):
        self.agent_check = agent_check
        self.log = agent_check.log
        self.instance = instance
        self.factory = TopologyFactory()

    def process(self):
        interpreter = TopologyInterpreter(self.factory)
        for topo_dsl_file in self.instance.topo_files:
            if topo_dsl_file.endswith(".topo"):
                topo_files = [topo_dsl_file]  # Single file
            else:
                topo_files = [f for f in os.listdir(topo_dsl_file) if f.endswith(".topo")]  # Folder
            for topo_file in topo_files:
                self.log.info(f"Processing '{topo_file}'")
                model = interpreter.model_from_file(topo_file)
                interpreter.interpret(model)
        self._publish()

    def _publish(self):
        self.log.info(f"Publishing '{len(self.factory.components.values())}' components")
        self.agent_check.start_snapshot()
        components: List[Component] = self.factory.components.values()
        for c in components:
            c.properties.dedup_labels()
            c_as_dict = c.properties.to_primitive()
            self.agent_check.component(c.uid, c.component_type, c_as_dict)
        self.log.info(f"Publishing '{len(self.factory.relations)}' relations")
        for r in self.factory.relations:
            self.agent_check.relation(r.source_id, r.target_id, r.rel_type, {})
        self.agent_check.stop_snapshot()
        self._publish_health()

    def _publish_health(self):
        self.log.info(f"Synchronizing  '{len(self.factory.health)}' health states")
        self.agent_check.health.start_snapshot()
        deviating, clear, critical = 0, 0, 0
        health_instances: List[ComponentHealth] = self.factory.health.values()
        for health in health_instances:
            health_value = health.health_value
            if not isinstance(health_value, Health):
                health_value = Health[health_value]
            if health_value == Health.CLEAR:
                clear += 1
            elif health_value == Health.CRITICAL:
                critical += 1
            elif health_value == Health.DEVIATING:
                deviating += 1
            self.agent_check.health.check_state(
                health.check_state_id,
                health.name,
                health_value,
                health.topology_element_identifier,
                health.message,
            )
        self.log.info(f"Critical -> {critical}, Deviating -> {deviating}, Clear -> {clear}")
        self.agent_check.health.stop_snapshot()
