def expensive_items(data, n):
    # Sort the data based on the price in descending order
    sorted_data = sorted(data, key=lambda x: x['price'], reverse=True)
    # Return the top n items
    return sorted_data[:n]