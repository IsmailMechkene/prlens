from prlens.config.settings import Settings, load_settings, filter_files, SupportedLanguages
from prlens.models.pr import FileChange, FileChangeStatus


def test_load_settings_defaults():
    settings = load_settings(config_path="nonexistent.yml")

    assert settings.llm_model == "gpt-4o"
    assert settings.max_workers == 5
    assert settings.approve_threshold == 80
    assert settings.changes_threshold == 50
    assert settings.min_severity.value == "info"


def test_load_settings_returns_settings_instance():
    settings = load_settings(config_path="nonexistent.yml")
    assert isinstance(settings, Settings)


def test_load_settings_reads_yaml_file(tmp_path):
    config = tmp_path / ".aireviewer.yml"
    config.write_text("llm_model: gpt-4o-mini\nmax_workers: 3\napprove_threshold: 90\n")

    settings = load_settings(config_path=str(config))

    assert isinstance(settings, Settings)
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.max_workers == 3
    assert settings.approve_threshold == 90


def test_filter_files_excludes_lock_files():
    settings = Settings(excluded_files=["*.lock"])

    files = [
        FileChange(filename="main.py", status=FileChangeStatus.MODIFIED,
                   additions=1, deletions=0, changes=1),
        FileChange(filename="package.lock", status=FileChangeStatus.MODIFIED,
                   additions=1, deletions=0, changes=1),
    ]

    result = filter_files(files, settings)

    assert len(result) == 1
    assert result[0].filename == "main.py"


def test_filter_files_respects_target_languages():
    settings = Settings(target_languages=[SupportedLanguages.PYTHON])

    files = [
        FileChange(filename="main.py", status=FileChangeStatus.ADDED,
                   additions=1, deletions=0, changes=1),
        FileChange(filename="README.md", status=FileChangeStatus.MODIFIED,
                   additions=1, deletions=0, changes=1),
    ]

    result = filter_files(files, settings)

    assert len(result) == 1
    assert result[0].filename == "main.py"


def test_filter_files_empty_target_languages_allows_all():
    settings = Settings(target_languages=[])

    files = [
        FileChange(filename="main.py", status=FileChangeStatus.ADDED,
                   additions=1, deletions=0, changes=1),
        FileChange(filename="README.md", status=FileChangeStatus.MODIFIED,
                   additions=1, deletions=0, changes=1),
    ]

    result = filter_files(files, settings)

    assert len(result) == 2


def test_filter_files_excludes_multiple_patterns():
    settings = Settings(excluded_files=["*.lock", "dist/**", "*.min.js"])

    files = [
        FileChange(filename="main.py", status=FileChangeStatus.ADDED,
                   additions=1, deletions=0, changes=1),
        FileChange(filename="yarn.lock", status=FileChangeStatus.MODIFIED,
                   additions=1, deletions=0, changes=1),
        FileChange(filename="dist/bundle.js", status=FileChangeStatus.ADDED,
                   additions=1, deletions=0, changes=1),
        FileChange(filename="app.min.js", status=FileChangeStatus.MODIFIED,
                   additions=1, deletions=0, changes=1),
    ]

    result = filter_files(files, settings)

    assert len(result) == 1
    assert result[0].filename == "main.py"


def test_filter_files_empty_list_returns_empty():
    settings = Settings()
    result = filter_files([], settings)
    assert result == []