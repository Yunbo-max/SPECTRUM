def frequency(lst, num):
    count = 0
    for i in lst:
        if i == num:
            count += 1
    return count