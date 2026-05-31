def validate_request(request_dict: dict):

    
    if "headers" not in request_dict:

        raise ValueError("Brak sekcji headers")
    

    headers = request_dict["headers"]


    if "Host" not in headers or headers["Host"] == "":

        raise ValueError("Brak wymaganego nagłówka: Host") 
    

    elif "User-Agent" not in headers or headers["User-Agent"] == "":
        
        raise ValueError("Brak wymaganego nagłówka: User-Agent") 
    

    return True



request1 = {
    "method": "GET",
    "target": "/users",
    "headers": {
        "Host": "example.com",
        "User-Agent": "PythonClient/1.0"
    },
    "body": ""
}


request2 = {
    "method": "GET",
    "target": "/users",
    "headers": {
        "User-Agent": "PythonClient/1.0"
    },
    "body": ""
}



try:

    validate_request(request1)

    print("Zadanie poprawne")

except ValueError as error:

    print(error)



try:

    validate_request(request2)

    print("Zadanie poprawne")

except ValueError as error:

    print(error)