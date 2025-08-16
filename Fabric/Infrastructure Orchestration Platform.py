from fabric import Connection, ThreadingGroup, task
import yaml
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class ServerGroup:
    name: str
    servers: List[str]
    roles: List[str]
    variables: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Task:
    name: str
    command: str
    when: Optional[str] = None
    retries: int = 0
    delay: int = 0

@dataclass
class Playbook:
    name: str
    hosts: str
    tasks: List[Task]
    variables: Dict[str, Any] = field(default_factory=dict)

class InfrastructureOrchestrator:
    def __init__(self, inventory_file: str):
        with open(inventory_file, 'r') as f:
            inventory = yaml.safe_load(f)
        
        self.server_groups = {}
        for group_name, group_config in inventory['groups'].items():
            self.server_groups[group_name] = ServerGroup(
                name=group_name,
                servers=group_config['hosts'],
                roles=group_config.get('roles', []),
                variables=group_config.get('vars', {})
            )
    
    def run_playbook(self, playbook_file: str):
        """Execute a playbook across infrastructure"""
        with open(playbook_file, 'r') as f:
            playbook_config = yaml.safe_load(f)
        
        playbook = Playbook(
            name=playbook_config['name'],
            hosts=playbook_config['hosts'],
            tasks=[Task(**task) for task in playbook_config['tasks']],
            variables=playbook_config.get('vars', {})
        )
        
        # Get target servers
        if playbook.hosts == 'all':
            target_servers = []
            for group in self.server_groups.values():
                target_servers.extend(group.servers)
        else:
            target_servers = self.server_groups[playbook.hosts].servers
        
        print(f"Executing playbook '{playbook.name}' on {len(target_servers)} servers")
        
        # Execute tasks
        results = {}
        for task in playbook.tasks:
            print(f"\n📋 Task: {task.name}")
            task_results = self.execute_task_on_servers(task, target_servers, playbook.variables)
            results[task.name] = task_results
        
        return results
    
    def execute_task_on_servers(self, task: Task, servers: List[str], variables: Dict[str, Any]):
        """Execute a single task on multiple servers"""
        
        def execute_on_server(server):
            try:
                with Connection(server) as c:
                    # Substitute variables in command
                    command = self.substitute_variables(task.command, variables)
                    
                    # Execute with retries
                    for attempt in range(task.retries + 1):
                        try:
                            result = c.run(command, warn=True, pty=True)
                            
                            if result.return_code == 0:
                                return {
                                    'server': server,
                                    'status': 'success',
                                    'stdout': result.stdout,
                                    'attempt': attempt + 1
                                }
                            elif attempt < task.retries:
                                print(f"⚠️ {server}: Retry {attempt + 1}/{task.retries}")
                                time.sleep(task.delay)
                                continue
                            else:
                                return {
                                    'server': server,
                                    'status': 'failed',
                                    'stderr': result.stderr,
                                    'return_code': result.return_code,
                                    'attempts': attempt + 1
                                }
                                
                        except Exception as e:
                            if attempt < task.retries:
                                print(f"⚠️ {server}: Exception on attempt {attempt + 1}: {e}")
                                time.sleep(task.delay)
                                continue
                            else:
                                return {
                                    'server': server,
                                    'status': 'error',
                                    'error': str(e),
                                    'attempts': attempt + 1
                                }
                                
            except Exception as e:
                return {
                    'server': server,
                    'status': 'connection_error',
                    'error': str(e)
                }
        
        # Execute in parallel
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_server = {executor.submit(execute_on_server, server): server 
                               for server in servers}
            
            for future in as_completed(future_to_server):
                result = future.result()
                results.append(result)
                
                # Print status
                status_emoji = {
                    'success': '✅',
                    'failed': '❌',
                    'error': '💥',
                    'connection_error': '🔌'
                }.get(result['status'], '❓')
                
                print(f"{status_emoji} {result['server']}: {result['status']}")
        
        return results
    
    def substitute_variables(self, command: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in command string"""
        for var_name, var_value in variables.items():
            command = command.replace(f"{{{var_name}}}", str(var_value))
        return command
    
    def rolling_restart(self, service_name: str, server_group: str, batch_size: int = 1):
        """Perform rolling restart of service across server group"""
        servers = self.server_groups[server_group].servers
        
        print(f"🔄 Rolling restart of {service_name} on {len(servers)} servers (batch size: {batch_size})")
        
        # Process servers in batches
        for i in range(0, len(servers), batch_size):
            batch = servers[i:i + batch_size]
            
            print(f"\n📦 Processing batch {i//batch_size + 1}: {batch}")
            
            # Stop services in batch
            print("🛑 Stopping services...")
            for server in batch:
                with Connection(server) as c:
                    result = c.run(f'sudo systemctl stop {service_name}', warn=True)
                    if result.return_code != 0:
                        print(f"⚠️ Failed to stop {service_name} on {server}")
            
            # Wait a moment
            time.sleep(5)
            
            # Start services in batch
            print("▶️ Starting services...")
            for server in batch:
                with Connection(server) as c:
                    result = c.run(f'sudo systemctl start {service_name}', warn=True)
                    if result.return_code != 0:
                        print(f"❌ Failed to start {service_name} on {server}")
                        return False
            
            # Health check
            print("🏥 Health checking...")
            time.sleep(10)  # Wait for services to stabilize
            
            health_ok = True
            for server in batch:
                with Connection(server) as c:
                    result = c.run(f'systemctl is-active {service_name}', warn=True)
                    if result.return_code != 0:
                        print(f"❌ Health check failed for {server}")
                        health_ok = False
            
            if not health_ok:
                print("❌ Rolling restart failed - stopping")
                return False
            
            print(f"✅ Batch {i//batch_size + 1} completed successfully")
            
            # Wait before next batch
            if i + batch_size < len(servers):
                print("⏳ Waiting before next batch...")
                time.sleep(30)
        
        print("🎉 Rolling restart completed successfully!")
        return True
    
    def disaster_recovery(self, primary_group: str, backup_group: str):
        """Perform disaster recovery failover"""
        print(f"🚨 Initiating disaster recovery: {primary_group} -> {backup_group}")
        
        primary_servers = self.server_groups[primary_group].servers
        backup_servers = self.server_groups[backup_group].servers
        
        # Check primary servers health
        primary_healthy = self.check_group_health(primary_group)
        backup_healthy = self.check_group_health(backup_group)
        
        if not backup_healthy:
            raise Exception("Backup servers are not healthy - cannot proceed with failover")
        
        if primary_healthy:
            print("⚠️ Primary servers appear healthy - manual confirmation required")
            # In a real system, you'd require manual confirmation here
        
        # Activate backup servers
        print("🔄 Activating backup servers...")
        backup_group_obj = self.server_groups[backup_group]
        
        with ThreadingGroup(*backup_servers) as group:
            # Start all services
            services = backup_group_obj.variables.get('services', ['nginx', 'app'])
            
            for service in services:
                print(f"▶️ Starting {service} on backup servers...")
                group.run(f'sudo systemctl start {service}')
                group.run(f'sudo systemctl enable {service}')
        
        # Update DNS/Load Balancer (simulation)
        print("🌐 Updating DNS records...")
        time.sleep(2)  # Simulate DNS update
        
        # Verify failover
        print("✅ Disaster recovery completed - backup servers are now active")
        return True
    
    def check_group_health(self, group_name: str) -> bool:
        """Check health of all servers in a group"""
        servers = self.server_groups[group_name].servers
        healthy_servers = 0
        
        for server in servers:
            try:
                with Connection(server) as c:
                    result = c.run('uptime', warn=True, timeout=10)
                    if result.return_code == 0:
                        healthy_servers += 1
            except:
                pass  # Server is not reachable
        
        health_percentage = (healthy_servers / len(servers)) * 100
        print(f"🏥 {group_name} health: {healthy_servers}/{len(servers)} ({health_percentage:.1f}%)")
        
        return health_percentage >= 80  # Consider healthy if 80%+ servers respond
