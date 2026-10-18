def remove_lowercase(s):
    # Use a list comprehension to filter out lowercase characters
    return ''.join([char for char in s if char.isupper()])