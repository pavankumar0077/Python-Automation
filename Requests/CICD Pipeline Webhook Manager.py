import requests
import json
import time
from typing import Dict, List, Optional

class CICDWebhookManager:
    def __init__(self, config: Dict):
        self.config = config
        self.jenkins_url = config['jenkins']['url']
        self.jenkins_user = config['jenkins']['username']
        self.jenkins_token = config['jenkins']['token']
        self.github_token = config['github']['token']
    
    def trigger_jenkins_build(self, job_name: str, parameters: Optional[Dict] = None):
        url = f"{self.jenkins_url}/job/{job_name}/buildWithParameters"
        
        auth = (self.jenkins_user, self.jenkins_token)
        data = parameters or {}
        
        response = requests.post(url, auth=auth, data=data)
        
        if response.status_code == 201:
            # Get build number from queue
            queue_url = response.headers.get('Location')
            return self.wait_for_build_start(queue_url)
        else:
            raise Exception(f"Failed to trigger build: {response.text}")
    
    def wait_for_build_start(self, queue_url: str, timeout: int = 300):
        auth = (self.jenkins_user, self.jenkins_token)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = requests.get(f"{queue_url}api/json", auth=auth)
            queue_item = response.json()
            
            if 'executable' in queue_item:
                build_number = queue_item['executable']['number']
                job_url = queue_item['executable']['url']
                return {'build_number': build_number, 'job_url': job_url}
            
            time.sleep(5)
        
        raise Exception("Timeout waiting for build to start")
    
    def get_build_status(self, job_name: str, build_number: int):
        url = f"{self.jenkins_url}/job/{job_name}/{build_number}/api/json"
        auth = (self.jenkins_user, self.jenkins_token)
        
        response = requests.get(url, auth=auth)
        build_info = response.json()
        
        return {
            'number': build_info['number'],
            'result': build_info['result'],
            'building': build_info['building'],
            'duration': build_info['duration'],
            'timestamp': build_info['timestamp']
        }
    
    def update_github_status(self, repo: str, commit_sha: str, state: str, description: str):
        url = f"https://api.github.com/repos/{repo}/statuses/{commit_sha}"
        
        headers = {
            'Authorization': f"token {self.github_token}",
            'Accept': 'application/vnd.github.v3+json'
        }
        
        data = {
            'state': state,  # pending, success, error, failure
            'description': description,
            'context': 'continuous-integration/jenkins'
        }
        
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 201
    
    def deployment_pipeline(self, repo: str, branch: str, environment: str):
        pipeline_steps = [
            {'job': 'build-and-test', 'stage': 'Build & Test'},
            {'job': 'security-scan', 'stage': 'Security Scan'},
            {'job': f'deploy-{environment}', 'stage': f'Deploy to {environment}'}
        ]
        
        results = []
        
        for step in pipeline_steps:
            print(f"Executing: {step['stage']}")
            
            try:
                build_info = self.trigger_jenkins_build(
                    step['job'],
                    {'BRANCH': branch, 'ENVIRONMENT': environment}
                )
                
                # Wait for completion
                while True:
                    status = self.get_build_status(step['job'], build_info['build_number'])
                    
                    if not status['building']:
                        results.append({
                            'stage': step['stage'],
                            'result': status['result'],
                            'duration': status['duration']
                        })
                        break
                    
                    time.sleep(10)
                
                if status['result'] != 'SUCCESS':
                    print(f"Pipeline failed at: {step['stage']}")
                    break
                    
            except Exception as e:
                results.append({
                    'stage': step['stage'],
                    'result': 'FAILED',
                    'error': str(e)
                })
                break
        
        return results
