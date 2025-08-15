import requests
import subprocess
def get_weather_data(city):
 api_key = 'your_weatherapi_key'
 base_url = f'http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}'
 response = requests.get(base_url)
 data = response.json()
 if 'error' not in data:
 weather = data['current']['condition']['text']
 temp_c = data['current']['temp_c']
 print(f'Weather in {city}: {weather}, Temperature: {temp_c}°C')
 if "Heavy rain" in weather:
 print("Scaling up AKS pods due to heavy rain.")
 scale_aks_pods('default', 'my-app', 3)
def scale_aks_pods(namespace, deployment_name, replicas):
 subprocess.run(['kubectl', 'scale', f'deployment/{deployment_name}', f'--replicas={replicas}', '-n',
namespace], check=True)
 print(f"Scaled {deployment_name} to {replicas} pods.")
# Example usage
get_weather_data('London')
