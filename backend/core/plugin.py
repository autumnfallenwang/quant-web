# core/plugin.py - API layer helpers for filtering, sorting, pagination
from typing import List, Optional, Any, Dict
from fastapi import Query

def apply_filters(items: List[Any], filters: Dict[str, Any]) -> List[Any]:
    """Apply filters to a list of items"""
    filtered_items = items
    
    for field, value in filters.items():
        if value is not None:
            filtered_items = [
                item for item in filtered_items 
                if getattr(item, field, None) == value
            ]
    
    return filtered_items

def apply_sorting(items: List[Any], sort_field: Optional[str], order: str = "desc") -> List[Any]:
    """Apply sorting to a list of items"""
    if not sort_field or not items:
        return items
        
    try:
        reverse = (order == "desc")
        return sorted(items, key=lambda x: getattr(x, sort_field, ""), reverse=reverse)
    except (AttributeError, TypeError):
        return items

def apply_pagination(items: List[Any], page: int = 1, limit: int = 50) -> Dict[str, Any]:
    """Apply pagination and return paginated response"""
    total_count = len(items)
    start_index = (page - 1) * limit
    end_index = start_index + limit
    
    paginated_items = items[start_index:end_index]
    
    return {
        "data": paginated_items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_count,
            "total_pages": (total_count + limit - 1) // limit
        }
    }

# Standard query parameters (reusable)
def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page")
):
    return {"page": page, "limit": limit}

def get_sorting_params(
    sort: Optional[str] = Query(None, description="Field to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    return {"sort": sort, "order": order}