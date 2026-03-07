from typing import Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
  status_code: int
  message: str
  result_data: Optional[T] = None