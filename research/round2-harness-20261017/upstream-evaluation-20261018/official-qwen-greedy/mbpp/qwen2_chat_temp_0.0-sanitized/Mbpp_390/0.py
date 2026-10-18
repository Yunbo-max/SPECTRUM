def add_string(lst, format_str):
    # Use list comprehension to apply the format string to each element in the list
    return [format_str.format(i) for i in lst]