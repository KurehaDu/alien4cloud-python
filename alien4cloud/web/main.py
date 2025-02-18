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
app = FastAPI(
    title="Alien4Cloud Python",
    debug=config.get("server", {}).get("debug", False)
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

if __name__ == "__main__":
    server_config = config.get("server", {})
    uvicorn.run(
        "alien4cloud.web.main:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8088),
        reload=server_config.get("debug", False)
    ) 