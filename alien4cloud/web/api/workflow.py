from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import yaml
import logging
from fastapi import Depends

from alien4cloud.core.tosca.parser.workflow import WorkflowDefinitionParser
from alien4cloud.core.workflow.models import WorkflowTemplate, WorkflowInstance
from alien4cloud.core.workflow.state import WorkflowState, StateManager
from alien4cloud.core.workflow.converter import WorkflowConverter
from alien4cloud.core.workflow.executor import WorkflowExecutor
from alien4cloud.core.workflow.scheduler import WorkflowScheduler, SchedulerConfig
from alien4cloud.core.database import get_db, DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter()

# 创建工作流执行器和调度器
state_manager = StateManager("sqlite:///alien4cloud.db")
executor = WorkflowExecutor(state_manager)
scheduler = WorkflowScheduler(state_manager, executor)

@router.on_event("startup")
async def startup_event():
    """启动时初始化调度器"""
    await scheduler.start()

@router.on_event("shutdown")
async def shutdown_event():
    """关闭时停止调度器"""
    await scheduler.stop()

@router.post("/upload")
async def upload_yaml(file: UploadFile = File(...)) -> Dict[str, Any]:
    """上传并解析YAML文件"""
    try:
        content = await file.read()
        yaml_content = content.decode()
        # 解析YAML
        parser = WorkflowDefinitionParser()
        parsed_data = parser.parse_string(yaml_content)
        return {"message": "解析成功", "data": parsed_data}
    except Exception as e:
        logger.error(f"解析YAML文件失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/template")
async def create_template(
    name: str, 
    description: str, 
    yaml_content: str, 
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """创建工作流模板"""
    try:
        # 解析YAML
        parser = WorkflowDefinitionParser()
        parsed_data = parser.parse_string(yaml_content)
        
        template = WorkflowTemplate(
            name=name,
            description=description,
            yaml_content=yaml_content,
            parsed_data=parsed_data.to_dict()
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        logger.info(f"创建工作流模板成功: {template.id}")
        return {"message": "创建成功", "data": template}
    except Exception as e:
        db.rollback()
        logger.error(f"创建工作流模板失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/template/{template_id}")
async def get_template(template_id: int, db: Session = Depends(get_db)) -> WorkflowTemplate:
    """获取工作流模板"""
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        logger.warning(f"工作流模板未找到: {template_id}")
        raise HTTPException(status_code=404, detail="模板未找到")
    return template

@router.post("/instance")
async def create_instance(
    template_id: int, 
    name: str, 
    cloud_provider: str = "mock", 
    db: Session = Depends(get_db)
) -> WorkflowInstance:
    """从模板创建工作流实例"""
    try:
        template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
        if not template:
            logger.warning(f"工作流模板未找到: {template_id}")
            raise HTTPException(status_code=404, detail="模板未找到")

        # 解析模板并创建工作流
        parser = WorkflowDefinitionParser()
        workflow_def = parser.parse_string(template.yaml_content)
        workflow = WorkflowConverter.from_definition(workflow_def)

        # 创建实例
        instance = WorkflowInstance(
            name=name,
            template_id=template_id,
            cloud_provider=cloud_provider,
            status=WorkflowState.CREATED.value,
            nodes_status={}  # 初始化节点状态
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)

        # 保存工作流状态
        state_manager.create_workflow(str(instance.id), name, workflow.inputs)

        logger.info(f"创建工作流实例成功: {instance.id}")
        return instance
    except Exception as e:
        db.rollback()
        logger.error(f"创建工作流实例失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/instance/{instance_id}")
async def get_instance(instance_id: int, db: Session = Depends(get_db)) -> WorkflowInstance:
    """获取工作流实例"""
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        logger.warning(f"工作流实例未找到: {instance_id}")
        raise HTTPException(status_code=404, detail="实例未找到")
    return instance

@router.get("/instance/{instance_id}/status")
async def get_instance_status(instance_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取工作流实例状态"""
    try:
        # 从数据库获取实例
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            logger.warning(f"工作流实例未找到: {instance_id}")
            raise HTTPException(status_code=404, detail="实例未找到")

        # 从状态管理器获取详细状态
        workflow_status = state_manager.get_workflow_status(str(instance_id))
        if workflow_status:
            return {
                "instance_id": instance.id,
                "status": instance.status,
                "nodes_status": instance.nodes_status,
                "workflow_status": workflow_status.to_dict()
            }
        else:
            return {
                "instance_id": instance.id,
                "status": instance.status,
                "nodes_status": instance.nodes_status
            }
    except Exception as e:
        logger.error(f"获取工作流状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deploy/{instance_id}")
async def deploy_workflow(
    instance_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """部署工作流实例"""
    try:
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            logger.warning(f"工作流实例未找到: {instance_id}")
            raise HTTPException(status_code=404, detail="实例未找到")

        # 检查状态
        if instance.status not in [WorkflowState.CREATED.value, WorkflowState.FAILED.value]:
            raise HTTPException(status_code=400, detail=f"工作流状态不正确: {instance.status}")

        # 调度工作流
        background_tasks.add_task(scheduler.schedule_workflow, str(instance_id))

        instance.status = WorkflowState.PENDING.value
        instance.nodes_status = {"status": "deploying"}
        db.commit()

        logger.info(f"部署工作流实例成功: {instance_id}")
        return {"message": "部署成功", "instance_id": instance_id}
    except Exception as e:
        db.rollback()
        logger.error(f"部署工作流实例失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/undeploy/{instance_id}")
async def undeploy_workflow(instance_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """撤销工作流实例"""
    try:
        instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not instance:
            logger.warning(f"工作流实例未找到: {instance_id}")
            raise HTTPException(status_code=404, detail="实例未找到")

        # 取消工作流执行
        await executor.cancel_workflow(str(instance_id))

        instance.status = WorkflowState.CANCELLED.value
        instance.nodes_status = {"status": "undeployed"}
        db.commit()

        logger.info(f"撤销工作流实例成功: {instance_id}")
        return {"message": "撤销成功", "instance_id": instance_id}
    except Exception as e:
        db.rollback()
        logger.error(f"撤销工作流实例失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def get_workflow_status(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """获取所有工作流实例的状态"""
    try:
        instances = db.query(WorkflowInstance).all()
        result = []
        for instance in instances:
            status = {
                "instance_id": instance.id,
                "status": instance.status,
                "nodes_status": instance.nodes_status
            }
            # 获取详细状态
            workflow_status = state_manager.get_workflow_status(str(instance.id))
            if workflow_status:
                status["workflow_status"] = workflow_status.to_dict()
            result.append(status)
        return result
    except Exception as e:
        logger.error(f"获取工作流状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scheduler/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """获取调度器状态"""
    return scheduler.get_scheduler_status() 