def truthy_value(value: str | bool | int | None) -> bool:
    """Truthy values from https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#literals"""
    if value in (False, 0, "0", "-0", "false", "null", None, ""):
        return False
    return True
