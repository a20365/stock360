def validate_foreign_key_id(value, field_name):
    if value is None:
        return
    if not isinstance(value, int) or value <= 0:
        raise ValueError(
            f"Invalid value for '{field_name}'. Must be a positive integer."
        )


def validate_required_fields(data, required_fields):
    missing_fields = []
    for field in required_fields:
        if (
            field not in data
            or data[field] is None
            or (isinstance(data[field], str) and not data[field].strip())
        ):
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(
            f"Missing or empty required fields: {', '.join(missing_fields)}"
        )
