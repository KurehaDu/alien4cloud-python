from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List, Dict, Any, Optional
import yaml
import logging
from datetime import datetime
from pydantic import BaseModel

from alien4cloud.core.tosca.parser.workflow import WorkflowDefinitionParser
from alien4cloud.core.workflow.state import StateManager
from alien4cloud.core.workflow.executor import MockWorkflowExecutor

logger = logging.getLogger(__name__)

router = APIRouter()

# 创建工作流执行器和状态管理器
state_manager = StateManager()
executor = MockWorkflowExecutor(state_manager)

class WorkflowCreate(BaseModel):
    """创建工作流请求"""
    name: str
    description: Optional[str] = None
    inputs: Dict[str, str] = {}

class WorkflowResponse(BaseModel):
    """工作流响应"""
    id: str
    name: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

@router.post("/upload")
async def upload_yaml(file: UploadFile = File(...)) -> Dict[str, Any]:
    """上传并解析YAML文件"""
    try:
        # 验证文件类型
        if not file.filename.endswith('.yaml') and not file.filename.endswith('.yml'):
            raise HTTPException(status_code=400, detail="仅支持YAML文件")
            
        content = await file.read()
        yaml_content = content.decode()
        # 解析YAML
        parser = WorkflowDefinitionParser()
        parsed_data = parser.parse_string(yaml_content)
        return {"message": "解析成功", "data": parsed_data.to_dict()}
    except Exception as e:
        logger.error(f"解析YAML文件失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(workflow: WorkflowCreate):
    """创建工作流"""
    # 生成工作流ID
    workflow_id = f"wf-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # 创建工作流状态
    state = state_manager.create_workflow(workflow_id, workflow.name)
    
    # 使用当前时间作为创建时间
    now = datetime.now()
    
    return WorkflowResponse(
        id=state.id,
        name=state.name,
        status=state.status.value,
        created_at=now,
        started_at=state.started_at,
        completed_at=state.completed_at,
        error_message=state.error_message
    )

@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    """获取工作流"""
    state = state_manager.get_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_id} 不存在")
    
    return WorkflowResponse(
        id=state.id,
        name=state.name,
        status=state.status.value,
        created_at=state.started_at or datetime.now(),
        started_at=state.started_at,
        completed_at=state.completed_at,
        error_message=state.error_message
    )

@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, inputs: Dict[str, str] = {}):
    """执行工作流"""
    state = state_manager.get_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_id} 不存在")
    
    try:
        await executor.execute_workflow(workflow_id, inputs)
        return {"message": "工作流执行成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows():
    """列出所有工作流"""
    workflows = state_manager.list_workflows()
    now = datetime.now()
    return [
        WorkflowResponse(
            id=state.id,
            name=state.name,
            status=state.status.value,
            created_at=state.started_at or now,
            started_at=state.started_at,
            completed_at=state.completed_at,
            error_message=state.error_message
        )
        for state in workflows
    ] 