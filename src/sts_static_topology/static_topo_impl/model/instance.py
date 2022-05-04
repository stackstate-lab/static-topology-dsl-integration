from typing import List

from schematics import Model
from schematics.types import IntType, ListType, StringType


class InstanceInfo(Model):
    instance_url: str = StringType(required=True)
    instance_type: str = StringType(default="static_topo_dsl")
    min_collection_interval: int = IntType(default=300)
    topo_files: List[str] = ListType(StringType(), default=[])
