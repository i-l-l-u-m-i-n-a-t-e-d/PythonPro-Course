weight = float(input("Ile ważysz [kg]? (wpisz tylko cyfry): ").replace(",","."))
height = float(input("Podaj swój wzrost [m] (wpisz tylko cyfry): ").replace(",","."))

bmi = weight/(pow(height,2))

print(f"Twój wskaźnik BMI wynosi: {bmi}")
