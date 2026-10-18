def sample_nam(names):
    # Filter out names that start with a lowercase letter
    filtered_names = [name for name in names if name[0].isupper()]
    # Calculate the sum of the lengths of the filtered names
    return sum(len(name) for name in filtered_names)