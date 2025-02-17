# alien4cloud/cloud/providers/k8s/provider.py

import asyncio
import base64
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

from ...base import CloudProvider, ResourceStatus, DeploymentStatus
from ...errors import (
    CloudError, ConfigError, ConnectionError, ResourceError,
    DeploymentError, OperationError, NotFoundError
)

class K8sCloudProvider(CloudProvider):
    """Kubernetes云平台提供者"""

    def __init__(self):
        self._connected = False
        self._api_client = None
        self._core_api = None
        self._apps_api = None
        self._custom_api = None
        self._namespace = "default"
        self._label_selector = "app.kubernetes.io/managed-by=alien4cloud"

    async def connect(self) -> None:
        """连接到Kubernetes集群"""
        try:
            # 尝试从默认位置加载配置
            config.load_kube_config()
            
            # 创建API客户端
            self._api_client = client.ApiClient()
            self._core_api = client.CoreV1Api(self._api_client)
            self._apps_api = client.AppsV1Api(self._api_client)
            self._custom_api = client.CustomObjectsApi(self._api_client)
            
            # 验证连接
            self._core_api.list_namespace()
            self._connected = True
        except Exception as e:
            raise ConnectionError(f"无法连接到Kubernetes集群: {str(e)}")

    async def disconnect(self) -> None:
        """断开与Kubernetes集群的连接"""
        if self._api_client:
            self._api_client.close()
        self._connected = False
        self._api_client = None
        self._core_api = None
        self._apps_api = None
        self._custom_api = None

    async def validate_connection(self) -> bool:
        """验证连接是否有效"""
        if not self._connected:
            return False
        try:
            self._core_api.list_namespace()
            return True
        except:
            return False

    def _check_connection(self):
        """检查连接状态"""
        if not self._connected:
            raise ConnectionError("未连接到Kubernetes集群")

    def _create_deployment_manifest(self, name: str, template: Dict[str, Any],
                                  inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建Kubernetes部署清单"""
        # 这里简化处理，假设模板直接是Kubernetes资源定义
        manifest = template.copy()
        
        # 添加标准标签
        labels = manifest.get("metadata", {}).get("labels", {})
        labels.update({
            "app.kubernetes.io/name": name,
            "app.kubernetes.io/managed-by": "alien4cloud"
        })
        manifest.setdefault("metadata", {})["labels"] = labels
        
        # 如果有输入参数，将其添加到注解中
        if inputs:
            annotations = manifest.get("metadata", {}).get("annotations", {})
            annotations["alien4cloud.inputs"] = base64.b64encode(
                json.dumps(inputs).encode()
            ).decode()
            manifest["metadata"]["annotations"] = annotations
        
        return manifest

    async def create_deployment(self, name: str, template: Dict[str, Any],
                              inputs: Dict[str, Any] = None) -> str:
        """创建部署"""
        self._check_connection()
        
        # 验证模板
        errors = await self.validate_template(template)
        if errors:
            raise DeploymentError(f"模板验证失败: {', '.join(errors)}")

        try:
            # 创建部署清单
            manifest = self._create_deployment_manifest(name, template, inputs)
            kind = manifest.get("kind", "").lower()

            # 根据资源类型创建资源
            if kind == "deployment":
                response = self._apps_api.create_namespaced_deployment(
                    namespace=self._namespace,
                    body=manifest
                )
            elif kind == "service":
                response = self._core_api.create_namespaced_service(
                    namespace=self._namespace,
                    body=manifest
                )
            else:
                # 对于其他类型的资源，使用通用API
                response = self._custom_api.create_namespaced_custom_object(
                    group=manifest["apiVersion"].split("/")[0],
                    version=manifest["apiVersion"].split("/")[1],
                    namespace=self._namespace,
                    plural=f"{kind}s",
                    body=manifest
                )

            return response.metadata.name

        except ApiException as e:
            raise DeploymentError(f"创建部署失败: {str(e)}")

    async def delete_deployment(self, deployment_id: str) -> None:
        """删除部署"""
        self._check_connection()
        
        try:
            # 删除部署
            self._apps_api.delete_namespaced_deployment(
                name=deployment_id,
                namespace=self._namespace
            )
            
            # 删除相关服务
            try:
                self._core_api.delete_namespaced_service(
                    name=deployment_id,
                    namespace=self._namespace
                )
            except ApiException as e:
                if e.status != 404:  # 忽略未找到错误
                    raise
                    
        except ApiException as e:
            if e.status != 404:  # 忽略未找到错误
                raise DeploymentError(f"删除部署失败: {str(e)}")

    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatus:
        """获取部署状态"""
        self._check_connection()
        
        try:
            # 获取部署
            deployment = self._apps_api.read_namespaced_deployment(
                name=deployment_id,
                namespace=self._namespace
            )
            
            # 获取相关的Pod
            pods = self._core_api.list_namespaced_pod(
                namespace=self._namespace,
                label_selector=f"app.kubernetes.io/name={deployment_id}"
            )
            
            # 创建资源状态列表
            resources = []
            for pod in pods.items:
                resources.append(ResourceStatus(
                    id=pod.metadata.uid,
                    name=pod.metadata.name,
                    type="Pod",
                    state=pod.status.phase,
                    created_at=pod.metadata.creation_timestamp,
                    updated_at=datetime.now(),
                    metadata={
                        "node": pod.spec.node_name,
                        "ip": pod.status.pod_ip,
                        "conditions": [
                            {
                                "type": c.type,
                                "status": c.status,
                                "message": c.message
                            }
                            for c in pod.status.conditions or []
                        ]
                    }
                ))
            
            # 创建部署状态
            return DeploymentStatus(
                id=deployment.metadata.uid,
                name=deployment.metadata.name,
                state="running" if deployment.status.available_replicas else "pending",
                resources=resources,
                created_at=deployment.metadata.creation_timestamp,
                started_at=deployment.status.start_time,
                completed_at=None,  # Kubernetes部署没有完成时间的概念
                error_message=None,
                metadata={
                    "replicas": deployment.spec.replicas,
                    "available_replicas": deployment.status.available_replicas,
                    "conditions": [
                        {
                            "type": c.type,
                            "status": c.status,
                            "message": c.message
                        }
                        for c in deployment.status.conditions or []
                    ]
                }
            )
            
        except ApiException as e:
            if e.status == 404:
                raise NotFoundError(f"未找到部署 {deployment_id}")
            raise CloudError(f"获取部署状态失败: {str(e)}")

    async def list_deployments(self, filters: Dict[str, Any] = None) -> List[DeploymentStatus]:
        """列出部署"""
        self._check_connection()
        
        try:
            # 获取所有部署
            deployments = self._apps_api.list_namespaced_deployment(
                namespace=self._namespace,
                label_selector=self._label_selector
            )
            
            # 转换为DeploymentStatus列表
            result = []
            for deployment in deployments.items:
                status = await self.get_deployment_status(deployment.metadata.name)
                
                # 应用过滤器
                if filters:
                    match = True
                    for key, value in filters.items():
                        if key == "state":
                            if status.state != value:
                                match = False
                                break
                        elif key == "name":
                            if value not in status.name:
                                match = False
                                break
                    if not match:
                        continue
                        
                result.append(status)
                
            return result
            
        except ApiException as e:
            raise CloudError(f"列出部署失败: {str(e)}")

    async def update_deployment(self, deployment_id: str,
                              template: Dict[str, Any],
                              inputs: Dict[str, Any] = None) -> None:
        """更新部署"""
        self._check_connection()
        
        # 验证模板
        errors = await self.validate_template(template)
        if errors:
            raise DeploymentError(f"模板验证失败: {', '.join(errors)}")

        try:
            # 创建更新的部署清单
            manifest = self._create_deployment_manifest(deployment_id, template, inputs)
            
            # 更新部署
            self._apps_api.replace_namespaced_deployment(
                name=deployment_id,
                namespace=self._namespace,
                body=manifest
            )
            
        except ApiException as e:
            if e.status == 404:
                raise NotFoundError(f"未找到部署 {deployment_id}")
            raise DeploymentError(f"更新部署失败: {str(e)}")

    async def execute_operation(self, deployment_id: str, operation: str,
                              inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行操作"""
        self._check_connection()
        
        try:
            deployment = self._apps_api.read_namespaced_deployment(
                name=deployment_id,
                namespace=self._namespace
            )
            
            if operation == "scale":
                # 扩缩容操作
                replicas = inputs.get("replicas", 1)
                self._apps_api.patch_namespaced_deployment_scale(
                    name=deployment_id,
                    namespace=self._namespace,
                    body={"spec": {"replicas": replicas}}
                )
                return {"status": "success", "replicas": replicas}
                
            elif operation == "restart":
                # 重启操作
                patch = {
                    "spec": {
                        "template": {
                            "metadata": {
                                "annotations": {
                                    "kubectl.kubernetes.io/restartedAt": datetime.now().isoformat()
                                }
                            }
                        }
                    }
                }
                self._apps_api.patch_namespaced_deployment(
                    name=deployment_id,
                    namespace=self._namespace,
                    body=patch
                )
                return {"status": "success"}
                
            else:
                raise OperationError(f"不支持的操作: {operation}")
                
        except ApiException as e:
            if e.status == 404:
                raise NotFoundError(f"未找到部署 {deployment_id}")
            raise OperationError(f"执行操作失败: {str(e)}")

    async def get_logs(self, deployment_id: str, resource_id: Optional[str] = None,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> List[str]:
        """获取日志"""
        self._check_connection()
        
        try:
            # 获取Pod列表
            pods = self._core_api.list_namespaced_pod(
                namespace=self._namespace,
                label_selector=f"app.kubernetes.io/name={deployment_id}"
            )
            
            logs = []
            for pod in pods.items:
                if resource_id and pod.metadata.uid != resource_id:
                    continue
                    
                # 获取Pod日志
                pod_logs = self._core_api.read_namespaced_pod_log(
                    name=pod.metadata.name,
                    namespace=self._namespace,
                    since_seconds=int((datetime.now() - start_time).total_seconds())
                    if start_time else None
                )
                
                # 添加Pod标识到日志
                for line in pod_logs.split("\n"):
                    if line:
                        logs.append(f"[{pod.metadata.name}] {line}")
                        
            return logs
            
        except ApiException as e:
            if e.status == 404:
                raise NotFoundError(f"未找到部署 {deployment_id}")
            raise CloudError(f"获取日志失败: {str(e)}")

    async def get_metrics(self, deployment_id: str, resource_id: Optional[str] = None,
                         metric_names: List[str] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> Dict[str, List[Any]]:
        """获取指标"""
        self._check_connection()
        
        try:
            # 获取Pod列表
            pods = self._core_api.list_namespaced_pod(
                namespace=self._namespace,
                label_selector=f"app.kubernetes.io/name={deployment_id}"
            )
            
            # 获取指标
            metrics = {}
            for pod in pods.items:
                if resource_id and pod.metadata.uid != resource_id:
                    continue
                    
                # 从Metrics API获取Pod指标
                pod_metrics = self._custom_api.get_namespaced_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    namespace=self._namespace,
                    plural="pods",
                    name=pod.metadata.name
                )
                
                # 处理CPU和内存指标
                for container in pod_metrics.get("containers", []):
                    cpu = container.get("usage", {}).get("cpu", "0")
                    memory = container.get("usage", {}).get("memory", "0")
                    
                    metrics.setdefault("cpu_usage", []).append(self._parse_cpu(cpu))
                    metrics.setdefault("memory_usage", []).append(self._parse_memory(memory))
                    
            return metrics
            
        except ApiException as e:
            if e.status == 404:
                raise NotFoundError(f"未找到部署 {deployment_id}")
            raise CloudError(f"获取指标失败: {str(e)}")

    def _parse_cpu(self, cpu: str) -> float:
        """解析CPU指标"""
        if cpu.endswith("n"):
            return float(cpu[:-1]) / 1000000000
        elif cpu.endswith("u"):
            return float(cpu[:-1]) / 1000000
        elif cpu.endswith("m"):
            return float(cpu[:-1]) / 1000
        return float(cpu)

    def _parse_memory(self, memory: str) -> int:
        """解析内存指标"""
        if memory.endswith("Ki"):
            return int(memory[:-2]) * 1024
        elif memory.endswith("Mi"):
            return int(memory[:-2]) * 1024 * 1024
        elif memory.endswith("Gi"):
            return int(memory[:-2]) * 1024 * 1024 * 1024
        return int(memory)

    async def validate_template(self, template: Dict[str, Any]) -> List[str]:
        """验证模板"""
        errors = []
        
        if not isinstance(template, dict):
            errors.append("模板必须是字典类型")
            return errors

        # 检查必需字段
        required_fields = ["apiVersion", "kind", "metadata"]
        for field in required_fields:
            if field not in template:
                errors.append(f"模板必须包含{field}字段")

        # 检查metadata
        metadata = template.get("metadata", {})
        if not isinstance(metadata, dict):
            errors.append("metadata必须是字典类型")
        elif "name" not in metadata:
            errors.append("metadata必须包含name字段")

        # 检查spec
        if "spec" not in template:
            errors.append("模板必须包含spec字段")
        elif not isinstance(template["spec"], dict):
            errors.append("spec必须是字典类型")

        return errors

    async def get_resource_types(self) -> List[str]:
        """获取支持的资源类型"""
        self._check_connection()
        return [
            "Deployment",
            "Service",
            "ConfigMap",
            "Secret",
            "PersistentVolumeClaim",
            "Job",
            "CronJob"
        ]

    async def get_operation_types(self) -> List[str]:
        """获取支持的操作类型"""
        self._check_connection()
        return [
            "scale",
            "restart"
        ]

    async def get_provider_info(self) -> Dict[str, Any]:
        """获取提供者信息"""
        version_info = None
        if self._connected:
            try:
                version_info = self._api_client.get_api_resources_api().get_code()
            except:
                pass
                
        return {
            "name": "Kubernetes Cloud Provider",
            "version": version_info.git_version if version_info else "unknown",
            "description": "Kubernetes集群云平台提供者",
            "features": [
                "deployment",
                "service",
                "configmap",
                "secret",
                "volume",
                "job",
                "cronjob"
            ]
        } 