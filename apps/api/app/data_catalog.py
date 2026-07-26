from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app import models


@dataclass(frozen=True)
class FieldDefinition:
    entity_type: models.EnrichmentEntityType
    field_name: str
    label: str
    description: str
    data_type: str
    unit: str | None
    automation_class: models.AutomationClass
    minimum: float | None = None
    maximum: float | None = None


FIELDS = (
    FieldDefinition(models.EnrichmentEntityType.COASTER, "name", "Official name", "Current public name.", "string", None, models.AutomationClass.A),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "status", "Operational status", "Current operating state.", "enum", None, models.AutomationClass.B),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "opened_on", "Public opening", "First regular public opening; excludes previews.", "date", None, models.AutomationClass.B),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "height_m", "Construction height", "Highest construction point; not the drop.", "number", "m", models.AutomationClass.B, 0, 500),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "drop_m", "Drop", "Largest vertical descent.", "number", "m", models.AutomationClass.B, 0, 500),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "speed_kmh", "Maximum speed", "Published maximum speed.", "number", "km/h", models.AutomationClass.B, 0, 500),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "length_m", "Track length", "Total track length.", "number", "m", models.AutomationClass.B, 0, 10000),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "inversions", "Inversions", "Number of intended track inversions.", "integer", None, models.AutomationClass.B, 0, 50),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "capacity_pph", "Capacity", "Theoretical riders per hour.", "integer", "pph", models.AutomationClass.B, 0, 10000),
    FieldDefinition(models.EnrichmentEntityType.COASTER, "summary", "Profile", "Neutral sourced profile text.", "text", None, models.AutomationClass.C),
    FieldDefinition(models.EnrichmentEntityType.PARK, "name", "Official name", "Current official park name.", "string", None, models.AutomationClass.A),
    FieldDefinition(models.EnrichmentEntityType.PARK, "city", "City", "Locality used by the park.", "string", None, models.AutomationClass.A),
    FieldDefinition(models.EnrichmentEntityType.PARK, "latitude", "Latitude", "WGS84 latitude.", "number", "degrees", models.AutomationClass.A, -90, 90),
    FieldDefinition(models.EnrichmentEntityType.PARK, "longitude", "Longitude", "WGS84 longitude.", "number", "degrees", models.AutomationClass.A, -180, 180),
    FieldDefinition(models.EnrichmentEntityType.PARK, "opened_on", "Public opening", "First regular public opening.", "date", None, models.AutomationClass.B),
    FieldDefinition(models.EnrichmentEntityType.PARK, "website_url", "Official website", "Current official website.", "url", None, models.AutomationClass.A),
    FieldDefinition(models.EnrichmentEntityType.PARK, "summary", "Profile", "Neutral sourced park profile.", "text", None, models.AutomationClass.C),
    FieldDefinition(models.EnrichmentEntityType.MANUFACTURER, "name", "Official name", "Current official or final company name.", "string", None, models.AutomationClass.A),
    FieldDefinition(models.EnrichmentEntityType.MANUFACTURER, "founded_year", "Founded", "Year the legal or recognized predecessor was founded.", "integer", "year", models.AutomationClass.C, 1700, 2100),
    FieldDefinition(models.EnrichmentEntityType.MANUFACTURER, "website_url", "Official website", "Current official website.", "url", None, models.AutomationClass.A),
    FieldDefinition(models.EnrichmentEntityType.MANUFACTURER, "summary", "Profile", "Neutral sourced manufacturer profile.", "text", None, models.AutomationClass.C),
)

FIELD_INDEX = {(item.entity_type, item.field_name): item for item in FIELDS}


def field_definition(
    entity_type: models.EnrichmentEntityType, field_name: str
) -> FieldDefinition | None:
    return FIELD_INDEX.get((entity_type, field_name))


def validate_value(definition: FieldDefinition, value: Any) -> bool:
    if value is None:
        return False
    if definition.data_type in {"number", "integer"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if definition.data_type == "integer" and int(value) != value:
            return False
        if definition.minimum is not None and value < definition.minimum:
            return False
        if definition.maximum is not None and value > definition.maximum:
            return False
    return True


def public_catalog() -> list[dict[str, Any]]:
    return [
        {
            "entity_type": item.entity_type.value,
            "field_name": item.field_name,
            "label": item.label,
            "description": item.description,
            "data_type": item.data_type,
            "unit": item.unit,
            "automation_class": item.automation_class.value,
            "minimum": item.minimum,
            "maximum": item.maximum,
        }
        for item in FIELDS
    ]
