import requests
import time
import json
from datetime import datetime

class APIHealthMonitor:
    def __init__(self, endpoints):
        self.endpoints = endpoints
        self.results = []
    
    def check_endpoint(self, url, expected_status=200, timeout=10):
        try:
            start_time = time.time()
            response = requests.get(url, timeout=timeout)
            response_time = time.time() - start_time
            
            return {
                'url': url,
                'status_code': response.status_code,
                'response_time': response_time,
                'is_healthy': response.status_code == expected_status,
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            return {
                'url': url,
                'error': str(e),
                'is_healthy': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def monitor_all_endpoints(self):
        for endpoint in self.endpoints:
            result = self.check_endpoint(endpoint['url'], endpoint.get('expected_status', 200))
            self.results.append(result)
            print(f"Checked {endpoint['url']}: {'✓' if result['is_healthy'] else '✗'}")
        
        return self.results
