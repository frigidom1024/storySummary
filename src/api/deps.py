from typing import Generator
from src.storage.database import Database
from src.storage.path_builder import PathBuilder
from src.storage.json_storage import JsonStorage
from src.services.user_service import UserService
from src.services.book_service import BookService
from src.services.node_service import NodeService

# 全局实例（单例模式）
_db = None
_path_builder = None
_json_storage = None
_user_service = None
_book_service = None
_node_service = None


def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database("data/story_summary.db")
    return _db


def get_path_builder() -> PathBuilder:
    global _path_builder
    if _path_builder is None:
        _path_builder = PathBuilder("data")
    return _path_builder


def get_json_storage() -> JsonStorage:
    global _json_storage
    if _json_storage is None:
        _json_storage = JsonStorage()
    return _json_storage


def get_user_service() -> UserService:
    global _user_service
    if _user_service is None:
        _user_service = UserService(get_database())
    return _user_service


def get_book_service() -> BookService:
    global _book_service
    if _book_service is None:
        _book_service = BookService(get_database(), get_path_builder())
    return _book_service


def get_node_service() -> NodeService:
    global _node_service
    if _node_service is None:
        _node_service = NodeService(get_database(), get_json_storage())
    return _node_service
