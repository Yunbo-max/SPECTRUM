import re
def text_starta_endb(text):
    # Define the pattern to match 'a' followed by anything, ending in 'b'
    pattern = 'a.*b'
    # Use re.search to find the pattern in the given text
    match = re.search(pattern, text)
    # Return True if a match is found, False otherwise
    return bool(match)