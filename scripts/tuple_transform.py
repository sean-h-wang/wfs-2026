import re

# Paste your tuples inside the triple quotes below
data = """
(24 2 0 26)
(22 4 2 24)
(20 6 4 22)
(18 8 6 20)
(16 10 8 18)
(14 12 10 16)
"""

def transform_tuples(input_text):
    # Find all sets of numbers inside parentheses
    matches = re.findall(r'\((\d+(?:\s+\d+)*)\)', input_text)
    
    for match in matches:
        # Convert string of numbers to a list of integers
        nums = [int(n) for n in match.split()]
        
        if len(nums) == 4:
            a, b, c, d = nums
            # Apply transformation (d+1 c+1 b+1 a+1)
            transformed = (d + 1, c + 1, b + 1, a + 1)
            # Print in the requested format without commas
            print(f"({transformed[0]} {transformed[1]} {transformed[2]} {transformed[3]})")

transform_tuples(data)