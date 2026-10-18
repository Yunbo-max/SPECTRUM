def sort_counter(counter):
    # Sort the dictionary by value in descending order
    sorted_items = sorted(counter.items(), key=lambda item: item[1], reverse=True)
    return sorted_items