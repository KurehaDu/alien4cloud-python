import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .base import WorkflowState, StepState, WorkflowStatus, StepStatus
from .database import Database, DatabaseError

logger = logging.getLogger(__name__)

class StateManager:
    """工作流状态管理器"""
    
    def __init__(self, database_url: str):
        """初始化状态管理器"""
        self.db = Database(database_url)
        self._workflows: Dict[str, WorkflowState] = {}
        self._load_from_db()

    def _load_from_db(self) -> None:
        """从数据库加载工作流状态"""
        try:
            workflows = self.db.list_workflows()
            for workflow in workflows:
                self._workflows[workflow.id] = workflow
        except DatabaseError as e:
            logger.error(f"从数据库加载工作流状态失败: {str(e)}")

    def create_workflow(self, workflow_id: str, name: str, inputs: Dict[str, Any] = None) -> WorkflowState:
        """创建工作流状态"""
        if workflow_id in self._workflows:
            raise ValueError(f"工作流 {workflow_id} 已存在")

        status = WorkflowState(
            id=workflow_id,
            name=name,
            status=WorkflowStatus.CREATED,
            inputs=inputs or {}
        )
        self._workflows[workflow_id] = status
        
        try:
            self.db.save_workflow(status)
        except DatabaseError as e:
            logger.error(f"保存工作流状态失败: {str(e)}")
            del self._workflows[workflow_id]
            raise
        
        return status

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowState]:
        """获取工作流状态"""
        return self._workflows.get(workflow_id)

    def update_workflow_state(self, workflow_id: str, status: WorkflowStatus, 
                            error_message: Optional[str] = None) -> WorkflowState:
        """更新工作流状态"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        workflow.status = status
        if status == WorkflowStatus.RUNNING and not workflow.started_at:
            workflow.started_at = datetime.now()
        elif status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
            workflow.completed_at = datetime.now()
        
        if error_message:
            workflow.error_message = error_message

        try:
            self.db.save_workflow(workflow)
        except DatabaseError as e:
            logger.error(f"保存工作流状态失败: {str(e)}")
            raise

        return workflow

    def update_step_state(self, workflow_id: str, step_id: str, 
                         status: StepStatus, error_message: Optional[str] = None,
                         outputs: Dict[str, Any] = None) -> StepState:
        """更新步骤状态"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        step = workflow.steps.get(step_id)
        if not step:
            raise ValueError(f"步骤 {step_id} 不存在")

        step.status = status
        if status == StepStatus.RUNNING and not step.started_at:
            step.started_at = datetime.now()
        elif status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]:
            step.completed_at = datetime.now()

        if error_message:
            step.error_message = error_message
        if outputs:
            step.outputs.update(outputs)

        try:
            self.db.save_workflow(workflow)
        except DatabaseError as e:
            logger.error(f"保存工作流状态失败: {str(e)}")
            raise

        return step

    def add_step(self, workflow_id: str, step_id: str, name: str) -> StepState:
        """添加工作流步骤"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        if step_id in workflow.steps:
            raise ValueError(f"步骤 {step_id} 已存在")

        step = StepState(
            id=step_id,
            name=name,
            status=StepStatus.PENDING
        )
        workflow.steps[step_id] = step

        try:
            self.db.save_workflow(workflow)
        except DatabaseError as e:
            logger.error(f"保存工作流状态失败: {str(e)}")
            del workflow.steps[step_id]
            raise

        return step

    def list_workflows(self, filters: Dict[str, Any] = None) -> List[WorkflowState]:
        """列出工作流状态"""
        if not filters:
            return list(self._workflows.values())

        result = []
        for workflow in self._workflows.values():
            match = True
            for key, value in filters.items():
                if hasattr(workflow, key) and getattr(workflow, key) != value:
                    match = False
                    break
            if match:
                result.append(workflow)
        return result

    def cleanup_completed_workflows(self, max_age_days: int = 30) -> int:
        """清理已完成的工作流"""
        try:
            count = self.db.cleanup_workflows(max_age_days)
            # 从内存中移除已清理的工作流
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            for workflow_id in list(self._workflows.keys()):
                workflow = self._workflows[workflow_id]
                if (workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED] and
                    workflow.completed_at and workflow.completed_at <= cutoff_date):
                    del self._workflows[workflow_id]
            return count
        except DatabaseError as e:
            logger.error(f"清理工作流失败: {str(e)}")
            raise 