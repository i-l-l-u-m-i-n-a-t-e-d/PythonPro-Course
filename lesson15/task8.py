class FakeServer:

    def __init__(self):
        
        self.db = {
            "users": [
                {"id": 1, "name": "Jan"}, 
                {"id": 2, "name": "Anna"}
                      ]
        }

    def handle_request(self, request: dict):

            # method: GET, target: /users -> dict + response: 200, body: list of users

            # method: POST, target: /users -> new user from request body, response: 201

            # else -> 404 (Not Found)


        result = {}

        if request["method"] == "GET" and request["target"] == "/users":

            result["response"] = 200
            result["body"] = self.db["users"]
        
        elif request["method"] == "POST" and request["target"] == "/users":

            self.db["users"].append(request["body"])

            result["response"] = 201
            result["body"] = request["body"]

        else:
            
            result["response"] = 404
            result["body"] = "Not Found"


        return result
        

class FakeClient:

    def send(self, server, request):

        response = server.handle_request(request)

        print(response)



server = FakeServer()

client = FakeClient()


request1 = {
    "method": "GET",
    "target": "/users"
}

client.send(server, request1)


request2 = {
    "method": "POST",
    "target": "/users",
    "body": {"id": 3, "name": "Kasia"}
}

client.send(server, request2)


request3 = {
    "method": "GET",
    "target": "/users"
}

client.send(server, request3)


request4 = {
    "method": "GET",
    "target": "/index.html"
}

client.send(server, request4)