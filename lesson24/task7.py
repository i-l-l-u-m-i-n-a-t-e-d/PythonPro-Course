# api/views.py
@api_view(["GET"])
def calculate(request):
    num1 = request.query_params.get("num1")
    num2 = request.query_params.get("num2")
    operation = request.query_params.get("operation")

    if num1 is None or num2 is None or operation is None:
        return Response(
            {"error": "Podaj parametry num1, num2 i operation."},
            status=400,
        )

    try:
        first_number = Decimal(num1)
        second_number = Decimal(num2)
    except InvalidOperation:
        return Response({"error": "Parametry num1 i num2 muszą być liczbami."}, status=400)

    if operation == "add":
        result = first_number + second_number
    elif operation == "subtract":
        result = first_number - second_number
    elif operation == "multiply":
        result = first_number * second_number
    elif operation == "divide":
        if second_number == 0:
            return Response({"error": "Nie można dzielić przez zero."}, status=400)
        result = first_number / second_number
    else:
        return Response({"error": "Nieznana operacja."}, status=400)

    return Response({"result": float(result)})


# config/urls.py
path('api/calculate/', views.calculate),


# Przyklady:
# /api/calculate/?num1=10&num2=5&operation=add
# Odpowiedz: {"result": 15.0}
#
# /api/calculate/?num1=10&num2=0&operation=divide
# Odpowiedz: {"error": "Nie można dzielić przez zero."}
