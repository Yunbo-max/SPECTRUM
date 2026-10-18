def all_Characters_Same(s):
    # Check if the length of the string is 1
    if len(s) == 1:
        return True
    # Check if all characters in the string are the same
    return all(c == s[0] for c in s)