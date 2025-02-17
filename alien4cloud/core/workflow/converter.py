from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..tosca.model.workflow import WorkflowDefinition, WorkflowStep, WorkflowStepType
from .state import WorkflowStatus, StepStatus, WorkflowState, StepState

class WorkflowConverter:
    """工作流转换器，将TOSCA工作流定义转换为可执行的工作流"""
    
    @classmethod
    def from_definition(cls, definition: WorkflowDefinition) -> WorkflowStatus:
        """从工作流定义创建工作流状态"""
        # 创建工作流状态
        workflow = WorkflowStatus(
            id=definition.id or str(uuid.uuid4()),
            name=definition.name,
            state=WorkflowState.CREATED,
            created_at=datetime.now(),
            inputs=definition.inputs,
            metadata={
                "preconditions": definition.preconditions,
                "triggers": definition.triggers
            }
        )
        
        # 转换步骤
        for step_id, step_def in definition.steps.items():
            step = cls._convert_step(step_id, step_def)
            workflow.steps[step_id] = step
            
        return workflow
    
    @classmethod
    def _convert_step(cls, step_id: str, step_def: WorkflowStep) -> StepStatus:
        """转换工作流步骤"""
        return StepStatus(
            id=step_id,
            name=step_def.target,
            state=StepState.PENDING,
            outputs={
                "type": step_def.type.value,
                "operation": step_def.operation,
                "inputs": step_def.inputs,
                "on_success": step_def.on_success,
                "on_failure": step_def.on_failure
            }
        )
    
    @classmethod
    def to_definition(cls, workflow: WorkflowStatus) -> WorkflowDefinition:
        """将工作流状态转换回工作流定义"""
        # 创建工作流定义
        definition = WorkflowDefinition(
            id=workflow.id,
            name=workflow.name,
            inputs=workflow.inputs,
            preconditions=workflow.metadata.get("preconditions", []),
            triggers=workflow.metadata.get("triggers", [])
        )
        
        # 转换步骤
        for step_id, step in workflow.steps.items():
            step_def = cls._convert_step_back(step)
            definition.steps[step_id] = step_def
            
        return definition
    
    @classmethod
    def _convert_step_back(cls, step: StepStatus) -> WorkflowStep:
        """将步骤状态转换回步骤定义"""
        outputs = step.outputs
        return WorkflowStep(
            type=WorkflowStepType(outputs["type"]),
            target=step.name,
            operation=outputs.get("operation"),
            inputs=outputs.get("inputs", {}),
            on_success=outputs.get("on_success", []),
            on_failure=outputs.get("on_failure", [])
        ) 