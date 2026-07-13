import requests
from bs4 import BeautifulSoup
import re

url = "https://www.menshealth.com/sex-women/a19547362/45-sex-positions-guys-should-know/"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    with open("45_sex_positions.txt", "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("45 SEX POSITIONS GUYS SHOULD KNOW\n")
        f.write("Source: Men's Health\n")
        f.write("=" * 60 + "\n\n")
        
        # Find all h2 headers (position names) and their content
        headings = soup.find_all(['h2', 'h3'])
        
        position_count = 0
        for heading in headings:
            text = heading.get_text(strip=True)
            # Look for numbered positions or position-like headers
            if re.match(r'^\d+[\.\)]\s', text) or 'position' in text.lower():
                position_count += 1
                f.write("-" * 40 + "\n")
                f.write(f"POSITION {position_count}\n")
                f.write(f"Name: {text}\n")
                
                # Get the next sibling elements for content
                next_elem = heading.find_next_sibling()
                while next_elem and next_elem.name not in ['h2', 'h3']:
                    content = next_elem.get_text(strip=True)
                    if content:
                        # Check for "Also Known As" or "Benefits"
                        if 'also known' in content.lower() or 'aka' in content.lower():
                            f.write(f"Also Known As: {content}\n")
                        elif 'benefit' in content.lower():
                            f.write(f"Benefits: {content}\n")
                        else:
                            f.write(f"Details: {content}\n")
                    next_elem = next_elem.find_next_sibling()
                f.write("\n")
        
        # If no structured positions found, extract all content
        if position_count == 0:
            f.write("Extracting article content...\n\n")
            
            # Try multiple possible content containers
            content_div = None
            for class_name in ['article-body', 'article-content', 'content-body', 'article__body', 'body-content']:
                content_div = soup.find('div', class_=lambda x: x and class_name in str(x).lower())
                if content_div:
                    break
            
            if not content_div:
                content_div = soup.find('article') or soup.find('main')
            
            if content_div:
                # Extract text with formatting
                for elem in content_div.find_all(['h2', 'h3', 'h4', 'p', 'li']):
                    text = elem.get_text(strip=True)
                    if text:
                        if elem.name in ['h2', 'h3', 'h4']:
                            f.write(f"\n{'=' * 40}\n")
                            f.write(f"{text}\n")
                            f.write(f"{'=' * 40}\n")
                        elif elem.name == 'li':
                            f.write(f"• {text}\n")
                        else:
                            f.write(f"{text}\n\n")
            else:
                # Fallback: get all text
                body = soup.find('body')
                if body:
                    # Remove script and style elements
                    for tag in body.find_all(['script', 'style', 'nav', 'header', 'footer']):
                        tag.decompose()
                    f.write(body.get_text(separator='\n', strip=True))
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("END OF DOCUMENT\n")
        f.write("=" * 60 + "\n")
    
    print(f"Extracted content to 45_sex_positions.txt")
    
    # Also save raw HTML for debugging
    with open("page_source.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved page source to page_source.html")
    
else:
    print(f"Failed to retrieve page. Status code: {response.status_code}")
