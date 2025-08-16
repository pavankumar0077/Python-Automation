import paramiko
import yaml
import time
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ServerConfig:
    hostname: str
    username: str
    key_path: str
    roles: List[str]

class InfrastructureOrchestrator:
    def __init__(self, config_file: str):
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        self.servers = [ServerConfig(**server) for server in self.config['servers']]
    
    def execute_playbook(self, playbook_path: str):
        with open(playbook_path, 'r') as f:
            playbook = yaml.safe_load(f)
        
        for play in playbook['plays']:
            target_servers = self.get_servers_by_role(play['hosts'])
            
            for server in target_servers:
                self.execute_tasks_on_server(server, play['tasks'])
    
    def execute_tasks_on_server(self, server: ServerConfig, tasks: List[Dict]):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(server.hostname, username=server.username, key_filename=server.key_path)
            
            for task in tasks:
                if task['type'] == 'shell':
                    self.execute_shell_task(ssh, task)
                elif task['type'] == 'file':
                    self.execute_file_task(ssh, task)
                elif task['type'] == 'service':
                    self.execute_service_task(ssh, task)
                    
        finally:
            ssh.close()
