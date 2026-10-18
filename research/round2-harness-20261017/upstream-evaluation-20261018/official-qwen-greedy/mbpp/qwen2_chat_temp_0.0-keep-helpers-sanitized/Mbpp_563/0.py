def extract_values(s):
    # Split the string by commas and remove any leading or trailing spaces
    values = [value.strip() for value in s.split(',')]
    # Filter out any values that are not enclosed in quotation marks
    return [value for value in values if value.startswith('"') and value.endswith('"')]