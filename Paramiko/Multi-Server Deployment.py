import paramiko
import threading
from concurrent.futures import ThreadPoolExecutor

class MultiServerDeployment:
    def __init__(self, servers):
        self.servers = servers
    
    def deploy_to_server(self, server_config):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                server_config['host'],
                username=server_config['username'],
                key_filename=server_config['key_path']
            )
            
            # Upload application
            sftp = ssh.open_sftp()
            sftp.put(server_config['local_path'], server_config['remote_path'])
            
            # Execute deployment commands
            commands = [
                'sudo systemctl stop myapp',
                f'sudo cp {server_config["remote_path"]} /opt/myapp/',
                'sudo systemctl start myapp',
                'sudo systemctl enable myapp'
            ]
            
            for cmd in commands:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                print(f"Server {server_config['host']}: {stdout.read().decode()}")
                
        finally:
            ssh.close()
    
    def parallel_deployment(self):
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(self.deploy_to_server, self.servers)
