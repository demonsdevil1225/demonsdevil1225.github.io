import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "https://www.menshealth.com/sex-women/a19547362/45-sex-positions-guys-should-know/"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')

    if not os.path.exists("images"):
        os.makedirs("images")

    img_tags = soup.find_all('img')
    for i, img in enumerate(img_tags):
        img_url = img.get('src') or img.get('data-src')
        if img_url:
            img_url = urljoin(url, img_url)
            filename = f"image_{i}.jpg"
            full_path = os.path.join(os.getcwd(), "images", filename)
            try:
                image_response = requests.get(img_url, headers=headers, timeout=10)
                with open(full_path, 'wb') as file:
                    file.write(image_response.content)
                print(f"Downloaded: {filename}")
            except Exception as e:
                print(f"Failed to download {img_url}: {e}")

    article_body = soup.find('div', class_='article-content-body')
    if article_body:
        body_content = article_body.get_text()
        with open("body_content.txt", "w", encoding="utf-8") as text_file:
            text_file.write(body_content)
        print("Saved body content to body_content.txt")
    else:
        print("Could not find article body content")

else:
    print(f"Failed to retrieve page. Status code: {response.status_code}")
