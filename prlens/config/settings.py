from enum import Enum
from pydantic import BaseModel, Field
from prlens.models.review import Severity
from prlens.models.pr import FileChange
import yaml
import fnmatch #Python module used for matching filenames


class SupportedLanguages(str, Enum):
    PYTHON = "python"
    JAVASCRIPT= "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"


class Settings(BaseModel):
    excluded_files: list[str] = Field(default_factory=list)
    target_languages: list[SupportedLanguages] = Field(default_factory=list)
    min_severity: Severity = Severity.INFO
    llm_model: str = "gpt-4o"
    reviewers_mapping: dict[str, str] = Field(default_factory=dict)

def load_settings(config_path: str = ".aireviewer.yml") -> Settings:
    try:
        with open(config_path, "r") as file:
            data = yaml.safe_load(file)
    except FileNotFoundError:
        return Settings()

    return Settings(**data)

def filter_files(files: list[FileChange], settings: Settings) -> list[FileChange]:
    supported_files = []
    for file in files:
        excluded = any(fnmatch.fnmatch(file.filename, pattern) for pattern in settings.excluded_files)
        if not excluded:
            supported_files.append(file)

    return supported_files

