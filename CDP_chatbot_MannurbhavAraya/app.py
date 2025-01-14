import streamlit as st
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Any
import re
from collections import defaultdict

class CDPChatbot:
    def __init__(self, docs_directory: str = "cdp_docs"):
        self.docs_directory = docs_directory
        self.docs_data = self.load_all_docs()
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=10000
        )
        self.doc_vectors = None
        self.process_documents()
        
    def load_all_docs(self) -> List[Dict[str, Any]]:
        """Load documentation from all CDP platforms"""
        all_docs = []
        for platform in ['segment', 'mparticle', 'lytics', 'zeotap']:
            file_path = os.path.join(self.docs_directory, f"{platform}_docs.json")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    platform_docs = json.load(f)
                    all_docs.extend(platform_docs)
            except FileNotFoundError:
                st.warning(f"Documentation for {platform} not found.")
        return all_docs

    def process_documents(self):
        """Process and vectorize all documents"""
        # Prepare document texts with metadata
        self.doc_texts = [
            f"{doc['title']} {doc['content']} {' '.join(doc['keywords'])}"
            for doc in self.docs_data
        ]
        
        # Create document vectors
        self.doc_vectors = self.vectorizer.fit_transform(self.doc_texts)
        
    def search_docs(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant documents based on the query"""
        # Vectorize the query
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.doc_vectors)[0]
        
        # Get top-k documents
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [
            {
                'doc': self.docs_data[idx],
                'similarity': similarities[idx]
            }
            for idx in top_indices
        ]

    def extract_steps(self, content: str) -> List[str]:
        """Extract steps from content"""
        # Look for numbered steps
        numbered_steps = re.findall(r'\d+\.\s+(.*?)(?=\d+\.|$)', content, re.DOTALL)
        if numbered_steps:
            return [step.strip() for step in numbered_steps]
        
        # Look for bullet points if no numbered steps
        bullet_steps = re.findall(r'[•\-\*]\s+(.*?)(?=[•\-\*]|$)', content, re.DOTALL)
        return [step.strip() for step in bullet_steps]

    def compare_platforms(self, feature: str) -> str:
        """Compare how different platforms handle a specific feature"""
        feature_docs = defaultdict(list)
        
        # Search for relevant docs across platforms
        for doc in self.docs_data:
            if feature.lower() in doc['content'].lower() or feature.lower() in ' '.join(doc['keywords']).lower():
                feature_docs[doc['platform']].append(doc)
        
        if not feature_docs:
            return "I couldn't find enough information to compare this feature across platforms."
        
        comparison = f"Here's how different platforms handle {feature}:\n\n"
        for platform, docs in feature_docs.items():
            if docs:
                comparison += f"\n{platform.upper()}:\n"
                for doc in docs[:2]:  # Take top 2 most relevant docs per platform
                    comparison += f"- {doc['title']}\n"
                    if doc['type'] == 'how-to' and doc['howto_steps']:
                        comparison += "  Key steps:\n"
                        for step in doc['howto_steps'][:3]:  # Show first 3 steps
                            comparison += f"  * {step}\n"
        
        return comparison

    def generate_response(self, query: str) -> str:
        """Generate a response based on the query"""
        # Check if it's a comparison question
        comparison_patterns = [
            r'compare|difference|versus|vs|different|better',
            r'how does (\w+) compare to (\w+)',
            r'which platform (is|has) better'
        ]
        
        is_comparison = any(re.search(pattern, query.lower()) for pattern in comparison_patterns)
        
        if is_comparison:
            # Extract the feature to compare
            feature_match = re.search(r'compare.+?(for|in|with)\s+([^?]+)', query.lower())
            feature = feature_match.group(2) if feature_match else query.split()[-1]
            return self.compare_platforms(feature)
        
        # Regular search
        relevant_docs = self.search_docs(query)
        
        if not relevant_docs:
            return "I'm sorry, I couldn't find any relevant information for your question."
        
        # Get the most relevant document
        top_doc = relevant_docs[0]['doc']
        
        # Format the response based on document type
        if top_doc['type'] == 'how-to':
            response = f"Here's how to {top_doc['title'].lower()}:\n\n"
            steps = top_doc['howto_steps'] if top_doc['howto_steps'] else self.extract_steps(top_doc['content'])
            
            if steps:
                for i, step in enumerate(steps, 1):
                    response += f"{i}. {step}\n"
            else:
                # If no clear steps found, provide relevant content
                response += top_doc['content'][:500] + "...\n"
                
            response += f"\nFor more details, visit: {top_doc['url']}"
            
        else:
            response = f"Here's what I found about {top_doc['title']}:\n\n"
            response += top_doc['content'][:500] + "...\n"
            response += f"\nFor more details, visit: {top_doc['url']}"
            
        return response

def main():
    st.set_page_config(
        page_title="CDP Documentation Chatbot",
        page_icon="🤖",
        layout="wide"
    )

    st.title("CDP Documentation Assistant 🤖")
    
    # Initialize session state for chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Initialize the chatbot
    if 'chatbot' not in st.session_state:
        with st.spinner("Loading CDP documentation..."):
            st.session_state.chatbot = CDPChatbot()
        st.success("Documentation loaded! Ready to help.")

    # Sidebar with platform selection and filters
    st.sidebar.title("Filters")
    selected_platforms = st.sidebar.multiselect(
        "Select Platforms",
        ["Segment", "mParticle", "Lytics", "Zeotap"],
        default=["Segment", "mParticle", "Lytics", "Zeotap"]
    )

    # Chat interface
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # User input
    if prompt := st.chat_input("Ask me anything about CDPs..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)

        # Generate and display response
        with st.chat_message("assistant"):
            response = st.session_state.chatbot.generate_response(prompt)
            st.write(response)
            
        # Add assistant response to chat history
        st.session_state.chat_history.append({"role": "assistant", "content": response})

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>This chatbot helps you navigate CDP documentation. Ask questions about:</p>
            <ul style='list-style-type: none'>
                <li>How to perform specific tasks</li>
                <li>Platform comparisons</li>
                <li>Features and capabilities</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
