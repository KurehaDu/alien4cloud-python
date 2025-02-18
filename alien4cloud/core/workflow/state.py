import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import os

from .base import (
    WorkflowState, StepState, WorkflowStatus, StepStatus,
    WorkflowTemplate, WorkflowInstance
)

logger = logging.getLogger(__name__)

class StateManager:
    """工作流状态管理器"""
    
    def __init__(self, data_dir: str = "/var/lib/alien4cloud"):
        """初始化状态管理器"""
        self.data_dir = data_dir
        self._workflows: Dict[str, WorkflowState] = {}
        self._templates: Dict[str, WorkflowTemplate] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
        self._load_from_file()

    def _load_from_file(self) -> None:
        """从文件加载状态"""
        try:
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            
            state_file = os.path.join(self.data_dir, "state.json")
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    data = json.load(f)
                    for wf_data in data.get("workflows", []):
                        wf = WorkflowState(**wf_data)
                        self._workflows[wf.id] = wf
                    for tmpl_data in data.get("templates", []):
                        tmpl = WorkflowTemplate(**tmpl_data)
                        self._templates[tmpl.id] = tmpl
                    for inst_data in data.get("instances", []):
                        inst = WorkflowInstance(**inst_data)
                        self._instances[inst.id] = inst
        except Exception as e:
            logger.error(f"加载状态失败: {str(e)}")

    def _save_to_file(self) -> None:
        """保存状态到文件"""
        try:
            state_file = os.path.join(self.data_dir, "state.json")
            data = {
                "workflows": [self._to_dict(wf) for wf in self._workflows.values()],
                "templates": [self._to_dict(tmpl) for tmpl in self._templates.values()],
                "instances": [self._to_dict(inst) for inst in self._instances.values()]
            }
            with open(state_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存状态失败: {str(e)}")

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """转换对象为字典"""
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return obj

    def create_workflow(self, workflow_id: str, name: str, inputs: Dict[str, Any] = None) -> WorkflowState:
        """创建工作流状态"""
        if workflow_id in self._workflows:
            raise ValueError(f"工作流 {workflow_id} 已存在")

        workflow = WorkflowState(
            id=workflow_id,
            name=name,
            inputs=inputs or {}
        )
        self._workflows[workflow_id] = workflow
        self._save_to_file()
        return workflow

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

        self._save_to_file()
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

        self._save_to_file()
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
        self._save_to_file()
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
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        count = 0
        for workflow_id in list(self._workflows.keys()):
            workflow = self._workflows[workflow_id]
            if (workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED] and
                workflow.completed_at and workflow.completed_at <= cutoff_date):
                del self._workflows[workflow_id]
                count += 1
        if count > 0:
            self._save_to_file()
        return count 