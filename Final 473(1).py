import requests
from bs4 import BeautifulSoup
import re
import nltk
from nltk.tokenize import word_tokenize
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, black  # Import color definitions

# Ensure that necessary NLTK resources are downloaded
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

def find_zip_codes(text):
    ZipRegEx = r'\b\d{5}\b'  # US-style zip codes that are 5 digits long
    return set(re.findall(ZipRegEx, text))

def find_phone_numbers(text):
    PhoneRegEx = r'(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})'
    return set(re.findall(PhoneRegEx, text))

def scrape_site(base_url):
    pages_visited = set()
    unique_images = {}
    phone_numbers = set()
    zip_codes = set()
    all_texts = ""

    def process_page(url):
        nonlocal all_texts
        if url in pages_visited or not url.startswith('https://casl.website'):
            return
        pages_visited.add(url)
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        for img in soup.find_all('img'):
            img_url = img.get('src') or img.get('data-src')
            if img_url:
                if img_url.startswith('/'):
                    img_url = 'https://casl.website' + img_url
                if img_url.startswith(('http', 'https')):
                    unique_images[img_url] = unique_images.get(img_url, 0) + 1

        text = soup.get_text()
        all_texts += text + " "
        phone_numbers.update(find_phone_numbers(text))
        zip_codes.update(find_zip_codes(text))

        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/') and 'https://casl.website' + href not in pages_visited:
                process_page('https://casl.website' + href)

    process_page(base_url)

    words = word_tokenize(all_texts)
    words = [word.lower() for word in words if word.isalpha()]
    tagged = nltk.pos_tag(words)
    nouns = {word for word, pos in tagged if pos.startswith('NN')}
    verbs = {word for word, pos in tagged if pos.startswith('VB')}
    vocabulary = set(words)

    return {
        'Unique URLs': list(pages_visited),
        'Unique Image URLs': unique_images,
        'Phone Numbers': list(phone_numbers),
        'Zip Codes': list(zip_codes),
        'Vocabulary': list(vocabulary),
        'Nouns': list(nouns),
        'Verbs': list(verbs)
    }

def create_pdf(data):
    c = canvas.Canvas("scraped_data_report.pdf", pagesize=letter)
    width, height = letter
    page_count = 0
    y_position = height - 40

    def check_overflow():
        nonlocal y_position, page_count
        if y_position < 40:
            if page_count < 9:  # Limit to 10 pages
                page_count += 1
                c.showPage()
                y_position = height - 40
            else:
                return False
        return True

    def add_content(section_title, content_list, highlight_red=False):
        nonlocal y_position
        if not check_overflow():
            return
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y_position, f"{section_title}:")
        y_position -= 20
        c.setFont("Helvetica", 10)
        for item in content_list:
            if not check_overflow():
                break
            if highlight_red:
                c.setFillColor(red)  # Set text color to red for nouns
            else:
                c.setFillColor(black)  # Ensure other text is black
            c.drawString(60, y_position, item)
            y_position -= 14
        c.setFillColor(black)  # Reset text color to black after highlighting

    # Add sections to the PDF
    add_content("Unique URLs", sorted(data['Unique URLs']))
    add_content("Unique Image URLs", [f"{url}: {count}" for url, count in sorted(data['Unique Image URLs'].items())])
    add_content("Phone Numbers", sorted(data['Phone Numbers']))
    add_content("Zip Codes", sorted(data['Zip Codes']))
    add_content("Vocabulary", sorted(data['Vocabulary']))
    add_content("Nouns", sorted(data['Nouns']), highlight_red=True)  # Highlight nouns in red
    add_content("Verbs", sorted(data['Verbs']))

    c.showPage()
    c.save()
    print(f"PDF saved in: {os.getcwd()}")

# Run the scraper and generate PDF report
results = scrape_site('https://casl.website/')
create_pdf(results)
