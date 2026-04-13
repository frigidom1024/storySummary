"""WebSocket 消息 Schema"""
from enum import Enum
from pydantic import BaseModel, Field


class ProgressStatus(str, Enum):
    """进度状态枚举"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressType(str, Enum):
    """进度类型枚举"""
    ANALYZE = "analyze"
    MANUSCRIPT = "manuscript"


class ProgressMessage(BaseModel):
    """WebSocket 进度消息

    书籍分析和口播稿生成共用同一个 WebSocket 通道，共享同一套进度消息格式。
    """
    progress: int = Field(
        ...,
        ge=0,
        le=100,
        description="进度百分比 (0-100)"
    )
    message: str = Field(
        ...,
        description="状态描述文本"
    )
    status: ProgressStatus = Field(
        ...,
        description="状态类型: processing(进行中) / completed(已完成) / failed(失败)"
    )
    type: ProgressType = Field(
        default=ProgressType.ANALYZE,
        description="任务类型: analyze(书籍分析) / manuscript(口播稿生成)"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                # 书籍分析
                {"progress": 0, "message": "开始解析文件...", "status": "processing", "type": "analyze"},
                {"progress": 20, "message": "分章完成，共 5 个章节", "status": "processing", "type": "analyze"},
                {"progress": 50, "message": "正在分析第 3/10 章...", "status": "processing", "type": "analyze"},
                {"progress": 100, "message": "解析完成！", "status": "completed", "type": "analyze"},
                # 口播稿生成
                {"progress": 0, "message": "正在启动生成...", "status": "processing", "type": "manuscript"},
                {"progress": 50, "message": "正在生成口播稿第 3/8 章...", "status": "processing", "type": "manuscript"},
                {"progress": 100, "message": "生成完成！共 8 章", "status": "completed", "type": "manuscript"},
                # 错误状态
                {"progress": 80, "message": "错误: 第 1 章分析失败: 服务器内部错误，请稍后重试", "status": "failed", "type": "analyze"},
                {"progress": 0, "message": "生成失败: 服务器内部错误", "status": "failed", "type": "manuscript"},
            ]
        }
