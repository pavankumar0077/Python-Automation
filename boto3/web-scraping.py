import requests
from bs4 import BeautifulSoup

def scrape_headlines_demo(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    headlines = soup.find_all('h2')
    for idx, headline in enumerate(headlines, 1):
        print(f'{idx}: {headline.text.strip()}')

# Example usage
scrape_headlines_demo('https://www.indiatoday.in/india')
