# ==========================================
# TEST EXAMPLE 1: The "God Function" with Deep Nesting
# ==========================================
def process_everything(data_list):
    total = 0
    # Magic numbers + Deep nesting
    for i in range(len(data_list)):
        if data_list[i] != None:
            if type(data_list[i]) == int:
                if data_list[i] > 0:
                    if data_list[i] < 100:
                        total = total + (data_list[i] * 3.14159) # Magic Number
    
    # Writing to file directly without error handling
    f = open("results.txt", "w")
    f.write(str(total))
    f.close()
    
    # DRY violation (repeated code)
    print("Process finished successfully.")
    print("Total was calculated.")
    print("Process finished successfully.")
    print("Total was calculated.")
    
    return total

# ==========================================
# TEST EXAMPLE 2: Horrible Variables & Unused Data
# ==========================================
def x(y):
    a = 10
    b = 20
    c = 30 # Unused variable
    
    # Vague naming
    z = y * a
    res = z + b
    return res

# ==========================================
# TEST EXAMPLE 3: Terrible Syntax Error
# ==========================================
def broken_function()
    my_list = [1, 2, 3
    print("I forgot a colon and a closing bracket"
