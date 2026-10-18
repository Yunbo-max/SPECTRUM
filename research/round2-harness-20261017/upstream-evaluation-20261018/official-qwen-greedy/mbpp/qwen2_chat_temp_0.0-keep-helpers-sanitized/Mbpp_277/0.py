def dict_filter(d, n):
    # Use dictionary comprehension to filter entries with values greater than or equal to n
    return {k: v for k, v in d.items() if v >= n}