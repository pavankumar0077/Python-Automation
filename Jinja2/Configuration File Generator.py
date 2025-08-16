from jinja2 import Environment, FileSystemLoader
import yaml
import os

class ConfigGenerator:
    def __init__(self, templates_dir='templates'):
        self.env = Environment(loader=FileSystemLoader(templates_dir))
    
    def generate_nginx_config(self, server_config):
        """Generate Nginx configuration from template"""
        template = self.env.get_template('nginx.conf.j2')
        
        return template.render(
            server_name=server_config['server_name'],
            listen_port=server_config.get('listen_port', 80),
            root_path=server_config['root_path'],
            upstream_servers=server_config.get('upstream_servers', []),
            ssl_enabled=server_config.get('ssl_enabled', False),
            ssl_cert_path=server_config.get('ssl_cert_path'),
            ssl_key_path=server_config.get('ssl_key_path')
        )
    
    def generate_systemd_service(self, service_config):
        """Generate systemd service file"""
        template = self.env.get_template('systemd.service.j2')
        
        return template.render(
            service_name=service_config['name'],
            description=service_config['description'],
            user=service_config.get('user', 'root'),
            group=service_config.get('group', 'root'),
            exec_start=service_config['exec_start'],
            working_directory=service_config.get('working_directory', '/'),
            environment_vars=service_config.get('environment', {}),
            restart_policy=service_config.get('restart_policy', 'always')
        )
    
    def batch_generate_configs(self, config_file):
        """Generate multiple configuration files from YAML specification"""
        with open(config_file, 'r') as f:
            configs = yaml.safe_load(f)
        
        generated_files = []
        
        for config in configs['configurations']:
            if config['type'] == 'nginx':
                content = self.generate_nginx_config(config['settings'])
            elif config['type'] == 'systemd':
                content = self.generate_systemd_service(config['settings'])
            else:
                continue
            
            # Write to file
            output_path = config['output_path']
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(content)
            
            generated_files.append(output_path)
            print(f"Generated: {output_path}")
        
        return generated_files

# Template files would be stored in templates/ directory:

# templates/nginx.conf.j2
nginx_template = """
server {
    listen {{ listen_port }};
    server_name {{ server_name }};
    
    {% if ssl_enabled %}
    listen 443 ssl;
    ssl_certificate {{ ssl_cert_path }};
    ssl_certificate_key {{ ssl_key_path }};
    {% endif %}
    
    root {{ root_path }};
    index index.html index.htm;
    
    {% if upstream_servers %}
    upstream backend {
        {% for server in upstream_servers %}
        server {{ server.host }}:{{ server.port }} weight={{ server.weight|default(1) }};
        {% endfor %}
    }
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    {% endif %}
    
    location /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
}
"""

# templates/systemd.service.j2
systemd_template = """
[Unit]
Description={{ description }}
After=network.target

[Service]
Type=simple
User={{ user }}
Group={{ group }}
WorkingDirectory={{ working_directory }}
ExecStart={{ exec_start }}
Restart={{ restart_policy }}
RestartSec=10

{% if environment_vars %}
{% for key, value in environment_vars.items() %}
Environment="{{ key }}={{ value }}"
{% endfor %}
{% endif %}

[Install]
WantedBy=multi-user.target
"""
