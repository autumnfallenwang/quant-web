# core/plugin.py
from typing import Any, List, Optional, Type

from fastapi import HTTPException
from pydantic import BaseModel

def filter_response_fields(
    items: List[Any],
    fields: Optional[str] = None,
    model_class: Optional[Type[BaseModel]] = None
) -> List[dict]:
    """
    Reusable helper to:
      - Validate and convert raw ORM objects to Pydantic models
      - Filter response fields if 'fields' query param is used
    """
    # Validate and convert to Pydantic models if needed
    models = [
        model_class.model_validate(item) if not isinstance(item, BaseModel) else item
        for item in items
    ]

    # Clean and parse the fields string
    selected_fields = [f.strip() for f in fields.split(",")] if fields else None

    if selected_fields and model_class:
        invalid_fields = [f for f in selected_fields if f not in model_class.model_fields]
        if invalid_fields:
            raise HTTPException(status_code=400, detail=f"Invalid fields: {invalid_fields}")

    result = []
    for model in models:
        item_dict = model.model_dump()
        if selected_fields:
            filtered = {k: v for k, v in item_dict.items() if k in selected_fields}
        else:
            filtered = item_dict
        result.append(filtered)

    return result