def tuple_str_int(tuple_str):
    # Remove the parentheses from the string
    tuple_str = tuple_str[1:-1]
    # Split the string by comma and convert each element to an integer
    return tuple(int(x) for x in tuple_str.split(','))