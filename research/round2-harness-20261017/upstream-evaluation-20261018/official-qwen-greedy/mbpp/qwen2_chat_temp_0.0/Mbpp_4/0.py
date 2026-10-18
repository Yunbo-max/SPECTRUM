import heapq

def heap_queue_largest(nums, n):
    # Use heapq to find the n largest numbers in the list
    largest_nums = heapq.nlargest(n, nums)
    # Return the largest numbers in descending order
    return largest_nums[::-1]