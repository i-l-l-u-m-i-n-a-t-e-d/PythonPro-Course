class HttpRequest:

    def __init__(self, method: str, target: str, headers: dict, body: str):
        self.method = method
        self.target = target
        self.headers = headers
        self.body = body

    def display(self):
        
        print("--- HTTP Request ---")
        print(f"Method: {self.method}")
        print(f"Target: {self.target}")

        print("Headers:")
        for key, value in self.headers.items():
            print(f"{key}: {value}")

        print("Body:")
        print(self.body)


request = HttpRequest(
    "POST",
    "/users",
    {
        "Host": "example.com",
        "Content-Type": "application/json",
        "Authorization": "Bearer 123"
    },
    '{"name": "Jan", "age": 25}'
)

request.display()
        
        


