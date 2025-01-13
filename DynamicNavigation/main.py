import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re
from urllib.parse import urljoin
import pickle
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Cache:
    """Simple file-based cache system"""
    def __init__(self, cache_file: str = 'doc_cache.pkl', expiry_hours: int = 24):
        self.cache_file = cache_file
        self.expiry_delta = timedelta(hours=expiry_hours)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        try:
            with open(self.cache_file, 'rb') as f:
                return pickle.load(f)
        except:
            return {}

    def _save_cache(self):
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.cache, f)

    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            content, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.expiry_delta:
                return content
            else:
                del self.cache[key]
                self._save_cache()
        return None

    def set(self, key: str, content: str):
        self.cache[key] = (content, datetime.now())
        self._save_cache()

class DocumentationHelper:
    def __init__(self):
        # Documentation URLs
        self.docs = {
            'segment': 'https://segment.com/docs/?ref=nav',
            'mparticle': 'https://docs.mparticle.com/',
            'lytics': 'https://docs.lytics.com/',
            'zeotap': 'https://docs.zeotap.com/home/en-us/'
        }

        # Simple keyword mapping for platform identification
        self.platform_keywords = {
            'segment': ['segment'],
            'mparticle': ['mparticle'],
            'lytics': ['lytics'],
            'zeotap': ['zeotap']
        }

        self.cache = Cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def identify_platform(self, question: str) -> Optional[str]:
        """Identify platform using simple keyword matching"""
        question_lower = question.lower()
        
        for platform, keywords in self.platform_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return platform
        return None

    def _clean_text(self, text: str) -> str:
        """Clean scraped text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters
        text = re.sub(r'[^\w\s.,?!-]', '', text)
        return text

    def scrape_documentation(self, url: str, search_term: str) -> List[Dict]:
        """Scrape documentation with basic caching"""
        cache_key = f"{url}_{search_term}"
        cached_content = self.cache.get(cache_key)
        
        if cached_content:
            return cached_content

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find relevant sections (adjust selectors based on site structure)
            relevant_sections = []
            
            # Look for content in common documentation elements
            content_elements = soup.find_all(['article', 'section', 'div'], 
                                          class_=re.compile(r'doc|content|article'))
            
            search_terms = search_term.lower().split()
            
            for element in content_elements:
                text = element.get_text()
                # Simple relevance scoring based on keyword presence
                if any(term in text.lower() for term in search_terms):
                    # Find nearest heading
                    heading = element.find_previous(['h1', 'h2', 'h3'])
                    title = heading.get_text() if heading else "Documentation Section"
                    
                    cleaned_text = self._clean_text(text)
                    
                    # Calculate simple relevance score
                    score = sum(cleaned_text.lower().count(term) for term in search_terms)
                    
                    relevant_sections.append({
                        'title': self._clean_text(title),
                        'content': cleaned_text,
                        'score': score,
                        'url': urljoin(url, element.find_parent('a').get('href', '')) 
                                if element.find_parent('a') else url
                    })
            
            # Sort by relevance score
            relevant_sections.sort(key=lambda x: x['score'], reverse=True)
            
            # Cache the results
            self.cache.set(cache_key, relevant_sections[:3])  # Cache top 3 results
            
            return relevant_sections[:3]
            
        except Exception as e:
            logger.error(f"Error scraping documentation: {str(e)}")
            return []

    def get_answer(self, question: str) -> str:
        """Main method to get documentation answer"""
        try:
            # 1. Identify platform
            platform = self.identify_platform(question)
            if not platform:
                return "Please specify which platform you're asking about (Segment, mParticle, Lytics, or Zeotap)."

            # 2. Scrape relevant documentation
            results = self.scrape_documentation(self.docs[platform], question)
            
            if not results:
                return f"I couldn't find relevant information in the {platform} documentation. Could you rephrase your question?"

            # 3. Format response with the most relevant result
            best_result = results[0]
            response = ( 
                f"Here's what I found in the {platform} documentation:\n\n"
                f"{best_result['content']}\n\n"
                f"Source: {best_result['url']}"
            )

            return response

        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return "I encountered an error while processing your question. Please try again."

def main():
    """Example usage"""
    helper = DocumentationHelper()
    
    # Example questions
    questions = [
        "How do I set up a new source in Segment?",
        # "How can I create a user profile in mParticle?",
        # "How do I build an audience segment in Lytics?"
    ]
    
    for question in questions:
        print(f"\nQuestion: {question}")
        answer = helper.get_answer(question)
        print(f"Answer: {answer}")

if __name__ == "__main__":
    main()