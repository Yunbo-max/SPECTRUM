import re
def is_decimal(s):
    # Regular expression to match a decimal number with a precision of 2
    pattern = r'^\d+(\.\d{2})?$'
    return bool(re.match(pattern, s))