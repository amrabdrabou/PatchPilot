import os
from dotenv import load_dotenv
from openai import OpenAI
from config import MODEL_NAME


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_model(messages):
    """
    Sends the conversation messages to the LLM
    and returns the assistant's text response.
    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0,
    )

    return response.choices[0].message.content