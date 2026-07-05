from eval.runner import EvalResult


def calculate_metrics(results: list[EvalResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    precision = passed / total if total > 0 else 0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "precision": round(precision * 100, 1),
        "meets_spec": precision >= 0.70  # spec requires >= 70%
    }


def print_report(results: list[EvalResult]) -> None:
    print("\n" + "=" * 60)
    print("PRLens Eval Report")
    print("=" * 60)

    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n{status} — {result.case.name}")
        print(f"  Reason: {result.reason}")
        print(f"  Comments found: {len(result.comments_found)}")
        for comment in result.comments_found:
            print(f"    [{comment.severity.value}] {comment.type.value}: {comment.message[:80]}")

    metrics = calculate_metrics(results)
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total cases:  {metrics['total']}")
    print(f"Passed:       {metrics['passed']}")
    print(f"Failed:       {metrics['failed']}")
    print(f"Precision:    {metrics['precision']}%")
    print(f"Meets spec:   {'✅ YES (≥70%)' if metrics['meets_spec'] else '❌ NO (<70%)'}")