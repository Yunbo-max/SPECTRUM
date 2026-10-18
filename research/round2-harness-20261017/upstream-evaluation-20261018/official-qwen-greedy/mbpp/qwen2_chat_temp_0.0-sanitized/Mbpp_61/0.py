def count_Substrings(s):
    count = 0
    for i in range(len(s)):
        for j in range(i, len(s)):
            if sum(int(digit) for digit in s[i:j+1]) == j - i + 1:
                count += 1
    return count