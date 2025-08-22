from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from app.models.base import IdentifiableModel

T = TypeVar('T', bound=IdentifiableModel)


class BaseRepository(ABC, Generic[T]):
    """Base repository interface following Repository pattern"""
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        pass
    
    @abstractmethod
    async def list_all(self) -> List[T]:
        """List all entities"""
        pass

