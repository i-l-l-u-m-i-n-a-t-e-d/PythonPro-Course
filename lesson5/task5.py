def calculator(a: float, b: float, operation: str) -> float | None: #None if error

    """
    Function tooks as an input 2 float variables and
    one of this symbols (*, +, -, \) which signals what
    type of calcualtion user wants to do on this 2 variables and returns that calculated value.
    
    """
   

    if operation == '+':

        add: float = a+b
        return add

    elif operation == '-': 
        
        difference: float = a-b
        return difference

    elif operation == '*':

        multiply: float = a*b
        return multiply
    
    elif operation == '/' and b != 0:

        divide: float = a/b
        return divide

    else:
        
        print("Error: Attempt to divide by 0 or invalid operation symbol.")
        

