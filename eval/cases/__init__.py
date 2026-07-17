from eval.cases.clean import CLEAN_CASES
from eval.cases.documentation import DOCUMENTATION_CASES
from eval.cases.mixed import MIXED_CASES
from eval.cases.performance import PERFORMANCE_CASES
from eval.cases.quality import QUALITY_CASES
from eval.cases.security import SECURITY_CASES
from eval.cases.style import STYLE_CASES

ALL_CASES = (
    SECURITY_CASES
    + QUALITY_CASES
    + CLEAN_CASES
    + MIXED_CASES
    + STYLE_CASES
    + DOCUMENTATION_CASES
    + PERFORMANCE_CASES
)
