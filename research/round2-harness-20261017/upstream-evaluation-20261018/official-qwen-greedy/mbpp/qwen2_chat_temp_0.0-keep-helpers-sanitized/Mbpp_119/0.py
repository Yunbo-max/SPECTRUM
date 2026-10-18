def search(arr):
    # Initialize the left and right pointers
    left, right = 0, len(arr) - 1
    
    # Loop until the left pointer is less than the right pointer
    while left < right:
        # Calculate the middle index
        mid = (left + right) // 2
        
        # Check if the middle element is the only element that appears once
        if mid == 0 or arr[mid] != arr[mid - 1] and arr[mid] != arr[mid + 1]:
            return arr[mid]
        
        # If the middle element is the first element and it is not the only element that appears once
        elif mid == 0 and arr[mid] != arr[mid + 1]:
            return arr[mid]
        
        # If the middle element is the last element and it is not the only element that appears once
        elif mid == len(arr) - 1 and arr[mid] != arr[mid - 1]:
            return arr[mid]
        
        # If the middle element is not the only element that appears once
        else:
            # If the element before the middle element is the same as the middle element
            if arr[mid - 1] == arr[mid]:
                # If the element after the middle element is the same as the middle element
                if arr[mid + 1] == arr[mid]:
                    # If the element before the middle element is the only element that appears once
                    if arr[mid - 2] == arr[mid - 1]:
                        return arr[mid - 1]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 2] == arr[mid + 1]:
                        return arr[mid + 1]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 3] == arr[mid - 2]:
                        return arr[mid - 2]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 3] == arr[mid + 2]:
                        return arr[mid + 2]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 4] == arr[mid - 3]:
                        return arr[mid - 3]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 4] == arr[mid + 3]:
                        return arr[mid + 3]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 5] == arr[mid - 4]:
                        return arr[mid - 4]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 5] == arr[mid + 4]:
                        return arr[mid + 4]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 6] == arr[mid - 5]:
                        return arr[mid - 5]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 6] == arr[mid + 5]:
                        return arr[mid + 5]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 7] == arr[mid - 6]:
                        return arr[mid - 6]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 7] == arr[mid + 6]:
                        return arr[mid + 6]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 8] == arr[mid - 7]:
                        return arr[mid - 7]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 8] == arr[mid + 7]:
                        return arr[mid + 7]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 9] == arr[mid - 8]:
                        return arr[mid - 8]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 9] == arr[mid + 8]:
                        return arr[mid + 8]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 10] == arr[mid - 9]:
                        return arr[mid - 9]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 10] == arr[mid + 9]:
                        return arr[mid + 9]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 11] == arr[mid - 10]:
                        return arr[mid - 10]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 11] == arr[mid + 10]:
                        return arr[mid + 10]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 12] == arr[mid - 11]:
                        return arr[mid - 11]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 12] == arr[mid + 11]:
                        return arr[mid + 11]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 13] == arr[mid - 12]:
                        return arr[mid - 12]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 13] == arr[mid + 12]:
                        return arr[mid + 12]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 14] == arr[mid - 13]:
                        return arr[mid - 13]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 14] == arr[mid + 13]:
                        return arr[mid + 13]
                    # If the element before the middle element is the only element that appears once
                    elif arr[mid - 15] == arr[mid - 14]:
                        return arr[mid - 14]
                    # If the element after the middle element is the only element that appears once
                    elif arr[mid + 15] == arr[mid + 14]:
                        return arr[mid + 14]
                    # If the element before the middle element is the only element that appears once