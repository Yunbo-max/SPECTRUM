def reverse_string_list(string_list):
    # Use list comprehension to reverse each string in the list
    reversed_list = [s[::-1] for s in string_list]
    return reversed_list