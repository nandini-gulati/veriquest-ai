
<p align="center">
    <b>VeriQuest AI</b> — AI that knows your sources.
</p>
<br>



# What is VeriQuest AI?
Large language model (LLM) chatbots like ChatGPT and GPT-4 are great tools for quick access to knowledge.
But they get things wrong a lot, especially if the information you are looking for is recent ("Tell me about the 2024 Super Bowl.") or about less popular topics ("What are some good movies to watch from [insert your favorite foreign director]?").
  
VeriQuest AI uses an LLM as its backbone, but it makes sure the information it provides comes from a reliable source like Wikipedia, so that its responses are more factual.


# What is this website?
VeriQuest AI helps you explore answers grounded in its connected sources. Thank you for giving it a try!
For further research on factual chatbots, we store conversations conducted on this website in a secure database. Only the text that you submit is stored. We do NOT collect or store any other information.


# How does VeriQuest AI work?
Given the user input and the history of the conversation, VeriQuest AI performs the following actions:

1. Searches Wikipedia to retrieve relevant information.
1. Summarizes and filters the retrieved passages.
1. Generates a response using a Language Learning Model (LLM).
1. Extracts claims from the LLM response.
1. Fact-checks the claims in the LLM response using additional retrieved evidence it retrieves from Wikipedia.
1. Drafts a response.
1. Refines the drafted response.

The following figure shows how these steps are applied during a sample conversation about an upcoming movie at the time, edited for brevity.
<p align="center">
    <img src="public/pipeline.svg" width="800px" alt="VeriQuest AI pipeline" />
</p>


# Sources

VeriQuest AI searches connected public sources, including Wikipedia, before drafting an answer. Verify important information with the linked sources in each response.
