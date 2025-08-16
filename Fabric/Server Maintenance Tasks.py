from fabric import Connection, task

@task
def system_update(c):
    """Update system packages on remote server"""
    c.run('sudo apt update && sudo apt upgrade -y')
    c.run('sudo apt autoremove -y')
    print("System update completed")

@task
def backup_logs(c, backup_dir='/tmp/log_backup'):
    """Backup log files from remote server"""
    c.run(f'mkdir -p {backup_dir}')
    c.run(f'sudo tar -czf {backup_dir}/logs-$(date +%Y%m%d).tar.gz /var/log/')
    
    # Download backup to local machine
    c.get(f'{backup_dir}/logs-$(date +%Y%m%d).tar.gz', 'logs-backup.tar.gz')
    print("Log backup completed and downloaded")

@task
def monitor_services(c):
    """Check status of important services"""
    services = ['nginx', 'mysql', 'redis-server', 'docker']
    
    for service in services:
        result = c.run(f'systemctl is-active {service}', warn=True)
        status = result.stdout.strip()
        print(f"{service}: {status}")
        
        if status != 'active':
            print(f"⚠️ {service} is not running!")

# Usage example
def run_maintenance():
    servers = [
        'web-server-1.example.com',
        'web-server-2.example.com',
        'db-server.example.com'
    ]
    
    for server in servers:
        print(f"\n=== Maintaining {server} ===")
        with Connection(server) as c:
            system_update(c)
            monitor_services(c)
            backup_logs(c)
