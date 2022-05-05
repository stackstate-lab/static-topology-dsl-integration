from datetime import datetime
from typing import Any, Dict, List, Optional

from schematics import Model
from schematics.types import BooleanType, DictType, IntType, ListType, ModelType, StringType, TimestampType

from static_topo_impl.model.stackstate import Component, Relation, HealthCheckState, AnyType


class Instance(Model):
    instance_type: str = StringType(required=True, serialized_name="type")
    url: str = StringType(required=True)


class TopologySync(Model):
    start_snapshot: bool = BooleanType(default=True)
    stop_snapshot: bool = BooleanType(default=True)
    instance: Instance = ModelType(Instance, required=True)
    delete_ids: List[str] = ListType(StringType(), default=[])
    components: List[Component] = ListType(ModelType(Component), default=[])
    relations: List[Relation] = ListType(ModelType(Relation), default=[])


class HealthSyncStartSnapshot(Model):
    expiry_interval_s: int = IntType(required=True, default=3600)  # 1 Hour
    repeat_interval_s: int = IntType(required=True, default=1800)  # 30 Minutes


class HealthStream(Model):
    urn: str = StringType(required=True)
    sub_stream_id: str = StringType()


class HealthSync(Model):
    start_snapshot: HealthSyncStartSnapshot = ModelType(HealthSyncStartSnapshot, required=True)
    stop_snapshot: Dict[str, Any] = DictType(AnyType, required=True, default={})
    stream: HealthStream = ModelType(HealthStream, required=True)
    check_states: List[HealthCheckState] = ListType(ModelType(HealthCheckState), default=[])


class ReceiverApi(Model):
    apiKey: str = StringType(required=True)
    collection_timestamp: datetime = TimestampType(required=True)
    internal_hostname: str = StringType(required=True, serialized_name="internalHostname")
    events: Dict[str, Any] = DictType(AnyType(), default={})
    metrics: List[Any] = ListType(AnyType(), default=[])
    service_checks: List[Any] = ListType(AnyType(), default=[])
    health: List[HealthSync] = ListType(ModelType(HealthSync), default=[])
    topologies: List[TopologySync] = ListType(ModelType(TopologySync), default=[])


class SyncStats(Model):
    components: int = IntType()
    relations: int = IntType()
    checks: int = IntType()
    payload: Optional[str] = StringType()
