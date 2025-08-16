from kubernetes import client, config
import yaml
from typing import Dict, List

class ApplicationDeploymentManager:
    def __init__(self):
        config.load_kube_config()
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.networking_v1 = client.NetworkingV1Api()
    
    def deploy_application(self, app_config: Dict):
        namespace = app_config.get('namespace', 'default')
        
        # Create namespace if not exists
        self.create_namespace(namespace)
        
        # Deploy components
        if 'deployment' in app_config:
            self.create_deployment(app_config['deployment'], namespace)
        
        if 'service' in app_config:
            self.create_service(app_config['service'], namespace)
        
        if 'ingress' in app_config:
            self.create_ingress(app_config['ingress'], namespace)
    
    def create_deployment(self, deployment_config: Dict, namespace: str):
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=deployment_config['name']),
            spec=client.V1DeploymentSpec(
                replicas=deployment_config.get('replicas', 1),
                selector=client.V1LabelSelector(
                    match_labels=deployment_config['labels']
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels=deployment_config['labels']),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name=container['name'],
                                image=container['image'],
                                ports=[client.V1ContainerPort(container_port=port) 
                                       for port in container.get('ports', [])],
                                env=[client.V1EnvVar(name=k, value=v) 
                                     for k, v in container.get('env', {}).items()]
                            ) for container in deployment_config['containers']
                        ]
                    )
                )
            )
        )
        
        return self.apps_v1.create_namespaced_deployment(namespace, deployment)
    
    def rolling_update(self, deployment_name: str, new_image: str, namespace: str):
        # Get current deployment
        deployment = self.apps_v1.read_namespaced_deployment(deployment_name, namespace)
        
        # Update image
        deployment.spec.template.spec.containers[0].image = new_image
        
        # Apply update
        return self.apps_v1.patch_namespaced_deployment(deployment_name, namespace, deployment)
    
    def scale_deployment(self, deployment_name: str, replicas: int, namespace: str):
        # Scale deployment
        scale = client.V1Scale(
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1ScaleSpec(replicas=replicas)
        )
        
        return self.apps_v1.patch_namespaced_deployment_scale(deployment_name, namespace, scale)
