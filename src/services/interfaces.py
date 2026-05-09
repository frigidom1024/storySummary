from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.user import User
from src.models.book import Book
from src.models.narrative_node import NarrativeNode
from src.models.story_structure import StoryStructure


class IUserService(ABC):
    @abstractmethod
    def create_user(self, username: str, email: str, password: str) -> User: ...

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[User]: ...

    @abstractmethod
    def authenticate(self, username: str, password: str) -> Optional[User]: ...

    @abstractmethod
    def update_profile(self, user_id: str, profile: dict) -> User: ...


class IBookService(ABC):
    @abstractmethod
    def create_book(self, user_id: str, title: str) -> Book: ...

    @abstractmethod
    def get_book(self, book_id: str) -> Optional[Book]: ...

    @abstractmethod
    def get_books_for_user(self, user_id: str) -> List[Book]: ...

    @abstractmethod
    def update_book_status(self, book_id: str, status: str) -> Book: ...

    @abstractmethod
    def delete_book(self, book_id: str) -> None: ...

    async def process_file(self, book_path: str, user_id: str = "default-user") -> dict: ...


class INodeService(ABC):
    @abstractmethod
    def save_nodes(self, book_id: str, nodes: List[NarrativeNode], structure: StoryStructure) -> None: ...

    @abstractmethod
    def get_nodes(self, book_id: str) -> List[NarrativeNode]: ...

    @abstractmethod
    def get_node(self, book_id: str, node_id: str) -> Optional[NarrativeNode]: ...

    @abstractmethod
    def get_structure(self, book_id: str) -> Optional[StoryStructure]: ...