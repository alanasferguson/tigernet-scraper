1. Problem Decomposition: How did you break this problem down? What were the sub-problems you identified?
    - Sub-Problem 1: Authentication. TigetNet, like all Princeton apps, sits behind CAS and Duo 2-Factor Authentication. I couldn't make a request and get data back, and brainstormed how I could programmatically log in and maintain a valid session across multiple requests. I worked on translating encoding my own session cookies adn tokens into the hidden .env file into providing my username and password for the program to use as input for automating the process. 
    - Sub-Problem 2: 
2. Approach Exploration: What different paths did you consider? (Direct HTTP requests vs. headless browser vs. API reverse-engineering, etc.) Why did you choose the path you chose?

3. Technical Tradeoffs: What tradeoffs did you encounter and how did you decide?
Speed vs. reliability? Complexity vs. maintainability? Be specific.

4. Obstacles &amp; Solutions: What broke? What surprised you? How did you debug it? Don’t sanitize this — we want the raw story.

5. AI Collaboration: This is critical. Tell us exactly how you used AI throughout the project. Which tools? What prompts worked and what didn’t? Where did AI accelerate you? Where did it lead you astray? Where did you override its suggestions and why? We’re not looking for “I used ChatGPT.” We’re looking for evidence of sophisticated AI- augmented engineering.