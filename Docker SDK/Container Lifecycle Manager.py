import docker

class ContainerManager:
    def __init__(self):
        self.client = docker.from_env()
    
    def create_and_run_container(self, image, name, ports=None, environment=None):
        container = self.client.containers.run(
            image,
            name=name,
            ports=ports or {},
            environment=environment or {},
            detach=True
        )
        return container.id
    
    def list_containers(self, all=False):
        containers = self.client.containers.list(all=all)
        return [(c.name, c.status, c.image.tags) for c in containers]
    
    def cleanup_stopped_containers(self):
        stopped_containers = self.client.containers.list(filters={'status': 'exited'})
        for container in stopped_containers:
            container.remove()
            print(f"Removed container: {container.name}")
