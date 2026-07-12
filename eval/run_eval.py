from eval.cases import ALL_CASES
from eval.metrics import print_report
from eval.runner import run_eval_case
from prlens.config.settings import load_settings
from prlens.llm.analyzer import Analyzer
from prlens.llm.client import LLMClient

if __name__ == "__main__":
    settings = load_settings()
    llm_client = LLMClient(settings.llm_model)
    analyzer = Analyzer(llm_client)

    results = [run_eval_case(case, analyzer) for case in ALL_CASES]
    print_report(results)