import os
from dotenv import load_dotenv
import openai
import anthropic

load_dotenv()

# Standard OpenAI client
openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# OpenRouter — OpenAI-compatible gateway that hosts Llama, Mistral, and others
openrouter_client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"]
)

# Anthropic / Claude
claude_client = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])

# Groq — OpenAI-compatible API, hosts fast open-source models like Llama 4
groq_client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"]
)
