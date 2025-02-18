import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class StepState:
    """步骤状态"""
    id: str
    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    outputs: Dict[str, str] = field(default_factory=dict)

@dataclass
class WorkflowState:
    """工作流状态"""
    id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    steps: Dict[str, StepState] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class StateManager:
    """工作流状态管理器"""
    
    def __init__(self):
        """初始化状态管理器"""
        self._workflows: Dict[str, WorkflowState] = {}
        
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """获取工作流状态"""
        return self._workflows.get(workflow_id)

    def create_workflow(self, workflow_id: str, name: str) -> WorkflowState:
        """创建工作流状态"""
        state = WorkflowState(id=workflow_id, name=name)
        self._workflows[workflow_id] = state
        return state

    def update_workflow(self, workflow_id: str, status: WorkflowStatus, error_message: Optional[str] = None) -> None:
        """更新工作流状态"""
        state = self._workflows.get(workflow_id)
        if not state:
            return
        
        state.status = status
        if error_message:
            state.error_message = error_message
        
        if status == WorkflowStatus.RUNNING and not state.started_at:
            state.started_at = datetime.now()
        elif status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
            state.completed_at = datetime.now()

    def add_step(self, workflow_id: str, step_id: str, name: str) -> Optional[StepState]:
        """添加步骤状态"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        step = StepState(id=step_id, name=name)
        workflow.steps[step_id] = step
        return step

    def update_step(self, workflow_id: str, step_id: str, status: StepStatus, 
                   error_message: Optional[str] = None, outputs: Optional[Dict[str, str]] = None) -> None:
        """更新步骤状态"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return
        
        step = workflow.steps.get(step_id)
        if not step:
            return
        
        step.status = status
        if error_message:
            step.error_message = error_message
        if outputs:
            step.outputs.update(outputs)
        
        if status == StepStatus.RUNNING and not step.started_at:
            step.started_at = datetime.now()
        elif status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED):
            step.completed_at = datetime.now()

    def cleanup_workflow(self, workflow_id: str) -> None:
        """清理工作流状态"""
        self._workflows.pop(workflow_id, None)

    def list_workflows(self, filters: Dict[str, Any] = None) -> List[WorkflowState]:
        """列出工作流状态"""
        if not filters:
            return list(self._workflows.values())

        result = []
        for state in self._workflows.values():
            match = True
            for key, value in filters.items():
                if key in state and state[key] != value:
                    match = False
                    break
            if match:
                result.append(state)
        return result

    def cleanup_completed_workflows(self, max_age_days: int = 30) -> int:
        """清理已完成的工作流"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        count = 0
        for workflow_id in list(self._workflows.keys()):
            workflow = self._workflows[workflow_id]
            if (workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED] and
                workflow.completed_at and workflow.completed_at <= cutoff_date):
                del self._workflows[workflow_id]
                count += 1
        return count 