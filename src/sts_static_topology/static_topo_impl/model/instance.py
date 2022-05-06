from typing import List

from schematics import Model
from schematics.types import IntType, ListType, ModelType, StringType, URLType


# Use when running as an agent-check
class InstanceInfo(Model):
    instance_url: str = StringType(required=True)
    instance_type: str = StringType(default="static_topo_dsl")
    min_collection_interval: int = IntType(default=300)
    topo_files: List[str] = ListType(StringType(), default=[])


# Rest of configuration used when running in cli mode.
class HealthSyncSpec(Model):
    source_name: str = StringType(required=True, default="static_health")
    stream_id: str = StringType(required=True)
    expiry_interval_seconds: int = IntType(required=False, default=0)  # Never
    repeat_interval_seconds: int = IntType(required=False, default=1800)  # 30 Minutes


class StackStateSpec(Model):
    receiver_url: str = URLType(required=True)
    api_key: str = StringType(required=True)
    instance_type: str = StringType()
    instance_url: str = StringType()
    health_sync: HealthSyncSpec = ModelType(HealthSyncSpec, required=False, default=None)
    internal_hostname: str = StringType(required=True, default="localhost")


class Configuration(Model):
    stackstate: StackStateSpec = ModelType(StackStateSpec, required=True)
    topo_files: List[str] = ListType(StringType(), default=[])
