import requests
import concurrent.futures
import json
import time
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

@dataclass
class ResourceMetric:
    resource_id: str
    resource_type: str
    cloud_provider: str
    region: str
    metric_name: str
    value: float
    unit: str
    timestamp: str

class CloudProvider(ABC):
    @abstractmethod
    def get_resources(self) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_metrics(self, resource_id: str) -> List[ResourceMetric]:
        pass

class AWSProvider(CloudProvider):
    def __init__(self, access_key: str, secret_key: str, region: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.base_url = f"https://monitoring.{region}.amazonaws.com"
    
    def get_resources(self) -> List[Dict]:
        # Implementation would use AWS API
        # This is a simplified example
        return [
            {'id': 'i-1234567890abcdef0', 'type': 'EC2Instance', 'region': self.region},
            {'id': 'vol-0123456789abcdef0', 'type': 'EBSVolume', 'region': self.region}
        ]
    
    def get_metrics(self, resource_id: str) -> List[ResourceMetric]:
        # Simulate CloudWatch API call
        metrics = []
        
        if resource_id.startswith('i-'):  # EC2 Instance
            metrics.append(ResourceMetric(
                resource_id=resource_id,
                resource_type='EC2Instance',
                cloud_provider='AWS',
                region=self.region,
                metric_name='CPUUtilization',
                value=45.2,
                unit='Percent',
                timestamp=time.time()
            ))
        
        return metrics

class MultiCloudResourceMonitor:
    def __init__(self, providers: Dict[str, CloudProvider]):
        self.providers = providers
        self.metrics_store = []
        self.alert_thresholds = {
            'CPUUtilization': 80.0,
            'MemoryUtilization': 85.0,
            'DiskUtilization': 90.0
        }
    
    def collect_all_metrics(self) -> List[ResourceMetric]:
        all_metrics = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_provider = {}
            
            for provider_name, provider in self.providers.items():
                resources = provider.get_resources()
                
                for resource in resources:
                    future = executor.submit(provider.get_metrics, resource['id'])
                    future_to_provider[future] = (provider_name, resource)
            
            for future in concurrent.futures.as_completed(future_to_provider):
                provider_name, resource = future_to_provider[future]
                try:
                    metrics = future.result()
                    all_metrics.extend(metrics)
                except Exception as e:
                    print(f"Error collecting metrics for {resource['id']}: {e}")
        
        self.metrics_store.extend(all_metrics)
        return all_metrics
    
    def check_alerts(self, metrics: List[ResourceMetric]) -> List[Dict]:
        alerts = []
        
        for metric in metrics:
            threshold = self.alert_thresholds.get(metric.metric_name)
            if threshold and metric.value > threshold:
                alerts.append({
                    'resource_id': metric.resource_id,
                    'cloud_provider': metric.cloud_provider,
                    'region': metric.region,
                    'metric': metric.metric_name,
                    'current_value': metric.value,
                    'threshold': threshold,
                    'severity': 'critical' if metric.value > threshold * 1.2 else 'warning'
                })
        
        return alerts
    
    def send_alerts(self, alerts: List[Dict]):
        webhook_urls = [
            'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK',
            'https://api.pagerduty.com/incidents'
        ]
        
        for alert in alerts:
            message = {
                'text': f"🚨 Alert: {alert['metric']} on {alert['resource_id']} "
                       f"is {alert['current_value']}{alert.get('unit', '')} "
                       f"(threshold: {alert['threshold']})",
                'severity': alert['severity'],
                'cloud_provider': alert['cloud_provider'],
                'region': alert['region']
            }
            
            for webhook_url in webhook_urls:
                try:
                    response = requests.post(webhook_url, json=message, timeout=10)
                    print(f"Alert sent to {webhook_url}: {response.status_code}")
                except Exception as e:
                    print(f"Failed to send alert to {webhook_url}: {e}")
    
    def generate_report(self) -> Dict:
        if not self.metrics_store:
            return {'error': 'No metrics available'}
        
        # Aggregate metrics by cloud provider
        provider_summary = {}
        for metric in self.metrics_store:
            provider = metric.cloud_provider
            if provider not in provider_summary:
                provider_summary[provider] = {
                    'total_resources': set(),
                    'avg_cpu': [],
                    'regions': set()
                }
            
            provider_summary[provider]['total_resources'].add(metric.resource_id)
            provider_summary[provider]['regions'].add(metric.region)
            
            if metric.metric_name == 'CPUUtilization':
                provider_summary[provider]['avg_cpu'].append(metric.value)
        
        # Calculate averages
        for provider in provider_summary:
            provider_summary[provider]['total_resources'] = len(provider_summary[provider]['total_resources'])
            provider_summary[provider]['regions'] = list(provider_summary[provider]['regions'])
            
            cpu_values = provider_summary[provider]['avg_cpu']
            provider_summary[provider]['avg_cpu'] = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        
        return {
            'timestamp': time.time(),
            'total_metrics_collected': len(self.metrics_store),
            'provider_summary': provider_summary,
            'last_collection_time': max(m.timestamp for m in self.metrics_store) if self.metrics_store else None
        }
