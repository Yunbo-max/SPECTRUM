def find_substring(string_list, target_substring):
    # Iterate through each string in the list
    for string in string_list:
        # Check if the target substring is present in the current string
        if target_substring in string:
            return True
    # If the loop completes without finding the substring, return False
    return False