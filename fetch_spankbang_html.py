import requests

url = 'https://spankbang.com/s/deepthroat/1/'
response = requests.get(url)

with open('spankbang_search_deepthroat.html', 'w', encoding='utf-8') as f:
    f.write(response.text)