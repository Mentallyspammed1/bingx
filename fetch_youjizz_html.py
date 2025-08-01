import requests

url = 'https://www.youjizz.com/search/deepthroat-1.html'
response = requests.get(url)

with open('youjizz_search_deepthroat.html', 'w', encoding='utf-8') as f:
    f.write(response.text)