from jinja2 import Environment, FileSystemLoader, select_autoescape
import yaml
import json
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

@dataclass
class ResourceSpec:
    name: str
    type: str
    properties: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class InfrastructureSpec:
    name: str
    cloud_provider: str
    region: str
    resources: List[ResourceSpec]
    variables: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)

class CloudTemplateGenerator(ABC):
    @abstractmethod
    def generate_template(self, spec: InfrastructureSpec) -> Dict[str, str]:
        pass
    
    @abstractmethod
    def validate_spec(self, spec: InfrastructureSpec) -> List[str]:
        pass

class AWSTemplateGenerator(CloudTemplateGenerator):
    def __init__(self, templates_dir: str):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.env.filters['to_json'] = json.dumps
    
    def generate_template(self, spec: InfrastructureSpec) -> Dict[str, str]:
        templates = {}
        
        # Generate Terraform main configuration
        main_template = self.env.get_template('aws/main.tf.j2')
        templates['main.tf'] = main_template.render(
            spec=spec,
            resources=self._group_resources_by_type(spec.resources)
        )
        
        # Generate variables file
        if spec.variables:
            vars_template = self.env.get_template('aws/variables.tf.j2')
            templates['variables.tf'] = vars_template.render(variables=spec.variables)
        
        # Generate outputs file
        if spec.outputs:
            outputs_template = self.env.get_template('aws/outputs.tf.j2')
            templates['outputs.tf'] = outputs_template.render(outputs=spec.outputs)
        
        # Generate terraform.tfvars for different environments
        templates['terraform.tfvars'] = self._generate_tfvars(spec)
        
        return templates
    
    def validate_spec(self, spec: InfrastructureSpec) -> List[str]:
        errors = []
        
        # Check for required AWS-specific properties
        for resource in spec.resources:
            if resource.type.startswith('aws_'):
                if 'region' not in resource.properties and 'region' not in spec.variables:
                    errors.append(f"Resource {resource.name}: AWS region not specified")
        
        # Check dependencies
        resource_names = {r.name for r in spec.resources}
        for resource in spec.resources:
            for dep in resource.dependencies:
                if dep not in resource_names:
                    errors.append(f"Resource {resource.name}: dependency {dep} not found")
        
        return errors
    
    def _group_resources_by_type(self, resources: List[ResourceSpec]) -> Dict[str, List[ResourceSpec]]:
        grouped = {}
        for resource in resources:
            if resource.type not in grouped:
                grouped[resource.type] = []
            grouped[resource.type].append(resource)
        return grouped
    
    def _generate_tfvars(self, spec: InfrastructureSpec) -> str:
        tfvars_lines = []
        for var_name, var_config in spec.variables.items():
            if 'default' in var_config:
                value = var_config['default']
                if isinstance(value, str):
                    tfvars_lines.append(f'{var_name} = "{value}"')
                else:
                    tfvars_lines.append(f'{var_name} = {json.dumps(value)}')
        return '\n'.join(tfvars_lines)

class AzureTemplateGenerator(CloudTemplateGenerator):
    def __init__(self, templates_dir: str):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.env.filters['to_json'] = json.dumps
    
    def generate_template(self, spec: InfrastructureSpec) -> Dict[str, str]:
        templates = {}
        
        # Generate ARM template
        arm_template = self.env.get_template('azure/azuredeploy.json.j2')
        templates['azuredeploy.json'] = arm_template.render(spec=spec)
        
        # Generate parameters file
        params_template = self.env.get_template('azure/azuredeploy.parameters.json.j2')
        templates['azuredeploy.parameters.json'] = params_template.render(spec=spec)
        
        return templates
    
    def validate_spec(self, spec: InfrastructureSpec) -> List[str]:
        errors = []
        
        # Azure-specific validations
        for resource in spec.resources:
            if resource.type.startswith('Microsoft.'):
                if 'location' not in resource.properties and 'location' not in spec.variables:
                    errors.append(f"Resource {resource.name}: Azure location not specified")
        
        return errors

class GCPTemplateGenerator(CloudTemplateGenerator):
    def __init__(self, templates_dir: str):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.env.filters['to_json'] = json.dumps
    
    def generate_template(self, spec: InfrastructureSpec) -> Dict[str, str]:
        templates = {}
        
        # Generate Deployment Manager template
        dm_template = self.env.get_template('gcp/deployment.yaml.j2')
        templates['deployment.yaml'] = dm_template.render(spec=spec)
        
        # Generate Terraform configuration for GCP
        tf_template = self.env.get_template('gcp/main.tf.j2')
        templates['main.tf'] = tf_template.render(spec=spec)
        
        return templates
    
    def validate_spec(self, spec: InfrastructureSpec) -> List[str]:
        errors = []
        
        # GCP-specific validations
        for resource in spec.resources:
            if resource.type.startswith('google_'):
                if 'project' not in resource.properties and 'project' not in spec.variables:
                    errors.append(f"Resource {resource.name}: GCP project not specified")
        
        return errors

class MultiCloudInfrastructureGenerator:
    def __init__(self, templates_dir: str = 'templates'):
        self.generators = {
            'aws': AWSTemplateGenerator(templates_dir),
            'azure': AzureTemplateGenerator(templates_dir),
            'gcp': GCPTemplateGenerator(templates_dir)
        }
        
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def load_infrastructure_spec(self, spec_file: str) -> InfrastructureSpec:
        """Load infrastructure specification from YAML file"""
        with open(spec_file, 'r') as f:
            spec_data = yaml.safe_load(f)
        
        resources = [
            ResourceSpec(
                name=r['name'],
                type=r['type'],
                properties=r['properties'],
                dependencies=r.get('dependencies', []),
                tags=r.get('tags', {})
            )
            for r in spec_data.get('resources', [])
        ]
        
        return InfrastructureSpec(
            name=spec_data['name'],
            cloud_provider=spec_data['cloud_provider'],
            region=spec_data['region'],
            resources=resources,
            variables=spec_data.get('variables', {}),
            outputs=spec_data.get('outputs', {})
        )
    
    def generate_infrastructure(self, spec_file: str, output_dir: str, environments: List[str] = None) -> Dict[str, Any]:
        """Generate infrastructure templates for multiple environments"""
        spec = self.load_infrastructure_spec(spec_file)
        
        # Validate specification
        generator = self.generators[spec.cloud_provider]
        validation_errors = generator.validate_spec(spec)
        
        if validation_errors:
            return {
                'status': 'error',
                'errors': validation_errors
            }
        
        environments = environments or ['dev', 'staging', 'prod']
        generated_files = {}
        
        for env in environments:
            env_spec = self._customize_spec_for_environment(spec, env)
            
            # Generate templates
            templates = generator.generate_template(env_spec)
            
            # Write templates to files
            env_dir = os.path.join(output_dir, env)
            os.makedirs(env_dir, exist_ok=True)
            
            env_files = []
            for filename, content in templates.items():
                file_path = os.path.join(env_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                env_files.append(file_path)
            
            generated_files[env] = env_files
        
        # Generate common files (README, deployment scripts, etc.)
        self._generate_common_files(spec, output_dir)
        
        return {
            'status': 'success',
            'generated_files': generated_files,
            'cloud_provider': spec.cloud_provider
        }
    
    def _customize_spec_for_environment(self, base_spec: InfrastructureSpec, environment: str) -> InfrastructureSpec:
        """Customize specification for specific environment"""
        
        # Load environment-specific overrides
        env_overrides_file = f'environments/{environment}.yaml'
        env_overrides = {}
        
        if os.path.exists(env_overrides_file):
            with open(env_overrides_file, 'r') as f:
                env_overrides = yaml.safe_load(f)
        
        # Create environment-specific spec
        env_resources = []
        for resource in base_spec.resources:
            env_resource = ResourceSpec(
                name=f"{resource.name}-{environment}",
                type=resource.type,
                properties={**resource.properties},
                dependencies=resource.dependencies.copy(),
                tags={**resource.tags, 'Environment': environment}
            )
            
            # Apply environment-specific overrides
            if resource.name in env_overrides.get('resources', {}):
                resource_overrides = env_overrides['resources'][resource.name]
                env_resource.properties.update(resource_overrides.get('properties', {}))
                env_resource.tags.update(resource_overrides.get('tags', {}))
            
            env_resources.append(env_resource)
        
        # Merge variables with environment overrides
        env_variables = {**base_spec.variables}
        if 'variables' in env_overrides:
            env_variables.update(env_overrides['variables'])
        
        return InfrastructureSpec(
            name=f"{base_spec.name}-{environment}",
            cloud_provider=base_spec.cloud_provider,
            region=base_spec.region,
            resources=env_resources,
            variables=env_variables,
            outputs=base_spec.outputs
        )
    
    def _generate_common_files(self, spec: InfrastructureSpec, output_dir: str):
        """Generate common files like README, deployment scripts"""
        
        # Generate README
        readme_template = self.env.get_template('common/README.md.j2')
        readme_content = readme_template.render(spec=spec)
        
        with open(os.path.join(output_dir, 'README.md'), 'w') as f:
            f.write(readme_content)
        
        # Generate deployment script
        deploy_script_template = self.env.get_template(f'common/deploy-{spec.cloud_provider}.sh.j2')
        deploy_script = deploy_script_template.render(spec=spec)
        
        script_path = os.path.join(output_dir, 'deploy.sh')
        with open(script_path, 'w') as f:
            f.write(deploy_script)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        # Generate Makefile for common tasks
        makefile_template = self.env.get_template('common/Makefile.j2')
        makefile_content = makefile_template.render(
            spec=spec,
            environments=['dev', 'staging', 'prod']
        )
        
        with open(os.path.join(output_dir, 'Makefile'), 'w') as f:
            f.write(makefile_content)

# Usage example
if __name__ == "__main__":
    generator = MultiCloudInfrastructureGenerator()
    
    result = generator.generate_infrastructure(
        spec_file='infrastructure-spec.yaml',
        output_dir='generated-infrastructure',
        environments=['dev', 'staging', 'prod']
    )
    
    if result['status'] == 'success':
        print(f"Infrastructure templates generated for {result['cloud_provider']}")
        for env, files in result['generated_files'].items():
            print(f"  {env}: {len(files)} files generated")
    else:
        print("Generation failed:")
        for error in result['errors']:
            print(f"  - {error}")
