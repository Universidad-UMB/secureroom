"""Room repository layer."""

from abc import ABC, abstractmethod
from typing import List, Optional
import threading
import uuid

from app.rooms.models import Room


class RoomRepository(ABC):
    @abstractmethod
    def get_by_id(self, room_id: uuid.UUID) -> Optional[Room]:
        pass

    @abstractmethod
    def list_all(self) -> List[Room]:
        pass

    @abstractmethod
    def list_active(self) -> List[Room]:
        pass

    @abstractmethod
    def create(self, room: Room) -> Room:
        pass

    @abstractmethod
    def update(self, room: Room) -> Room:
        pass


class SQLAlchemyRoomRepository(RoomRepository):
    def __init__(self, db_session):
        self.db = db_session

    def get_by_id(self, room_id: uuid.UUID) -> Optional[Room]:
        return self.db.query(Room).filter(Room.id == room_id).first()

    def list_all(self) -> List[Room]:
        return self.db.query(Room).order_by(Room.name.asc()).all()

    def list_active(self) -> List[Room]:
        return self.db.query(Room).filter(Room.is_active == True).order_by(Room.name.asc()).all()

    def create(self, room: Room) -> Room:
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def update(self, room: Room) -> Room:
        self.db.commit()
        self.db.refresh(room)
        return room


class InMemoryRoomRepository(RoomRepository):
    def __init__(self):
        self._lock = threading.Lock()
        self._rooms = {}

    def get_by_id(self, room_id: uuid.UUID) -> Optional[Room]:
        with self._lock:
            return self._rooms.get(room_id)

    def list_all(self) -> List[Room]:
        with self._lock:
            return sorted(list(self._rooms.values()), key=lambda r: r.name.lower())

    def list_active(self) -> List[Room]:
        with self._lock:
            return sorted(
                [r for r in self._rooms.values() if r.is_active],
                key=lambda r: r.name.lower(),
            )

    def create(self, room: Room) -> Room:
        with self._lock:
            if room.id is None:
                room.id = uuid.uuid4()
            self._rooms[room.id] = room
            return room

    def update(self, room: Room) -> Room:
        with self._lock:
            self._rooms[room.id] = room
            return room

    def clear(self):
        with self._lock:
            self._rooms.clear()


in_memory_room_repo = InMemoryRoomRepository()
