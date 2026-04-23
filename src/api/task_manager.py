"""后台任务管理器"""
import asyncio
import logging
from typing import Callable, Coroutine, Any, Optional

logger = logging.getLogger(__name__)


class TaskManager:
    """后台任务管理器，统一管理异步任务和错误处理"""

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}

    def create_task(
        self,
        task_id: str,
        coro: Coroutine,
        on_error: Optional[Callable[[str, Exception], Any]] = None,
        on_complete: Optional[Callable[[str], Any]] = None,
    ) -> asyncio.Task:
        """创建带错误处理的任务"""

        async def wrapped():
            try:
                await coro
            except asyncio.CancelledError:
                logger.info(f"Task {task_id} was cancelled")
                raise
            except Exception as e:
                logger.exception(f"Task {task_id} failed: {e}")
                if on_error:
                    await on_error(task_id, e)
            finally:
                self._tasks.pop(task_id, None)
                if on_complete:
                    await on_complete(task_id)

        # 取消已存在的同名任务
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            logger.info(f"Cancelled existing task: {task_id}")

        task = asyncio.create_task(wrapped())
        self._tasks[task_id] = task
        logger.info(f"Created task: {task_id}, total tasks: {len(self._tasks)}")
        return task

    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务"""
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            logger.info(f"Cancelled task: {task_id}")
            return True
        return False

    def get_task(self, task_id: str) -> Optional[asyncio.Task]:
        """获取任务对象"""
        return self._tasks.get(task_id)

    def is_running(self, task_id: str) -> bool:
        """检查任务是否在运行"""
        task = self._tasks.get(task_id)
        return task is not None and not task.done()


# 全局实例
task_manager = TaskManager()
