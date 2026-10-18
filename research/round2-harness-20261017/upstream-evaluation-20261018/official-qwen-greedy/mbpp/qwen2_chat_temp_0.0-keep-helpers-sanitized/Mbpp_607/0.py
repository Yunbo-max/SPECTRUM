import re
def find_literals(text, pattern):
    match = re.search(pattern, text)
    if match:
        return match.group(), match.start(), match.end()
    else:
        return None