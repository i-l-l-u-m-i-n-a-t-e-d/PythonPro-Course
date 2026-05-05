from openpyxl import Workbook, load_workbook

wb = Workbook()
ws = wb.active 
ws.title = "Finanse"

ws.append(["Nazwa wydatku", "Wartość"]) # Dodaj nagłówek
ws.append(["Czynsz", 550.75])
ws.append(["Jedzenie", 990])
ws.append(['Suma', '= SUM(B2:B3)'])

wb.save("finanse.xlsx")