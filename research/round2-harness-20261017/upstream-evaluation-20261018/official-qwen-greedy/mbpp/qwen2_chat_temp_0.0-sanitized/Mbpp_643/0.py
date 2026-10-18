def text_match_wordz_middle(text):
    # Check if the string contains 'z' at the start or end
    if text[0] == 'z' or text[-1] == 'z':
        return False
    # Check if 'z' is present in the middle of the string
    for i in range(1, len(text) - 1):
        if text[i] == 'z':
            return True
    return False