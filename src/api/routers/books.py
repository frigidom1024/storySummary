from fastapi import APIRouter, Depends, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from typing import List, Optional
import os
import uuid
import tempfile
import asyncio
from src.api.schemas.book import BookCreate, BookResponse, NodesResponse, SaveNodesRequest
from src.api.schemas.user import UserResponse
from src.api.deps import get_book_service, get_node_service, get_user_service, get_current_user_id
from src.api.websocket import manager
from src.services.book_service import BookService
from src.services.node_service import NodeService
from src.services.analyzer import Analyzer
from src.models.narrative_node import NarrativeNode
from src.models.story_structure import StoryStructure
from src.services.epub_parser import parse_epub
from src.storage.database import Database
from src.storage.file_manager import file_manager
from src.api.exceptions import (
    NotFoundError, AuthorizationError, ValidationError,
    FileTooLargeError, UnsupportedFileTypeError, InvalidFileError, EncodingError
)
from src.logging_config import debug

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
        raise ValidationError("文件名为空")

    filename = file.filename
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    if ext not in ('epub', 'txt'):
        raise UnsupportedFileTypeError("epub, txt")

    # 读取文件内容
    file_bytes = await file.read()

    # 文件大小检查 (50MB)
    if len(file_bytes) > 50 * 1024 * 1024:
        raise FileTooLargeError()

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
            raise ValidationError(str(e))
        except Exception as e:
            raise InvalidFileError(f"epub 文件格式错误: {e}")
    else:
        # txt 编码检测
        for encoding in ('utf-8', 'gbk', 'gb2312'):
            try:
                file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise EncodingError("无法解析文本编码，请使用 UTF-8、GBK 或 GB2312 编码")
        book_title = title or ''

    # 生成 book_id
    book_id = str(uuid.uuid4())
    nodes_file_path = f"data/books/{book_id}"

    # 保存文件
    file_manager.save_book_file(book_id, file_bytes, ext)

    # 保存封面
    cover_url = file_manager.save_cover(book_id, cover_image, cover_extension) if cover_image else None

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


@router.post("/{book_id}/analyze")
async def analyze_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    book_service: BookService = Depends(get_book_service)
):
    """启动书籍 AI 解析（异步，通过 WebSocket 推送进度）"""
    import sys
    sys.stderr.write(f"[analyze_book] FUNCTION CALLED book_id={book_id}\n")
    sys.stderr.flush()
    print(f"[analyze_book] FUNCTION CALLED book_id={book_id}", file=sys.stderr, flush=True)
    debug("books", "Received analyze request for book_id={}", book_id)

    book = book_service.get_book(book_id)
    if not book:
        print(f"[analyze_book] Book NOT FOUND: {book_id}", file=sys.stderr, flush=True)
        debug("books", "Book not found: {}", book_id)
        raise NotFoundError("书籍")
    if book.user_id != user_id:
        print(f"[analyze_book] UNAUTHORIZED book_id={book_id} user_id={user_id} book.user_id={book.user_id}", file=sys.stderr, flush=True)
        debug("books", "Unauthorized access attempt for book_id={} by user_id={}", book_id, user_id)
        raise AuthorizationError("无权分析此书籍")

    # 更新状态为 processing
    print(f"[analyze_book] Updating status to processing: {book_id}", file=sys.stderr, flush=True)
    debug("books", "Updating book status to processing: {}", book_id)
    book_service.update_book_status(book_id, "processing")

    # 检查文件是否存在
    if not file_manager.book_file_exists(book_id):
        debug("books", "Book file not found for book_id={}", book_id)
        book_service.update_book_status(book_id, "failed", "书籍文件不存在，请重新上传")
        raise NotFoundError("书籍文件不存在，请重新上传")

    # 启动异步分析
    print(f"[analyze_book] Creating asyncio task for _run_analysis: {book_id}", file=sys.stderr, flush=True)
    debug("books", "Starting async analysis task for book_id={}", book_id)
    asyncio.create_task(_run_analysis(book_id))
    print(f"[analyze_book] Task created, returning response: {book_id}", file=sys.stderr, flush=True)

    return {"message": "Analysis started", "book_id": book_id}


async def _run_analysis(book_id: str):
    """Run analysis in background with progress reporting."""
    import sys
    print(f"[_run_analysis] started for book_id={book_id}", file=sys.stderr, flush=True)

    async def progress_callback(progress: int, message: str):
        print(f"[progress_callback] book_id={book_id} progress={progress} message={message}", file=sys.stderr, flush=True)
        debug("progress", "book_id={} progress={} message={}", book_id, progress, message)
        await manager.send_progress(book_id, progress, message)

    try:
        print(f"[_run_analysis] Creating Analyzer for book_id={book_id}", file=sys.stderr, flush=True)
        analyzer = Analyzer()

        # 使用 FileManager 查找文件
        book_file = file_manager.get_book_file(book_id)
        if not book_file:
            print(f"[_run_analysis] Book file NOT FOUND for book_id={book_id}", file=sys.stderr, flush=True)
            debug("books", "Book file not found for book_id={}", book_id)
            await manager.send_progress(book_id, 0, "未找到书籍文件", "failed")
            Database().update_book_status(book_id, "failed", "未找到书籍文件")
            return

        actual_path, file_type = book_file
        print(f"[_run_analysis] Found file type={file_type} path={actual_path} for book_id={book_id}", file=sys.stderr, flush=True)
        debug("books", "Found file type={} path={} for book_id={}", file_type, actual_path, book_id)
        await analyzer.analyze(book_id, actual_path, file_type, progress_callback)
    except Exception as e:
        error_msg = str(e)
        debug("books", "Analysis failed for book_id={} error={}", book_id, error_msg)
        await manager.send_progress(book_id, 0, f"解析失败: {error_msg}", "failed")
        Database().update_book_status(book_id, "failed", error_msg)


@router.websocket("/{book_id}/ws")
async def websocket_endpoint(websocket: WebSocket, book_id: str):
    """WebSocket 端点，用于接收解析进度"""
    await manager.connect(book_id, websocket)
    try:
        while True:
            # 保持连接，等待分析完成
            data = await websocket.receive_text()
            # 客户端可以发送心跳
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(book_id, websocket)


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
        raise NotFoundError("书籍")
    if book.user_id != user_id:
        raise AuthorizationError("无权访问此书籍")
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
        raise NotFoundError("书籍")
    if book.user_id != user_id:
        raise AuthorizationError("无权删除此书籍")

    # 清理文件
    file_manager.cleanup_book_data(book_id)

    # 删除数据库记录
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
        raise NotFoundError("书籍")
    if book.user_id != user_id:
        raise AuthorizationError("无权访问此书籍")

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
        raise NotFoundError("书籍")
    if book.user_id != user_id:
        raise AuthorizationError("无权修改此书籍")

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
