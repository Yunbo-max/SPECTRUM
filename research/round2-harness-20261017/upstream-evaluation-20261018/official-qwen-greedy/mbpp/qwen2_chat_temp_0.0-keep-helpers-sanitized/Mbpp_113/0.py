def check_integer(s):
    # Check if the string is empty
    if not s:
        return False
    # Check if the string is a valid integer
    try:
        int(s)
        return True
    except ValueError:
        return False