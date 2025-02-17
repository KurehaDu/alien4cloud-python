from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from alien4cloud.web.api import workflow, deploy

app = FastAPI(title="Alien4Cloud Python")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载API路由
app.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
app.include_router(deploy.router, prefix="/deploy", tags=["deploy"])

# 挂载静态文件
app.mount("/static", StaticFiles(directory="alien4cloud/web/static"), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8088, reload=True) 