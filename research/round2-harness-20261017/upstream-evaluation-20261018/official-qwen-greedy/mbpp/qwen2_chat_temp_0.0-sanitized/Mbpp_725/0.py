def extract_quotation(s):
    # Split the string by spaces to get individual words
    words = s.split()
    # Filter words that are enclosed in quotation marks
    quoted_words = [word for word in words if word.startswith('"') and word.endswith('"')]
    return quoted_words