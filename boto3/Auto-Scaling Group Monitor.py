import boto3
import json

class ASGMonitor:
    def __init__(self):
        self.asg_client = boto3.client('autoscaling')
        self.cloudwatch = boto3.client('cloudwatch')
    
    def get_asg_health(self, asg_name):
        response = self.asg_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
        )
        
        for asg in response['AutoScalingGroups']:
            healthy_instances = len([i for i in asg['Instances'] if i['HealthStatus'] == 'Healthy'])
            return {
                'name': asg['AutoScalingGroupName'],
                'desired': asg['DesiredCapacity'],
                'healthy': healthy_instances,
                'total': len(asg['Instances'])
            }
    
    def scale_asg(self, asg_name, desired_capacity):
        return self.asg_client.update_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            DesiredCapacity=desired_capacity
        )
