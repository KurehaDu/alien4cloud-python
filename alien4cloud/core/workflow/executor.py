# alien4cloud/core/workflow/executor.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import asyncio
import logging
from datetime import datetime, timedelta

from .state import WorkflowState, StepState, WorkflowStatus, StepStatus, StateManager

logger = logging.getLogger(__name__)

class ExecutionError(Exception):
    """执行错误"""
    pass

class StepExecutor(ABC):
    """步骤执行器接口"""
    
    @abstractmethod
    async def execute(self, step: StepStatus, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行步骤"""
        pass

    @abstractmethod
    async def cancel(self, step: StepStatus) -> None:
        """取消步骤执行"""
        pass

class NodeOperationExecutor(StepExecutor):
    """节点操作执行器"""
    
    async def execute(self, step: StepStatus, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行节点操作"""
        # MVP版本：模拟执行
        await asyncio.sleep(2)  # 模拟操作执行时间
        return {'result': 'success', 'message': f'执行节点操作 {step.name}'}

    async def cancel(self, step: StepStatus) -> None:
        """取消节点操作"""
        # MVP版本：简单实现
        pass

class RelationshipOperationExecutor(StepExecutor):
    """关系操作执行器"""
    
    async def execute(self, step: StepStatus, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行关系操作"""
        # MVP版本：模拟执行
        await asyncio.sleep(1.5)  # 模拟操作执行时间
        return {'result': 'success', 'message': f'执行关系操作 {step.name}'}

    async def cancel(self, step: StepStatus) -> None:
        """取消关系操作"""
        # MVP版本：简单实现
        pass

class InlineExecutor(StepExecutor):
    """内联操作执行器"""
    
    async def execute(self, step: StepStatus, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行内联操作"""
        # MVP版本：模拟执行
        await asyncio.sleep(1)  # 模拟操作执行时间
        return {'result': 'success', 'message': f'执行内联操作 {step.name}'}

    async def cancel(self, step: StepStatus) -> None:
        """取消内联操作"""
        # MVP版本：简单实现
        pass

class WorkflowExecutor:
    """工作流执行器"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.executors = {
            'node_operation': NodeOperationExecutor(),
            'relationship_operation': RelationshipOperationExecutor(),
            'inline': InlineExecutor()
        }
        self._running_workflows: Dict[str, asyncio.Task] = {}

    async def execute_workflow(self, workflow_id: str) -> None:
        """执行工作流"""
        workflow = self.state_manager.get_workflow_status(workflow_id)
        if not workflow:
            raise ExecutionError(f"工作流 {workflow_id} 不存在")

        if workflow.state != WorkflowState.CREATED:
            raise ExecutionError(f"工作流 {workflow_id} 状态不正确: {workflow.state}")

        # 更新工作流状态为PENDING
        self.state_manager.update_workflow_state(workflow_id, WorkflowState.PENDING)

        # 创建执行任务
        task = asyncio.create_task(self._execute_workflow_steps(workflow))
        self._running_workflows[workflow_id] = task

        try:
            await task
        except asyncio.CancelledError:
            # 工作流被取消
            self.state_manager.update_workflow_state(
                workflow_id, 
                WorkflowState.CANCELLED,
                "工作流被手动取消"
            )
        except Exception as e:
            # 工作流执行失败
            logger.exception(f"工作流 {workflow_id} 执行失败")
            self.state_manager.update_workflow_state(
                workflow_id, 
                WorkflowState.FAILED,
                str(e)
            )
        finally:
            self._running_workflows.pop(workflow_id, None)

    async def cancel_workflow(self, workflow_id: str) -> None:
        """取消工作流执行"""
        task = self._running_workflows.get(workflow_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _execute_workflow_steps(self, workflow: WorkflowStatus) -> None:
        """执行工作流步骤"""
        # 更新工作流状态为RUNNING
        self.state_manager.update_workflow_state(workflow.id, WorkflowState.RUNNING)

        try:
            # 获取所有待执行的步骤
            pending_steps = {
                step_id: step 
                for step_id, step in workflow.steps.items()
                if step.state == StepState.PENDING
            }

            # 执行步骤
            while pending_steps:
                # 获取可执行的步骤（没有依赖或依赖已完成的步骤）
                executable_steps = self._get_executable_steps(workflow, pending_steps)
                if not executable_steps:
                    raise ExecutionError("检测到循环依赖或无法执行的步骤")

                # 并行执行可执行的步骤
                tasks = []
                for step_id in executable_steps:
                    step = pending_steps[step_id]
                    task = asyncio.create_task(self._execute_step(workflow, step))
                    tasks.append(task)

                # 等待所有任务完成
                await asyncio.gather(*tasks)

                # 从待执行列表中移除已完成的步骤
                for step_id in executable_steps:
                    pending_steps.pop(step_id)

            # 所有步骤执行完成，更新工作流状态
            self.state_manager.update_workflow_state(workflow.id, WorkflowState.COMPLETED)

        except Exception as e:
            # 更新工作流状态为FAILED
            self.state_manager.update_workflow_state(
                workflow.id, 
                WorkflowState.FAILED,
                str(e)
            )
            raise

    def _get_executable_steps(self, workflow: WorkflowStatus, 
                            pending_steps: Dict[str, StepStatus]) -> List[str]:
        """获取可执行的步骤"""
        executable_steps = []
        
        for step_id, step in pending_steps.items():
            # 检查步骤的依赖是否都已完成
            dependencies_met = True
            for other_id, other_step in workflow.steps.items():
                if other_id == step_id:
                    continue
                if (step_id in other_step.outputs.get('on_success', []) and 
                    other_step.state != StepState.COMPLETED):
                    dependencies_met = False
                    break
                if (step_id in other_step.outputs.get('on_failure', []) and 
                    other_step.state != StepState.FAILED):
                    dependencies_met = False
                    break
            
            if dependencies_met:
                executable_steps.append(step_id)

        return executable_steps

    async def _execute_step(self, workflow: WorkflowStatus, step: StepStatus) -> None:
        """执行单个步骤"""
        # 更新步骤状态为RUNNING
        self.state_manager.update_step_state(workflow.id, step.id, StepState.RUNNING)

        try:
            # 获取步骤类型对应的执行器
            executor = self.executors.get(step.outputs.get('type', 'inline'))
            if not executor:
                raise ExecutionError(f"未知的步骤类型: {step.outputs.get('type')}")

            # 执行步骤
            result = await executor.execute(step, workflow.inputs)

            # 更新步骤状态为COMPLETED
            self.state_manager.update_step_state(
                workflow.id,
                step.id,
                StepState.COMPLETED,
                outputs=result
            )

        except Exception as e:
            # 更新步骤状态为FAILED
            self.state_manager.update_step_state(
                workflow.id,
                step.id,
                StepState.FAILED,
                error_message=str(e)
            )
            raise