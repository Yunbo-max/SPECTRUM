def text_match_two_three(text):
    # Check if the string contains 'a' followed by two or three 'b' characters
    return 'a' in text and (text.count('b') >= 2 and text.count('b') <= 3)