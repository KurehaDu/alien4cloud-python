from typing import Any, Dict, List, Optional, Set
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .state import WorkflowState, StateManager
from .executor import WorkflowExecutor, ExecutionError

logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    """调度器配置"""
    max_concurrent_workflows: int = 10
    max_workflow_timeout: int = 3600  # 秒
    cleanup_interval: int = 86400  # 秒
    history_retention_days: int = 30

class WorkflowScheduler:
    """工作流调度器"""
    
    def __init__(self, state_manager: StateManager, executor: WorkflowExecutor,
                 config: Optional[SchedulerConfig] = None):
        self.state_manager = state_manager
        self.executor = executor
        self.config = config or SchedulerConfig()
        self._running_workflows: Set[str] = set()
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动调度器"""
        if self._scheduler_task is not None:
            return

        # 启动调度任务
        self._scheduler_task = asyncio.create_task(self._schedule_workflows())
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_workflows())

        logger.info("工作流调度器已启动")

    async def stop(self) -> None:
        """停止调度器"""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        logger.info("工作流调度器已停止")

    async def schedule_workflow(self, workflow_id: str) -> None:
        """调度工作流"""
        workflow = self.state_manager.get_workflow_status(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        if workflow.state != WorkflowState.CREATED:
            raise ValueError(f"工作流 {workflow_id} 状态不正确: {workflow.state}")

        # 将工作流加入队列
        await self._queue.put(workflow_id)
        logger.info(f"工作流 {workflow_id} 已加入调度队列")

    async def _schedule_workflows(self) -> None:
        """工作流调度循环"""
        while True:
            try:
                # 检查是否可以执行更多工作流
                while len(self._running_workflows) < self.config.max_concurrent_workflows:
                    # 从队列中获取下一个工作流
                    try:
                        workflow_id = await asyncio.wait_for(
                            self._queue.get(),
                            timeout=1.0  # 1秒超时，允许定期检查停止信号
                        )
                    except asyncio.TimeoutError:
                        break

                    # 启动工作流执行
                    self._running_workflows.add(workflow_id)
                    asyncio.create_task(self._execute_workflow(workflow_id))
                    logger.info(f"工作流 {workflow_id} 开始执行")

                # 等待一段时间再继续调度
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                # 调度器被停止
                break
            except Exception as e:
                logger.exception("工作流调度出错")
                await asyncio.sleep(5)  # 出错后等待一段时间再继续

    async def _execute_workflow(self, workflow_id: str) -> None:
        """执行工作流并处理完成状态"""
        try:
            # 设置超时
            async with asyncio.timeout(self.config.max_workflow_timeout):
                await self.executor.execute_workflow(workflow_id)
        except asyncio.TimeoutError:
            logger.error(f"工作流 {workflow_id} 执行超时")
            self.state_manager.update_workflow_state(
                workflow_id,
                WorkflowState.FAILED,
                "工作流执行超时"
            )
        except Exception as e:
            logger.exception(f"工作流 {workflow_id} 执行出错")
        finally:
            self._running_workflows.remove(workflow_id)
            self._queue.task_done()

    async def _cleanup_workflows(self) -> None:
        """定期清理已完成的工作流"""
        while True:
            try:
                # 清理过期的工作流
                cleaned = self.state_manager.cleanup_completed_workflows(
                    self.config.history_retention_days
                )
                if cleaned > 0:
                    logger.info(f"已清理 {cleaned} 个已完成的工作流")

                # 等待下一次清理
                await asyncio.sleep(self.config.cleanup_interval)

            except asyncio.CancelledError:
                # 清理任务被停止
                break
            except Exception as e:
                logger.exception("工作流清理出错")
                await asyncio.sleep(300)  # 出错后等待5分钟再继续

    def get_queue_size(self) -> int:
        """获取队列中等待的工作流数量"""
        return self._queue.qsize()

    def get_running_count(self) -> int:
        """获取正在运行的工作流数量"""
        return len(self._running_workflows)

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            'queue_size': self.get_queue_size(),
            'running_count': self.get_running_count(),
            'max_concurrent_workflows': self.config.max_concurrent_workflows,
            'is_running': self._scheduler_task is not None
        } 