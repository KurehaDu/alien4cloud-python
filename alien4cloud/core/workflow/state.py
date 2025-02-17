from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .database import Database, DatabaseError

class WorkflowState(Enum):
    """工作流状态枚举"""
    CREATED = "created"         # 已创建
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    PAUSED = "paused"          # 已暂停
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 执行失败
    CANCELLED = "cancelled"     # 已取消

class StepState(Enum):
    """步骤状态枚举"""
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 执行失败
    SKIPPED = "skipped"        # 已跳过

@dataclass
class StepStatus:
    """步骤状态信息"""
    id: str
    name: str
    state: StepState
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'outputs': self.outputs,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StepStatus':
        """从字典创建实例"""
        return cls(
            id=data['id'],
            name=data['name'],
            state=StepState(data['state']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            error_message=data.get('error_message'),
            outputs=data.get('outputs', {}),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3)
        )

@dataclass
class WorkflowStatus:
    """工作流状态信息"""
    id: str
    name: str
    state: WorkflowState
    steps: Dict[str, StepStatus] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'state': self.state.value,
            'steps': {k: v.to_dict() for k, v in self.steps.items()},
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStatus':
        """从字典创建实例"""
        steps = {}
        for step_id, step_data in data.get('steps', {}).items():
            steps[step_id] = StepStatus.from_dict(step_data)

        return cls(
            id=data['id'],
            name=data['name'],
            state=WorkflowState(data['state']),
            steps=steps,
            created_at=datetime.fromisoformat(data['created_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            error_message=data.get('error_message'),
            inputs=data.get('inputs', {}),
            outputs=data.get('outputs', {}),
            metadata=data.get('metadata', {})
        )

class StateManager:
    """工作流状态管理器"""
    
    def __init__(self, database_url: str):
        """初始化状态管理器"""
        self.db = Database(database_url)
        self._workflows: Dict[str, WorkflowStatus] = {}
        self._load_from_db()

    def _load_from_db(self) -> None:
        """从数据库加载工作流状态"""
        try:
            workflows = self.db.list_workflows()
            for workflow in workflows:
                self._workflows[workflow.id] = workflow
        except DatabaseError as e:
            logger.error(f"从数据库加载工作流状态失败: {str(e)}")

    def create_workflow(self, workflow_id: str, name: str, inputs: Dict[str, Any] = None) -> WorkflowStatus:
        """创建工作流状态"""
        if workflow_id in self._workflows:
            raise ValueError(f"工作流 {workflow_id} 已存在")

        status = WorkflowStatus(
            id=workflow_id,
            name=name,
            state=WorkflowState.CREATED,
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

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """获取工作流状态"""
        return self._workflows.get(workflow_id)

    def update_workflow_state(self, workflow_id: str, state: WorkflowState, 
                            error_message: Optional[str] = None) -> WorkflowStatus:
        """更新工作流状态"""
        status = self._workflows.get(workflow_id)
        if not status:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        status.state = state
        if state == WorkflowState.RUNNING and not status.started_at:
            status.started_at = datetime.now()
        elif state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
            status.completed_at = datetime.now()
        
        if error_message:
            status.error_message = error_message

        try:
            self.db.save_workflow(status)
        except DatabaseError as e:
            logger.error(f"保存工作流状态失败: {str(e)}")
            raise

        return status

    def update_step_state(self, workflow_id: str, step_id: str, 
                         state: StepState, error_message: Optional[str] = None,
                         outputs: Dict[str, Any] = None) -> StepStatus:
        """更新步骤状态"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        step = workflow.steps.get(step_id)
        if not step:
            raise ValueError(f"步骤 {step_id} 不存在")

        step.state = state
        if state == StepState.RUNNING and not step.started_at:
            step.started_at = datetime.now()
        elif state in [StepState.COMPLETED, StepState.FAILED, StepState.SKIPPED]:
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

    def add_step(self, workflow_id: str, step_id: str, name: str) -> StepStatus:
        """添加工作流步骤"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")

        if step_id in workflow.steps:
            raise ValueError(f"步骤 {step_id} 已存在")

        step = StepStatus(
            id=step_id,
            name=name,
            state=StepState.PENDING
        )
        workflow.steps[step_id] = step

        try:
            self.db.save_workflow(workflow)
        except DatabaseError as e:
            logger.error(f"保存工作流状态失败: {str(e)}")
            del workflow.steps[step_id]
            raise

        return step

    def list_workflows(self, filters: Dict[str, Any] = None) -> List[WorkflowStatus]:
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
            # 重新加载内存中的工作流
            self._workflows.clear()
            self._load_from_db()
            return count
        except DatabaseError as e:
            logger.error(f"清理工作流失败: {str(e)}")
            raise 