def replace_spaces(input_string):
    # Replace spaces with underscores
    result = input_string.replace(' ', '_')
    # Replace underscores with spaces
    result = result.replace('_', ' ')
    return result