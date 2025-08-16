import docker
import json
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class SecurityVulnerability:
    severity: str
    package: str
    vulnerability: str
    fixed_version: Optional[str]

class ContainerSecurityManager:
    def __init__(self):
        self.client = docker.from_env()
    
    def scan_image_vulnerabilities(self, image_name: str) -> List[SecurityVulnerability]:
        # Using Trivy for vulnerability scanning
        try:
            result = subprocess.run([
                'trivy', 'image', '--format', 'json', image_name
            ], capture_output=True, text=True, check=True)
            
            scan_results = json.loads(result.stdout)
            vulnerabilities = []
            
            for result in scan_results.get('Results', []):
                for vuln in result.get('Vulnerabilities', []):
                    vulnerabilities.append(SecurityVulnerability(
                        severity=vuln.get('Severity'),
                        package=vuln.get('PkgName'),
                        vulnerability=vuln.get('VulnerabilityID'),
                        fixed_version=vuln.get('FixedVersion')
                    ))
            
            return vulnerabilities
        except subprocess.CalledProcessError as e:
            print(f"Error scanning image: {e}")
            return []
    
    def check_container_compliance(self, container_id: str) -> Dict:
        container = self.client.containers.get(container_id)
        config = container.attrs['Config']
        
        compliance_checks = {
            'runs_as_root': config.get('User') == '' or config.get('User') is None,
            'privileged': container.attrs['HostConfig'].get('Privileged', False),
            'has_capabilities': len(container.attrs['HostConfig'].get('CapAdd', [])) > 0,
            'readonly_rootfs': container.attrs['HostConfig'].get('ReadonlyRootfs', False),
            'no_new_privileges': container.attrs['HostConfig'].get('SecurityOpt', [])
        }
        
        return compliance_checks
    
    def remediate_container_security(self, image_name: str, vulnerabilities: List[SecurityVulnerability]):
        # Generate Dockerfile with security fixes
        dockerfile_content = f"""
FROM {image_name}

# Security remediations
RUN apt-get update && apt-get upgrade -y
"""
        
        # Add specific package updates for fixable vulnerabilities
        fixable_packages = [v.package for v in vulnerabilities if v.fixed_version]
        if fixable_packages:
            dockerfile_content += f"RUN apt-get install -y {' '.join(fixable_packages)}\n"
        
        dockerfile_content += """
# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Remove unnecessary packages
RUN apt-get autoremove -y && apt-get clean
"""
        
        # Build secured image
        secured_image = self.client.images.build(
            fileobj=dockerfile_content.encode(),
            tag=f"{image_name}-secured",
            rm=True
        )
        
        return secured_image[0].id
