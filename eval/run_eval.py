from eval.cases import ALL_CASES
from eval.runner import run_eval_case
from eval.metrics import calculate_metrics, print_report
from prlens.llm.client import LLMClient
from prlens.llm.analyzer import Analyzer
from prlens.config.settings import load_settings

if __name__ == "__main__":
    settings = load_settings()
    llm_client = LLMClient(settings.llm_model)
    analyzer = Analyzer(llm_client)

    results = [run_eval_case(case, analyzer) for case in ALL_CASES]
    print_report(results)