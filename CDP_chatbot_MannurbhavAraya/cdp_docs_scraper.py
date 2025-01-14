import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse
import time
import logging
from concurrent.futures import ThreadPoolExecutor
import re

class CDPDocScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraping.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_doc_structure(self, url, content, title, platform):
        """Create a structured document with metadata"""
        return {
            'url': url,
            'title': title,
            'platform': platform,
            'content': content,
            'type': self.classify_content(title, content),
            'keywords': self.extract_keywords(title, content),
            'howto_steps': self.extract_steps(content),
            'metadata': {
                'last_updated': None,  # To be filled if available
                'category': self.determine_category(title, content),
                'difficulty_level': self.estimate_difficulty(content)
            }
        }

    def classify_content(self, title, content):
        """Classify the type of documentation page"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        if any(word in title_lower for word in ['how to', 'guide', 'tutorial']):
            return 'how-to'
        elif any(word in title_lower for word in ['api', 'reference', 'sdk']):
            return 'technical-reference'
        elif any(word in title_lower for word in ['concept', 'overview', 'introduction']):
            return 'conceptual'
        return 'general'

    def extract_keywords(self, title, content):
        """Extract relevant keywords from the content"""
        # Common CDP-related terms
        cdp_terms = ['segment', 'audience', 'profile', 'integration', 'source', 'destination',
                    'tracking', 'identity', 'data', 'analytics', 'api']
        
        # Extract words that might be important
        words = re.findall(r'\b\w+\b', f"{title} {content}".lower())
        return list(set([word for word in words if word in cdp_terms or len(word) > 4]))

    def extract_steps(self, content):
        """Extract numbered steps or bullet points from content"""
        steps = []
        # Look for numbered steps
        numbered_steps = re.findall(r'\d+\.\s+(.*?)(?=\d+\.|$)', content, re.DOTALL)
        if numbered_steps:
            steps.extend(numbered_steps)
        
        # Look for bullet points
        bullet_points = re.findall(r'[•\-\*]\s+(.*?)(?=[•\-\*]|$)', content, re.DOTALL)
        if bullet_points:
            steps.extend(bullet_points)
            
        return [step.strip() for step in steps if step.strip()]

    def determine_category(self, title, content):
        """Determine the category of the documentation"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        categories = {
            'setup': ['setup', 'installation', 'getting started'],
            'integration': ['integrate', 'connection', 'connector'],
            'user_management': ['user', 'profile', 'identity'],
            'data_management': ['data', 'schema', 'model'],
            'analytics': ['analytics', 'reporting', 'dashboard'],
            'security': ['security', 'privacy', 'authentication']
        }
        
        for category, keywords in categories.items():
            if any(keyword in title_lower or keyword in content_lower for keyword in keywords):
                return category
        return 'general'

    def estimate_difficulty(self, content):
        """Estimate the difficulty level of the content"""
        technical_terms = ['api', 'sdk', 'code', 'implementation', 'configuration']
        technical_count = sum(term in content.lower() for term in technical_terms)
        
        if technical_count > 5:
            return 'advanced'
        elif technical_count > 2:
            return 'intermediate'
        return 'beginner'

    def scrape_segment(self, base_url="https://segment.com/docs/"):
        return self._scrape_platform('segment', base_url)

    def scrape_mparticle(self, base_url="https://docs.mparticle.com/"):
        return self._scrape_platform('mparticle', base_url)

    def scrape_lytics(self, base_url="https://docs.lytics.com/"):
        return self._scrape_platform('lytics', base_url)

    def scrape_zeotap(self, base_url="https://docs.zeotap.com/"):
        return self._scrape_platform('zeotap', base_url)

    def _scrape_platform(self, platform_name, base_url):
        """Generic platform scraping method"""
        self.logger.info(f"Starting to scrape {platform_name} documentation...")
        docs = []
        visited = set()
        
        def is_valid_url(url):
            parsed = urlparse(url)
            return (
                parsed.netloc.endswith(urlparse(base_url).netloc) and
                not any(ext in url for ext in ['.png', '.jpg', '.gif', '.pdf']) and
                not any(pattern in url for pattern in ['login', 'sign-in', 'search'])
            )

        def process_page(url):
            if url in visited or not is_valid_url(url):
                return []
            
            visited.add(url)
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code != 200:
                    self.logger.warning(f"Failed to fetch {url}: {response.status_code}")
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract main content (adjust selectors based on the platform's HTML structure)
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if not main_content:
                    return []
                
                # Clean the content
                for tag in main_content(['script', 'style', 'nav', 'header', 'footer']):
                    tag.decompose()
                
                content = main_content.get_text(strip=True, separator=' ')
                title = soup.title.string if soup.title else url.split('/')[-1]
                
                # Create structured document
                doc = self.create_doc_structure(url, content, title, platform_name)
                docs.append(doc)
                
                # Find more links to scrape
                links = main_content.find_all('a', href=True)
                return [urljoin(base_url, link['href']) for link in links]
            
            except Exception as e:
                self.logger.error(f"Error processing {url}: {str(e)}")
                return []

        # Start with the base URL
        urls_to_process = [base_url]
        
        # Process URLs in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            while urls_to_process:
                new_urls = []
                future_to_url = {executor.submit(process_page, url): url 
                               for url in urls_to_process[:5]}  # Process 5 at a time
                
                for future in future_to_url:
                    new_urls.extend(future.result())
                
                urls_to_process = list(set(new_urls) - visited)
                
                # Add delay to be respectful to the servers
                time.sleep(1)
        
        # Save the results
        output_file = f"{platform_name}_docs.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Completed scraping {platform_name}. Found {len(docs)} documents.")
        return docs

def main():
    scraper = CDPDocScraper()
    
    # Create output directory if it doesn't exist
    os.makedirs('cdp_docs', exist_ok=True)
    
    # Scrape all platforms
    platforms = {
        'segment': "https://segment.com/docs/",
        'mparticle': "https://docs.mparticle.com/",
        'lytics': "https://docs.lytics.com/",
        'zeotap': "https://docs.zeotap.com/"
    }
    
    for platform, url in platforms.items():
        try:
            docs = getattr(scraper, f"scrape_{platform}")(url)
            
            # Save platform-specific data
            output_file = os.path.join('cdp_docs', f"{platform}_docs.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(docs, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            scraper.logger.error(f"Failed to scrape {platform}: {str(e)}")

if __name__ == "__main__":
    main()
