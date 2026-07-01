from enum import Enum
from pydantic import BaseModel, Field
from prlens.models.review import Severity, ReviewType
from prlens.models.pr import FileChange
import yaml
import fnmatch #Python module used for matching filenames
from pathlib import Path



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
    reviewers_mapping: dict[ReviewType, str] = Field(default_factory=dict)
    max_workers: int = 5
    approve_threshold: int = 80
    changes_threshold: int = 50
    large_pr_threshold: int = 20

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_settings(config_path: str | None = None) -> Settings:
    path = Path(config_path) if config_path else PROJECT_ROOT / ".aireviewer.yml"

    try:
        with open(path, "r") as file:
            data = yaml.safe_load(file)
    except FileNotFoundError:
        return Settings()

    return Settings(**data)

def filter_files(files: list[FileChange], settings: Settings) -> list[FileChange]:
    EXTENSION_TO_LANGUAGE = {
        ".py": SupportedLanguages.PYTHON,
        ".js": SupportedLanguages.JAVASCRIPT,
        ".ts": SupportedLanguages.TYPESCRIPT,
        ".java": SupportedLanguages.JAVA,
    }

    supported_files = []

    for file in files:
        file_extension = Path(file.filename).suffix
        language = EXTENSION_TO_LANGUAGE.get(file_extension)
        language_accepted = (
                not settings.target_languages
                or language in settings.target_languages
        )
        excluded = any(fnmatch.fnmatch(file.filename, pattern) for pattern in settings.excluded_files)
        if not excluded and language_accepted:
            supported_files.append(file)

    return supported_files

