from typing import Any, Dict, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


def paginate(
    items: List[T],
    total: int,
    page: int,
    size: int,
) -> Dict[str, Any]:
    pages = (total + size - 1) // size if size > 0 else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }
