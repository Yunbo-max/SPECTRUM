def find_sum(lst):
    # Create a dictionary to count occurrences of each element
    count_dict = {}
    for num in lst:
        if num in count_dict:
            count_dict[num] += 1
        else:
            count_dict[num] = 1
    
    # Calculate the sum of non-repeated elements
    sum_non_repeated = sum(num for num, count in count_dict.items() if count == 1)
    
    return sum_non_repeated