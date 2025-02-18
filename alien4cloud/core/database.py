import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

# 基础异常类
class DatabaseError(Exception):
    """数据库错误基类"""
    pass

# 创建基础模型类
Base = declarative_base()

# 默认数据库配置
DEFAULT_DB_CONFIG = {
    'type': 'sqlite',
    'path': os.path.join(os.path.expanduser('~'), '.alien4cloud', 'alien4cloud.db'),
    'echo': False
}

class Database:
    """数据库管理类"""
    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._engine is None:
            self.init_db()

    def init_db(self, config: dict = None) -> None:
        """初始化数据库"""
        if config is None:
            config = DEFAULT_DB_CONFIG

        # 确保数据库目录存在
        db_dir = os.path.dirname(config['path'])
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # 创建数据库引擎
        if config['type'] == 'sqlite':
            self._engine = create_engine(
                f"sqlite:///{config['path']}", 
                echo=config['echo']
            )
        else:
            raise DatabaseError(f"不支持的数据库类型: {config['type']}")

        # 创建会话工厂
        self._session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine
        )

        # 创建表
        Base.metadata.create_all(bind=self._engine)

    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话"""
        if self._session_factory is None:
            raise DatabaseError("数据库未初始化")

        session = self._session_factory()
        try:
            yield session
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(f"数据库操作失败: {str(e)}")
        finally:
            session.close()

# 全局数据库实例
db = Database()

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（FastAPI依赖）"""
    try:
        yield from db.get_session()
    except DatabaseError as e:
        logger.error(f"获取数据库会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 