from jinja2 import Environment, FileSystemLoader, select_autoescape
import yaml
import json
from typing import Dict, List, Any, Optional
import os

class IaCTemplateEngine:
    def __init__(self, templates_dir: str = 'templates'):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['to_json'] = json.dumps
        self.env.filters['from_yaml'] = yaml.safe_load
        self.env.filters['b64encode'] = self._base64_encode
    
    def _base64_encode(self, s):
        import base64
        return base64.b64encode(s.encode()).decode()
    
    def generate_terraform_config(self, infrastructure_spec: Dict[str, Any]) -> str:
        """Generate Terraform configuration from specification"""
        template = self.env.get_template('terraform/main.tf.j2')
        
        return template.render(
            provider=infrastructure_spec['provider'],
            resources=infrastructure_spec['resources'],
            variables=infrastructure_spec.get('variables', {}),
            outputs=infrastructure_spec.get('outputs', {})
        )
    
    def generate_kubernetes_manifests(self, app_spec: Dict[str, Any]) -> Dict[str, str]:
        """Generate Kubernetes manifests for an application"""
        manifests = {}
        
        # Generate deployment
        if 'deployment' in app_spec:
            template = self.env.get_template('kubernetes/deployment.yaml.j2')
            manifests['deployment.yaml'] = template.render(
                app=app_spec,
                deployment=app_spec['deployment']
            )
        
        # Generate service
        if 'service' in app_spec:
            template = self.env.get_template('kubernetes/service.yaml.j2')
            manifests['service.yaml'] = template.render(
                app=app_spec,
                service=app_spec['service']
            )
        
        # Generate ingress
        if 'ingress' in app_spec:
            template = self.env.get_template('kubernetes/ingress.yaml.j2')
            manifests['ingress.yaml'] = template.render(
                app=app_spec,
                ingress=app_spec['ingress']
            )
        
        # Generate configmap
        if 'config' in app_spec:
            template = self.env.get_template('kubernetes/configmap.yaml.j2')
            manifests['configmap.yaml'] = template.render(
                app=app_spec,
                config=app_spec['config']
            )
        
        return manifests
    
    def generate_docker_compose(self, services_spec: Dict[str, Any]) -> str:
        """Generate Docker Compose file from services specification"""
        template = self.env.get_template('docker/docker-compose.yaml.j2')
        
        return template.render(
            version=services_spec.get('version', '3.8'),
            services=services_spec['services'],
            networks=services_spec.get('networks', {}),
            volumes=services_spec.get('volumes', {})
        )
    
    def generate_ansible_playbook(self, playbook_spec: Dict[str, Any]) -> str:
        """Generate Ansible playbook from specification"""
        template = self.env.get_template('ansible/playbook.yaml.j2')
        
        return template.render(
            playbook_name=playbook_spec['name'],
            hosts=playbook_spec['hosts'],
            vars=playbook_spec.get('vars', {}),
            tasks=playbook_spec['tasks'],
            handlers=playbook_spec.get('handlers', [])
        )
    
    def process_environment_configs(self, base_config: Dict[str, Any], environments: List[str]) -> Dict[str, str]:
        """Generate environment-specific configurations"""
        configs = {}
        
        for env in environments:
            # Load environment-specific variables
            env_vars_file = f'environments/{env}.yaml'
            if os.path.exists(env_vars_file):
                with open(env_vars_file, 'r') as f:
                    env_vars = yaml.safe_load(f)
            else:
                env_vars = {}
            
            # Merge base config with environment variables
            config = {**base_config, **env_vars, 'environment': env}
            
            # Generate configuration for this environment
            if config['type'] == 'kubernetes':
                manifests = self.generate_kubernetes_manifests(config)
                configs[env] = manifests
            elif config['type'] == 'terraform':
                terraform_config = self.generate_terraform_config(config)
                configs[env] = {'main.tf': terraform_config}
            elif config['type'] == 'docker-compose':
                compose_config = self.generate_docker_compose(config)
                configs[env] = {'docker-compose.yaml': compose_config}
        
        return configs

# Example template files:

# templates/terraform/main.tf.j2
terraform_template = """
terraform {
  required_version = ">= 0.14"
  
  required_providers {
    {{ provider.name }} = {
      source  = "{{ provider.source }}"
      version = "{{ provider.version }}"
    }
  }
}

provider "{{ provider.name }}" {
  region = "{{ provider.region }}"
}

{% for var_name, var_config in variables.items() %}
variable "{{ var_name }}" {
  type        = {{ var_config.type }}
  description = "{{ var_config.description }}"
  {% if var_config.default is defined %}
  default     = {{ var_config.default | to_json }}
  {% endif %}
}
{% endfor %}

{% for resource in resources %}
resource "{{ resource.type }}" "{{ resource.name }}" {
  {% for key, value in resource.properties.items() %}
  {% if value is string %}
  {{ key }} = "{{ value }}"
  {% elif value is mapping %}
  {{ key }} = {{ value | to_json }}
  {% else %}
  {{ key }} = {{ value }}
  {% endif %}
  {% endfor %}
  
  {% if resource.tags is defined %}
  tags = {
    {% for tag_key, tag_value in resource.tags.items() %}
    "{{ tag_key }}" = "{{ tag_value }}"
    {% endfor %}
  }
  {% endif %}
}
{% endfor %}

{% for output_name, output_config in outputs.items() %}
output "{{ output_name }}" {
  value       = {{ output_config.value }}
  description = "{{ output_config.description }}"
  {% if output_config.sensitive %}
  sensitive   = true
  {% endif %}
}
{% endfor %}
"""

# templates/kubernetes/deployment.yaml.j2
k8s_deployment_template = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ app.name }}
  namespace: {{ app.namespace | default('default') }}
  labels:
    app: {{ app.name }}
    version: {{ app.version }}
    environment: {{ environment }}
spec:
  replicas: {{ deployment.replicas }}
  selector:
    matchLabels:
      app: {{ app.name }}
  template:
    metadata:
      labels:
        app: {{ app.name }}
        version: {{ app.version }}
    spec:
      containers:
      {% for container in deployment.containers %}
      - name: {{ container.name }}
        image: {{ container.image }}:{{ container.tag }}
        ports:
        {% for port in container.ports %}
        - containerPort: {{ port.container_port }}
          name: {{ port.name }}
        {% endfor %}
        
        {% if container.resources is defined %}
        resources:
          {% if container.resources.requests is defined %}
          requests:
            cpu: {{ container.resources.requests.cpu }}
            memory: {{ container.resources.requests.memory }}
          {% endif %}
          {% if container.resources.limits is defined %}
          limits:
            cpu: {{ container.resources.limits.cpu }}
            memory: {{ container.resources.limits.memory }}
          {% endif %}
        {% endif %}
        
        {% if container.env is defined %}
        env:
        {% for env_var in container.env %}
        - name: {{ env_var.name }}
          {% if env_var.value is defined %}
          value: "{{ env_var.value }}"
          {% elif env_var.valueFrom is defined %}
          valueFrom:
            {{ env_var.valueFrom | to_json }}
          {% endif %}
        {% endfor %}
        {% endif %}
        
        {% if container.health_check is defined %}
        livenessProbe:
          httpGet:
            path: {{ container.health_check.path }}
            port: {{ container.health_check.port }}
          initialDelaySeconds: {{ container.health_check.initial_delay | default(30) }}
          periodSeconds: {{ container.health_check.period | default(10) }}
        
        readinessProbe:
          httpGet:
            path: {{ container.health_check.path }}
            port: {{ container.health_check.port }}
          initialDelaySeconds: {{ container.health_check.initial_delay | default(5) }}
          periodSeconds: {{ container.health_check.period | default(5) }}
        {% endif %}
      {% endfor %}
      
      {% if deployment.volumes is defined %}
      volumes:
      {% for volume in deployment.volumes %}
      - name: {{ volume.name }}
        {% if volume.type == 'configMap' %}
        configMap:
          name: {{ volume.configMap.name }}
        {% elif volume.type == 'secret' %}
        secret:
          secretName: {{ volume.secret.name }}
        {% elif volume.type == 'persistentVolumeClaim' %}
        persistentVolumeClaim:
          claimName: {{ volume.pvc.name }}
        {% endif %}
      {% endfor %}
      {% endif %}
"""
