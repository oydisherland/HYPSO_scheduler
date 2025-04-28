import numpy as np

array1 = np.array([[1,1], [2,2]])
array2 = np.array([[1,1], [3,3]])
array3 = np.array([[1,1], [2,2], [3,3]])

# Check if elements of array1 are in array2
result = np.isin(array1, array2)
result2 = np.isin(array1, array3)
result3 = np.isin(array3, array1)

print("Elements of array1 in array2:", result)

# Optionally, check if all elements of array1 are in array2
if np.all(result):
    print("All elements of array1 are in array2")
else:
    print("Not all elements of array1 are in array2")

if np.all(result2):
    print("All elements of array1 are in array3")
else:
    print("Not all elements of array1 are in array3")

if np.all(result3):
    print("All elements of array3 are in array1")
else:
    print("Not all elements of array3 are in array1")