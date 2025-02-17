from fastapi import APIRouter, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from typing import List
import yaml
from fastapi import Depends

from alien4cloud.core.tosca.parser.workflow import WorkflowParser
from alien4cloud.core.workflow.models import WorkflowTemplate, WorkflowInstance, WorkflowStatus
from alien4cloud.core.workflow.converter import WorkflowConverter
from alien4cloud.core.database import get_db

router = APIRouter()

@router.post("/upload")
async def upload_yaml(file: UploadFile = File(...)):
    """上传并解析YAML文件"""
    try:
        content = await file.read()
        yaml_content = content.decode()
        # 解析YAML
        parser = WorkflowParser()
        parsed_data = parser.parse(yaml_content)
        return {"message": "解析成功", "data": parsed_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/template")
async def create_template(name: str, description: str, yaml_content: str):
    """创建工作流模板"""
    try:
        template = WorkflowTemplate(
            name=name,
            description=description,
            yaml_content=yaml_content,
            parsed_data=yaml.safe_load(yaml_content)
        )
        # TODO: 保存到数据库
        return {"message": "创建成功", "data": template}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/template/{template_id}")
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """获取工作流模板"""
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板未找到")
    return template

@router.post("/instance")
async def create_instance(template_id: int, name: str, cloud_provider: str = "mock", db: Session = Depends(get_db)):
    """从模板创建工作流实例"""
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板未找到")
    instance = WorkflowInstance(
        name=name,
        template_id=template_id,
        cloud_provider=cloud_provider,
        status=WorkflowStatus.CREATED
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance

@router.get("/instance/{instance_id}")
async def get_instance(instance_id: int, db: Session = Depends(get_db)):
    """获取工作流实例"""
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例未找到")
    return instance

@router.get("/instance/{instance_id}/status")
async def get_instance_status(instance_id: int, db: Session = Depends(get_db)):
    """获取工作流实例状态"""
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例未找到")
    return {"instance_id": instance.id, "status": instance.status}

@router.post("/deploy/{instance_id}")
async def deploy_workflow(instance_id: int, db: Session = Depends(get_db)):
    """部署工作流实例"""
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例未找到")
    # TODO: 执行部署逻辑
    instance.status = WorkflowStatus.RUNNING
    db.commit()
    return {"message": "部署成功", "instance_id": instance_id}

@router.delete("/undeploy/{instance_id}")
async def undeploy_workflow(instance_id: int, db: Session = Depends(get_db)):
    """撤销工作流实例"""
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例未找到")
    # TODO: 执行撤销逻辑
    instance.status = WorkflowStatus.STOPPED
    db.commit()
    return {"message": "撤销成功", "instance_id": instance_id}

@router.get("/status")
async def get_workflow_status(db: Session = Depends(get_db)):
    """获取所有工作流实例的状态"""
    instances = db.query(WorkflowInstance).all()
    return [{"instance_id": instance.id, "status": instance.status} for instance in instances] 