from prlens.config.settings import load_settings

settings = load_settings()
print(settings.model_dump_json(indent=2))
