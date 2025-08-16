from kubernetes import client, config

class PodManager:
    def __init__(self):
        config.load_incluster_config()  # or load_kube_config() for local
        self.v1 = client.CoreV1Api()
    
    def create_pod(self, name, image, namespace='default'):
        pod_spec = client.V1Pod(
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name=name,
                        image=image,
                        ports=[client.V1ContainerPort(container_port=80)]
                    )
                ]
            )
        )
        
        return self.v1.create_namespaced_pod(namespace, pod_spec)
    
    def list_pods(self, namespace='default'):
        pods = self.v1.list_namespaced_pod(namespace)
        return [(pod.metadata.name, pod.status.phase) for pod in pods.items]
    
    def delete_pod(self, name, namespace='default'):
        return self.v1.delete_namespaced_pod(name, namespace)
