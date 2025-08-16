from fabric import Connection, task, ThreadingGroup
import time
import os

class DeploymentManager:
    def __init__(self, servers, app_config):
        self.servers = servers
        self.app_config = app_config
        self.group = ThreadingGroup(*servers)
    
    def pre_deployment_checks(self):
        """Run pre-deployment health checks"""
        results = self.group.run('df -h | grep -E "9[0-9]%|100%"', warn=True)
        
        failed_servers = []
        for conn, result in results.items():
            if result.return_code == 0:  # Found high disk usage
                failed_servers.append(conn.host)
                print(f"❌ {conn.host}: High disk usage detected")
            else:
                print(f"✅ {conn.host}: Disk usage OK")
        
        if failed_servers:
            raise Exception(f"Pre-deployment checks failed for: {failed_servers}")
    
    def backup_current_version(self):
        """Backup current application version"""
        backup_dir = f"/tmp/backup-{int(time.time())}"
        
        commands = [
            f'mkdir -p {backup_dir}',
            f'cp -r {self.app_config["app_dir"]} {backup_dir}/',
            f'systemctl stop {self.app_config["service_name"]}'
        ]
        
        for cmd in commands:
            self.group.run(cmd, pty=True)
        
        print(f"Current version backed up to {backup_dir}")
        return backup_dir
    
    def deploy_new_version(self, version_tag):
        """Deploy new application version"""
        
        # Upload new version
        for server in self.servers:
            with Connection(server) as c:
                # Upload application files
                c.put(
                    f'./dist/{self.app_config["app_name"]}-{version_tag}.tar.gz',
                    '/tmp/app.tar.gz'
                )
                
                # Extract and install
                c.run(f'cd {self.app_config["app_dir"]} && sudo tar -xzf /tmp/app.tar.gz')
                c.run('sudo chown -R appuser:appuser ' + self.app_config["app_dir"])
        
        # Install dependencies
        self.group.run(f'cd {self.app_config["app_dir"]} && pip install -r requirements.txt')
        
        # Update configuration
        self.update_configuration()
        
        print(f"New version {version_tag} deployed")
    
    def update_configuration(self):
        """Update application configuration"""
        config_commands = [
            f'sudo cp {self.app_config["app_dir"]}/config/prod.conf /etc/{self.app_config["service_name"]}/',
            f'sudo systemctl daemon-reload'
        ]
        
        for cmd in config_commands:
            self.group.run(cmd)
    
    def start_services(self):
        """Start application services"""
        service_commands = [
            f'sudo systemctl start {self.app_config["service_name"]}',
            f'sudo systemctl enable {self.app_config["service_name"]}'
        ]
        
        for cmd in service_commands:
            self.group.run(cmd)
        
        # Wait for services to start
        time.sleep(10)
    
    def health_check(self):
        """Perform post-deployment health checks"""
        health_url = self.app_config.get('health_check_url', '/health')
        
        failed_servers = []
        for server in self.servers:
            with Connection(server) as c:
                result = c.run(
                    f'curl -f http://localhost:8080{health_url}',
                    warn=True
                )
                
                if result.return_code != 0:
                    failed_servers.append(server)
                    print(f"❌ {server}: Health check failed")
                else:
                    print(f"✅ {server}: Health check passed")
        
        if failed_servers:
            raise Exception(f"Health checks failed for: {failed_servers}")
    
    def rollback(self, backup_dir):
        """Rollback to previous version"""
        print(f"Rolling back to backup: {backup_dir}")
        
        rollback_commands = [
            f'sudo systemctl stop {self.app_config["service_name"]}',
            f'rm -rf {self.app_config["app_dir"]}',
            f'cp -r {backup_dir}/{os.path.basename(self.app_config["app_dir"])} {self.app_config["app_dir"]}',
            f'sudo systemctl start {self.app_config["service_name"]}'
        ]
        
        for cmd in rollback_commands:
            self.group.run(cmd, pty=True)
        
        print("Rollback completed")
    
    def deploy(self, version_tag):
        """Execute full deployment pipeline"""
        backup_dir = None
        
        try:
            print("🔍 Running pre-deployment checks...")
            self.pre_deployment_checks()
            
            print("💾 Backing up current version...")
            backup_dir = self.backup_current_version()
            
            print(f"🚀 Deploying version {version_tag}...")
            self.deploy_new_version(version_tag)
            
            print("▶️ Starting services...")
            self.start_services()
            
            print("🏥 Running health checks...")
            self.health_check()
            
            print("✅ Deployment completed successfully!")
            
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            
            if backup_dir:
                print("🔄 Initiating rollback...")
                self.rollback(backup_dir)
            
            raise e
