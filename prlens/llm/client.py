from prlens.config.settings import load_settings
from dotenv import load_dotenv
from openai import OpenAI
import os


class LLMClient:
    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not found in environment")

        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT not found in environment")

        self.base_url = self.endpoint

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        self.settings = load_settings()


    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(  #ChatCompletion object
            model= self.settings.llm_model,
            messages = [
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

