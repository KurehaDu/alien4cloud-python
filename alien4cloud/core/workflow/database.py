# alien4cloud/core/workflow/database.py

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, WorkflowModel, StepModel
from .state import WorkflowState, StepState, WorkflowStatus, StepStatus

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """数据库操作错误"""
    pass

class Database:
    """数据库操作类"""
    
    def __init__(self, database_url: str):
        """初始化数据库连接"""
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建表
        Base.metadata.create_all(self.engine)
        
        logger.info(f"数据库初始化完成: {database_url}")

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def save_workflow(self, workflow: WorkflowStatus) -> None:
        """保存工作流状态"""
        try:
            with self.get_session() as session:
                # 检查工作流是否存在
                db_workflow = session.get(WorkflowModel, workflow.id)
                if db_workflow is None:
                    # 创建新工作流
                    db_workflow = WorkflowModel(
                        id=workflow.id,
                        name=workflow.name,
                        state=workflow.state,
                        created_at=workflow.created_at,
                        started_at=workflow.started_at,
                        completed_at=workflow.completed_at,
                        error_message=workflow.error_message,
                        inputs=workflow.inputs,
                        outputs=workflow.outputs,
                        metadata=workflow.metadata
                    )
                    session.add(db_workflow)
                else:
                    # 更新现有工作流
                    db_workflow.state = workflow.state
                    db_workflow.started_at = workflow.started_at
                    db_workflow.completed_at = workflow.completed_at
                    db_workflow.error_message = workflow.error_message
                    db_workflow.inputs = workflow.inputs
                    db_workflow.outputs = workflow.outputs
                    db_workflow.metadata = workflow.metadata

                # 保存步骤
                for step_id, step in workflow.steps.items():
                    db_step = session.get(StepModel, step_id)
                    if db_step is None:
                        # 创建新步骤
                        db_step = StepModel(
                            id=step_id,
                            workflow_id=workflow.id,
                            name=step.name,
                            state=step.state,
                            started_at=step.started_at,
                            completed_at=step.completed_at,
                            error_message=step.error_message,
                            outputs=step.outputs,
                            retry_count=step.retry_count,
                            max_retries=step.max_retries
                        )
                        session.add(db_step)
                    else:
                        # 更新现有步骤
                        db_step.state = step.state
                        db_step.started_at = step.started_at
                        db_step.completed_at = step.completed_at
                        db_step.error_message = step.error_message
                        db_step.outputs = step.outputs
                        db_step.retry_count = step.retry_count

                session.commit()
                
        except SQLAlchemyError as e:
            logger.error(f"保存工作流失败: {str(e)}")
            raise DatabaseError(f"保存工作流失败: {str(e)}")

    def load_workflow(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """加载工作流状态"""
        try:
            with self.get_session() as session:
                db_workflow = session.get(WorkflowModel, workflow_id)
                if db_workflow is None:
                    return None

                # 转换为WorkflowStatus
                workflow = WorkflowStatus(
                    id=db_workflow.id,
                    name=db_workflow.name,
                    state=db_workflow.state,
                    created_at=db_workflow.created_at,
                    started_at=db_workflow.started_at,
                    completed_at=db_workflow.completed_at,
                    error_message=db_workflow.error_message,
                    inputs=db_workflow.inputs,
                    outputs=db_workflow.outputs,
                    metadata=db_workflow.metadata
                )

                # 加载步骤
                for db_step in db_workflow.steps:
                    step = StepStatus(
                        id=db_step.id,
                        name=db_step.name,
                        state=db_step.state,
                        started_at=db_step.started_at,
                        completed_at=db_step.completed_at,
                        error_message=db_step.error_message,
                        outputs=db_step.outputs,
                        retry_count=db_step.retry_count,
                        max_retries=db_step.max_retries
                    )
                    workflow.steps[db_step.id] = step

                return workflow

        except SQLAlchemyError as e:
            logger.error(f"加载工作流失败: {str(e)}")
            raise DatabaseError(f"加载工作流失败: {str(e)}")

    def list_workflows(self, filters: Dict[str, Any] = None) -> List[WorkflowStatus]:
        """列出工作流状态"""
        try:
            with self.get_session() as session:
                # 构建查询
                query = select(WorkflowModel)
                if filters:
                    for key, value in filters.items():
                        if hasattr(WorkflowModel, key):
                            query = query.where(getattr(WorkflowModel, key) == value)

                # 执行查询
                workflows = []
                for db_workflow in session.execute(query).scalars():
                    workflow = WorkflowStatus(
                        id=db_workflow.id,
                        name=db_workflow.name,
                        state=db_workflow.state,
                        created_at=db_workflow.created_at,
                        started_at=db_workflow.started_at,
                        completed_at=db_workflow.completed_at,
                        error_message=db_workflow.error_message,
                        inputs=db_workflow.inputs,
                        outputs=db_workflow.outputs,
                        metadata=db_workflow.metadata
                    )
                    
                    # 加载步骤
                    for db_step in db_workflow.steps:
                        step = StepStatus(
                            id=db_step.id,
                            name=db_step.name,
                            state=db_step.state,
                            started_at=db_step.started_at,
                            completed_at=db_step.completed_at,
                            error_message=db_step.error_message,
                            outputs=db_step.outputs,
                            retry_count=db_step.retry_count,
                            max_retries=db_step.max_retries
                        )
                        workflow.steps[db_step.id] = step
                    
                    workflows.append(workflow)

                return workflows

        except SQLAlchemyError as e:
            logger.error(f"列出工作流失败: {str(e)}")
            raise DatabaseError(f"列出工作流失败: {str(e)}")

    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        try:
            with self.get_session() as session:
                db_workflow = session.get(WorkflowModel, workflow_id)
                if db_workflow is None:
                    return False
                
                session.delete(db_workflow)
                session.commit()
                return True

        except SQLAlchemyError as e:
            logger.error(f"删除工作流失败: {str(e)}")
            raise DatabaseError(f"删除工作流失败: {str(e)}")

    def cleanup_workflows(self, max_age_days: int = 30) -> int:
        """清理过期工作流"""
        try:
            with self.get_session() as session:
                # 计算截止时间
                cutoff_date = datetime.now() - timedelta(days=max_age_days)
                
                # 查找需要清理的工作流
                completed_states = [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]
                query = select(WorkflowModel).where(
                    WorkflowModel.state.in_(completed_states),
                    WorkflowModel.completed_at <= cutoff_date
                )
                
                # 删除工作流
                count = 0
                for db_workflow in session.execute(query).scalars():
                    session.delete(db_workflow)
                    count += 1
                
                session.commit()
                return count

        except SQLAlchemyError as e:
            logger.error(f"清理工作流失败: {str(e)}")
            raise DatabaseError(f"清理工作流失败: {str(e)}") 