"""Process entity relationships assembled from normalized facts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from praetor.contracts.evidence import EvidenceFact
from praetor.evidence.provenance import SYSMON_EVENT_LOG


@dataclass(frozen=True)
class ProcessEntity:
    process_guid: str
    process_name: str
    image: str
    parent_process_guid: str | None = None
    parent_process_name: str | None = None
    parent_image: str | None = None


@dataclass
class ProcessRelationshipGraph:
    entities: dict[str, ProcessEntity] = field(default_factory=dict)

    def add_entity(self, entity: ProcessEntity) -> None:
        self.entities[entity.process_guid] = entity

    def parent_of(self, process_guid: str) -> ProcessEntity | None:
        entity = self.entities.get(process_guid)
        if entity is None or not entity.parent_process_guid:
            return None
        return self.entities.get(entity.parent_process_guid)

    def children_of(self, process_guid: str) -> tuple[ProcessEntity, ...]:
        return tuple(
            entity
            for entity in self.entities.values()
            if entity.parent_process_guid == process_guid
        )


def assemble_process_relationships(
    facts: Sequence[EvidenceFact],
) -> ProcessRelationshipGraph:
    """Build parent/child process relationships from Sysmon facts."""
    graph = ProcessRelationshipGraph()
    for fact in facts:
        if fact.provenance_path != SYSMON_EVENT_LOG:
            continue
        fields = fact.normalized_fields
        process_guid = str(fields.get("process_guid") or "")
        if not process_guid:
            continue
        parent_guid = str(fields.get("parent_process_guid") or "") or None
        parent_name = str(fields.get("parent_process_name") or "") or None
        parent_image = str(fields.get("parent_image") or "") or None
        graph.add_entity(
            ProcessEntity(
                process_guid=process_guid,
                process_name=str(fields.get("process_name") or ""),
                image=str(fields.get("image") or ""),
                parent_process_guid=parent_guid,
                parent_process_name=parent_name,
                parent_image=parent_image,
            )
        )
    return graph
