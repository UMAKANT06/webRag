CDP Documentation Chatbot
A comprehensive chatbot that helps users navigate and understand documentation from multiple Customer Data Platforms (CDPs). The project includes a web scraper to gather documentation and a Streamlit-based chat interface.


Core Functionalities:
1. Answer "How-to" Questions:
○ The chatbot should be able to understand and respond to user questions
about how to perform specific tasks or use features within each CDP.
○ Example questions:
■ "How do I set up a new source in Segment?"
■ "How can I create a user profile in mParticle?"
■ "How do I build an audience segment in Lytics?"
■ "How can I integrate my data with Zeotap?"
2. Extract Information from Documentation:
○ The chatbot should be capable of retrieving relevant information from the
provided documentation to answer user questions.
○ It should be able to navigate through the documentation, identify relevant
sections, and extract the necessary instructions or steps.
3. Handle Variations in Questions:
○ Size variations. E.g extremely long question should not break it down.
○ Questions irrelevant to CDP. e.g Which Movie is getting released this
week


Install required packages:
pip install -r requirements.txt

Start the Streamlit application:
streamlit run app.py
