import paramiko

class ServerChecker:
    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password
    
    def connect(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.hostname, username=self.username, password=self.password)
    
    def check_disk_space(self):
        stdin, stdout, stderr = self.ssh.exec_command('df -h')
        return stdout.read().decode()
    
    def check_services(self, services):
        results = {}
        for service in services:
            stdin, stdout, stderr = self.ssh.exec_command(f'systemctl is-active {service}')
            results[service] = stdout.read().decode().strip()
        return results
