from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import yaml
import logging
import os
from pathlib import Path

from alien4cloud.web.api import workflow, deploy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 加载配置
def load_config():
    config_file = os.getenv('CONFIG_FILE', 'config/app.yaml')
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"无法加载配置文件 {config_file}: {str(e)}")
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8088,
                "debug": True
            }
        }

config = load_config()
server_config = config.get("server", {})

# 创建FastAPI应用
app = FastAPI(
    title="Alien4Cloud Python",
    debug=server_config.get("debug", False)
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载API路由
app.include_router(workflow.router, prefix="/api/workflow", tags=["workflow"])
app.include_router(deploy.router, prefix="/api/deploy", tags=["deploy"])

# 挂载静态文件
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    """应用启动时的事件处理"""
    logger.info(f"服务启动于 http://{server_config.get('host', '0.0.0.0')}:{server_config.get('port', 8088)}")
    logger.info(f"调试模式: {server_config.get('debug', False)}")

def start():
    """启动应用的函数"""
    uvicorn.run(
        app,
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8088),
        reload=server_config.get("debug", False)
    )

if __name__ == "__main__":
    start() 