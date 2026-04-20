
def calculator(a: float, b: float, operation: str):

   

    if operation == '+':

        return a+b

    elif operation == '-': 
        
        return a-b

    elif operation == '*':

        return a*b
    
    elif operation == '/' and b != 0:

   
        return a/b

    else:
        
        print("Error: Attempt to divide by 0 or invalid operation symbol.")
        



result = calculator(0.234, 0.0, "x")

if result != None:

    print(result)


    
