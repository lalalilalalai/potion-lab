import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        categories = [
            name for name in ("unit", "integration") if item.get_closest_marker(name)
        ]
        if len(categories) != 1:
            raise pytest.UsageError(
                f"Тест должен иметь одну категорию unit/integration: {item.nodeid}"
            )
