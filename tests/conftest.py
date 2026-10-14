import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    counts = {"unit": 0, "integration": 0}
    for item in items:
        categories = [name for name in counts if item.get_closest_marker(name)]
        if len(categories) != 1:
            raise pytest.UsageError(
                f"Тест должен иметь одну категорию unit/integration: {item.nodeid}"
            )
        counts[categories[0]] += 1
    if counts["unit"] > 30 or counts["integration"] > 10:
        raise pytest.UsageError(
            f"Превышен лимит тестов (unit ≤30, integration ≤10): {counts}"
        )
