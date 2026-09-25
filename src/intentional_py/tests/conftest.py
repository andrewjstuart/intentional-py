import os

# Rich wraps at 80 columns when not attached to a terminal, which splits asserted messages.
os.environ["COLUMNS"] = "200"


def pytest_collection_modifyitems(session, config, items):
    """Modifies test items in place to ensure test functions run in a given order"""
    function_order = [
        "test_version",
        "test_validate_exceptions",
        "test_validate",
        "test_extract_exceptions",
        "test_extract_XLSM",
        "test_extract_XLSB",
        "test_DD_exceptions",
        "test_DD",
        "test_NL_exceptions",
        "test_NL",
        "test_NL_reuse",
    ]
    # OR
    # function_order = ["test_one[1]", "test_two[2]"]
    function_mapping = {item: item.name.split("[")[0] if "]" not in function_order[0] else item.name for item in items}

    sorted_items = items.copy()
    for func_ in function_order:
        sorted_items = [it for it in sorted_items if function_mapping[it] != func_] + [
            it for it in sorted_items if function_mapping[it] == func_
        ]
    items[:] = sorted_items
