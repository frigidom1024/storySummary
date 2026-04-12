from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
import os
import uuid
import tempfile
from src.api.schemas.book import BookCreate, BookResponse, NodesResponse, SaveNodesRequest
from src.api.schemas.user import UserResponse
from src.api.deps import get_book_service, get_node_service, get_user_service, get_current_user_id
from src.services.book_service import BookService
from src.services.node_service import NodeService
from src.models.narrative_node import NarrativeNode
from src.models.story_structure import StoryStructure
from src.services.epub_parser import parse_epub

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/upload", response_model=BookResponse, status_code=201)
async def upload_book(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    publisher: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """上传 epub 或 txt 文件创建书籍。"""
    # 文件类型检查
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    filename = file.filename
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    if ext not in ('epub', 'txt'):
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持 epub 和 txt")

    # 读取文件内容
    file_bytes = await file.read()

    # 文件大小检查 (50MB)
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件大小超过 50MB")

    # 解析元数据
    book_title = title or ''
    book_author = author
    book_publisher = publisher
    cover_image = None
    cover_extension = None

    if ext == 'epub':
        try:
            # 保存文件到临时路径以便 ebooklib 读取
            tmp_path = tempfile.NamedTemporaryFile(suffix='.epub', delete=False)
            tmp_path.write(file_bytes)
            tmp_path.close()

            book_epub = parse_epub(file_bytes)

            # 提取 title
            book_title = title or book_epub.title or '未知书名'

            # 提取 author
            if book_epub.author:
                book_author = author or book_epub.author

            # 提取 publisher
            if book_epub.publisher:
                book_publisher = publisher or book_epub.publisher

            # 提取封面
            cover_image = book_epub.cover_image
            cover_extension = book_epub.cover_extension

            # 清理临时文件
            os.unlink(tmp_path.name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"epub 文件格式错误: {e}")
    else:
        # txt 编码检测
        for encoding in ('utf-8', 'gbk', 'gb2312'):
            try:
                file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="无法解析文本编码，请使用 UTF-8、GBK 或 GB2312 编码")
        book_title = title or ''

    # 生成 book_id 和路径
    book_id = str(uuid.uuid4())
    nodes_file_path = f"data/books/{book_id}"

    # 保存封面
    cover_url = None
    if cover_image and cover_extension:
        covers_dir = "data/covers"
        os.makedirs(covers_dir, exist_ok=True)
        cover_path = os.path.join(covers_dir, f"{book_id}.{cover_extension}")
        with open(cover_path, 'wb') as f:
            f.write(cover_image)
        cover_url = f"/api/covers/{book_id}.{cover_extension}"

    # 创建书籍记录
    new_book = book_service.create_book_object(
        user_id=user_id,
        title=book_title,
        author=book_author,
        publisher=book_publisher,
        cover_url=cover_url,
        nodes_file_path=nodes_file_path
    )

    return BookResponse.model_validate(new_book)


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
