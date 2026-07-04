from prlens.config.settings import load_settings
settings = load_settings()
print(settings.reviewers_mapping)
print(type(list(settings.reviewers_mapping.keys())[0]))