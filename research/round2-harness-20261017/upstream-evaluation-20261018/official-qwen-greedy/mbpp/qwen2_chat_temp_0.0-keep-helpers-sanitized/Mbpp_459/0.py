def remove_uppercase(s):
    # Use a list comprehension to filter out uppercase characters
    result = ''.join([char for char in s if char.islower()])
    return result