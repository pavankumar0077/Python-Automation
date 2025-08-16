from kubernetes import client, config
import git
import yaml
import os
import tempfile
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ClusterConfig:
    name: str
    kubeconfig_path: str
    context: str

class MultiClusterGitOpsManager:
    def __init__(self, clusters: List[ClusterConfig], git_repo_url: str):
        self.clusters = {cluster.name: cluster for cluster in clusters}
        self.git_repo_url = git_repo_url
        self.temp_dir = tempfile.mkdtemp()
        self.repo = git.Repo.clone_from(git_repo_url, self.temp_dir)
    
    def sync_cluster(self, cluster_name: str):
        cluster_config = self.clusters[cluster_name]
        config.load_kube_config(config_file=cluster_config.kubeconfig_path, 
                               context=cluster_config.context)
        
        cluster_manifests_path = os.path.join(self.temp_dir, 'clusters', cluster_name)
        
        if os.path.exists(cluster_manifests_path):
            self.apply_manifests(cluster_manifests_path)
    
    def apply_manifests(self, manifests_path: str):
        for root, dirs, files in os.walk(manifests_path):
            for file in files:
                if file.endswith(('.yaml', '.yml')):
                    manifest_path = os.path.join(root, file)
                    self.apply_manifest(manifest_path)
    
    def apply_manifest(self, manifest_path: str):
        with open(manifest_path, 'r') as f:
            manifests = yaml.safe_load_all(f)
            
        for manifest in manifests:
            if not manifest:
                continue
                
            kind = manifest.get('kind')
            namespace = manifest.get('metadata', {}).get('namespace', 'default')
            
            if kind == 'Deployment':
                self.apply_deployment(manifest, namespace)
            elif kind == 'Service':
                self.apply_service(manifest, namespace)
            elif kind == 'ConfigMap':
                self.apply_configmap(manifest, namespace)
    
    def health_check_clusters(self) -> Dict[str, Dict]:
        cluster_health = {}
        
        for cluster_name, cluster_config in self.clusters.items():
            try:
                config.load_kube_config(config_file=cluster_config.kubeconfig_path,
                                       context=cluster_config.context)
                v1 = client.CoreV1Api()
                
                # Check node status
                nodes = v1.list_node()
                ready_nodes = sum(1 for node in nodes.items 
                                 if any(condition.type == 'Ready' and condition.status == 'True'
                                       for condition in node.status.conditions))
                
                # Check system pods
                system_pods = v1.list_namespaced_pod('kube-system')
                running_pods = sum(1 for pod in system_pods.items 
                                  if pod.status.phase == 'Running')
                
                cluster_health[cluster_name] = {
                    'status': 'healthy',
                    'nodes_ready': ready_nodes,
                    'total_nodes': len(nodes.items),
                    'system_pods_running': running_pods,
                    'total_system_pods': len(system_pods.items)
                }
                
            except Exception as e:
                cluster_health[cluster_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        return cluster_health
    
    def disaster_recovery(self, source_cluster: str, target_cluster: str):
        # Backup source cluster resources
        source_config = self.clusters[source_cluster]
        config.load_kube_config(config_file=source_config.kubeconfig_path,
                               context=source_config.context)
        
        apps_v1 = client.AppsV1Api()
        core_v1 = client.CoreV1Api()
        
        # Get all deployments and services
        deployments = apps_v1.list_deployment_for_all_namespaces()
        services = core_v1.list_service_for_all_namespaces()
        
        # Switch to target cluster
        target_config = self.clusters[target_cluster]
        config.load_kube_config(config_file=target_config.kubeconfig_path,
                               context=target_config.context)
        
        target_apps_v1 = client.AppsV1Api()
        target_core_v1 = client.CoreV1Api()
        
        # Recreate resources in target cluster
        for deployment in deployments.items:
            if deployment.metadata.namespace != 'kube-system':
                self.recreate_deployment(deployment, target_apps_v1)
        
        for service in services.items:
            if service.metadata.namespace != 'kube-system':
                self.recreate_service(service, target_core_v1)
