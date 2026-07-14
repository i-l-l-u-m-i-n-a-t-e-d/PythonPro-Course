# api/views.py
@api_view(["GET"])
def set_name(request):
    name = request.query_params.get("name", "Gość")
    response = Response({"message": f"Zapisano imię: {name}"})
    response.set_cookie("user_name", name, max_age=3600)
    return response


@api_view(["GET"])
def hello(request):
    name = request.COOKIES.get("user_name", "Gość")
    return Response({"message": f"Witaj, {name}!"})


# config/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/set-name/', views.set_name),
    path('api/hello/', views.hello),
    path('api/calculate/', views.calculate),
]


# Testowane adresy:
# /api/set-name/?name=Anna
# /api/hello/
# Po ustawieniu ciasteczka odpowiedź z /api/hello/ to {"message": "Witaj, Anna!"}.
