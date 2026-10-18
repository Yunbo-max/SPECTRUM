def extract_string(string_list, size):
    # Use list comprehension to filter strings based on the specified size
    return [s for s in string_list if len(s) == size]