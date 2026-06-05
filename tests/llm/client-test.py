from prlens.llm.client import LLMClient

client = LLMClient()

print(client.generate("Say hello in one word"))