from prlens.llm.client import LLMClient

client = LLMClient()

print(client.generate("say hello"))