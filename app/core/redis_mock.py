import asyncio
from typing import Optional, Any, Dict
import json
import time


class WatchError(Exception):
    """Mock Redis WatchError exception"""
    pass


class MockRedis:
    """Simple Redis mock for development without Redis"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
            return None
        return self._data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair"""
        self._data[key] = value
        if ex:
            self._expiry[key] = time.time() + ex
        return True
    
    async def setex(self, key: str, ex: int, value: str) -> bool:
        """Set key-value pair with expiry"""
        return await self.set(key, value, ex)
    
    async def delete(self, *keys: str) -> int:
        """Delete keys"""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                if key in self._expiry:
                    del self._expiry[key]
                count += 1
        return count
    
    async def incrby(self, key: str, amount: int = 1) -> int:
        """Increment by amount"""
        current = await self.get(key)
        if current is None:
            new_value = amount
        else:
            new_value = int(current) + amount
        await self.set(key, str(new_value))
        return new_value
    
    async def decrby(self, key: str, amount: int = 1) -> int:
        """Decrement by amount"""
        new_value = await self.incrby(key, -amount)
        # Clamp at zero to avoid negative counters
        if new_value < 0:
            await self.set(key, "0")
            return 0
        return new_value
    
    async def watch(self, *keys: str):
        """Mock watch - no-op for now"""
        pass
    
    async def multi(self):
        """Mock multi - no-op for now"""
        pass
    
    async def execute(self):
        """Mock execute - no-op for now"""
        pass
    
    async def close(self):
        """Close connection - no-op for mock"""
        pass
    
    async def ping(self) -> bool:
        """Ping - always return True for mock"""
        return True


class MockRedisPipeline:
    """Mock Redis pipeline for transactions"""
    
    def __init__(self, redis: MockRedis):
        self._redis = redis
        self._commands = []
        self._watched_keys = set()
    
    async def watch(self, *keys: str):
        """Mock watch"""
        for key in keys:
            self._watched_keys.add(key)
    
    async def multi(self):
        """Mock multi"""
        pass
    
    async def incrby(self, key: str, amount: int = 1):
        """Queue incrby command"""
        self._commands.append(('incrby', key, amount))
    
    async def execute(self):
        """Execute all commands"""
        results = []
        for cmd, *args in self._commands:
            if cmd == 'incrby':
                result = await self._redis.incrby(*args)
                results.append(result)
        self._commands.clear()
        self._watched_keys.clear()
        return results
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass


# Add pipeline method to MockRedis
MockRedis.pipeline = lambda self: MockRedisPipeline(self)
MockRedis.WatchError = WatchError

