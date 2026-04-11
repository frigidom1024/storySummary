from fastapi import APIRouter, HTTPException, Depends
from typing import List
from src.api.schemas.book import BookCreate, BookResponse, NodesResponse, SaveNodesRequest
from src.api.schemas.user import UserResponse
from src.api.deps import get_book_service, get_node_service, get_user_service, get_current_user_id
from src.services.book_service import BookService
from src.services.node_service import NodeService
from src.models.narrative_node import NarrativeNode, StoryStructure

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=List[BookResponse])
def list_books(
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """列出当前用户的所有书籍"""
    return book_service.get_books_for_user(user_id)


@router.post("", response_model=BookResponse)
def create_book(
    request: BookCreate,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """创建书籍"""
    return book_service.create_book(user_id, request.title)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """获取书籍详情"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this book")
    return book


@router.delete("/{book_id}")
def delete_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """删除书籍"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this book")
    book_service.delete_book(book_id)
    return {"message": "Book deleted"}


@router.get("/{book_id}/nodes", response_model=NodesResponse)
def get_nodes(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service),
    node_service: NodeService = Depends(get_node_service)
):
    """获取书籍的节点"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this book")

    nodes = node_service.get_nodes(book_id)
    structure = node_service.get_structure(book_id)
    return NodesResponse(
        book_id=book_id,
        structure=structure.model_dump() if structure else None,
        nodes=[n.to_dict() for n in nodes]
    )


@router.post("/{book_id}/nodes")
def save_nodes(
    book_id: str,
    request: SaveNodesRequest,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service),
    node_service: NodeService = Depends(get_node_service)
):
    """保存节点到书籍"""
    book = book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this book")

    # 更新书籍状态为 processing
    book_service.update_book_status(book_id, "processing")

    # 将 dict 转换为 NarrativeNode 对象
    nodes = [NarrativeNode.model_validate(n) for n in request.nodes]
    structure = StoryStructure.model_validate(request.structure) if request.structure else None

    # 保存节点
    node_service.save_nodes(book_id, nodes, structure)

    # 更新状态为 completed
    book_service.update_book_status(book_id, "completed")

    return {"message": "Nodes saved", "book_id": book_id}
