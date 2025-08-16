import docker
import yaml
import time
from typing import Dict, List

class MultiServiceOrchestrator:
    def __init__(self, compose_file: str):
        self.client = docker.from_env()
        with open(compose_file, 'r') as f:
            self.compose_config = yaml.safe_load(f)
        self.network = None
    
    def create_network(self):
        self.network = self.client.networks.create(
            "app_network",
            driver="bridge"
        )
        return self.network.id
    
    def deploy_services(self):
        self.create_network()
        
        for service_name, service_config in self.compose_config['services'].items():
            self.deploy_service(service_name, service_config)
    
    def deploy_service(self, name: str, config: Dict):
        # Build image if build context provided
        if 'build' in config:
            image = self.build_image(name, config['build'])
        else:
            image = config['image']
        
        # Create container
        container = self.client.containers.run(
            image,
            name=name,
            ports=config.get('ports', {}),
            environment=config.get('environment', {}),
            volumes=config.get('volumes', {}),
            network=self.network.name,
            detach=True,
            restart_policy={"Name": "unless-stopped"}
        )
        
        print(f"Deployed service: {name} ({container.id[:12]})")
        return container
    
    def health_check(self):
        services_health = {}
        for service_name in self.compose_config['services'].keys():
            try:
                container = self.client.containers.get(service_name)
                services_health[service_name] = {
                    'status': container.status,
                    'health': getattr(container.attrs['State'], 'Health', {}).get('Status', 'unknown')
                }
            except docker.errors.NotFound:
                services_health[service_name] = {'status': 'not_found', 'health': 'unhealthy'}
        
        return services_health
