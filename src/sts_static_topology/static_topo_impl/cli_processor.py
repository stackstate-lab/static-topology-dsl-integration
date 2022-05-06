import logging
import os

from static_topo_impl.dsl.interpreter import TopologyInterpreter
from static_topo_impl.model.factory import TopologyFactory
from static_topo_impl.model.instance import Configuration
from static_topo_impl.model.stackstate_receiver import SyncStats
from static_topo_impl.stackstate import StackStateClient


class CliProcessor:
    def __init__(self, config: Configuration):
        self.config = config
        self.stackstate: StackStateClient = StackStateClient(config.stackstate)
        self.factory: TopologyFactory = TopologyFactory()

    def run(self, dry_run=False) -> SyncStats:
        interpreter = TopologyInterpreter(self.factory)
        for topo_dsl_file in self.config.topo_files:
            if topo_dsl_file.endswith(".topo"):
                topo_files = [topo_dsl_file]  # Single file
            else:
                topo_files = [os.path.join(topo_dsl_file, f) for f in os.listdir(topo_dsl_file) if f.endswith(".topo")]
            for topo_file in topo_files:
                logging.info(f"Processing '{topo_file}'")
                model = interpreter.model_from_file(topo_file)
                interpreter.interpret(model)

        stats = self.stackstate.publish(
            list(self.factory.components.values()), list(self.factory.relations.values()), dry_run
        )
        return self.stackstate.publish_health_checks(list(self.factory.health.values()), dry_run=dry_run, stats=stats)
