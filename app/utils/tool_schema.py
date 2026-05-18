from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def build_tool_schema(
    model_class: type[BaseModel],
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    """
    Dérive l'input_schema Tool Use depuis model_class.model_json_schema().
    Filtre les computed_fields et les champs post-assignés pour éviter
    que Claude ne tente de les remplir.
    Le schéma n'est jamais écrit manuellement — toujours dérivé de Pydantic.
    """
    schema = model_class.model_json_schema()
    if exclude:
        props = schema.get("properties", {})
        for field_name in exclude:
            props.pop(field_name, None)
        schema["required"] = [f for f in schema.get("required", []) if f not in exclude]
    return schema
