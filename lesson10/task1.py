class Film:
    
    def __init__(self, title, director, year_of_production):
        
        self.title = title
        self.director = director
        self.year_of_production = year_of_production
    
    def informacje(self):
        
        return f'"{self.title}" ({self.year_of_production}), reżyseria: {self.director}'



film = Film("Skazani na Shawshank", "Frank Darabont", 1994)

film2 = Film("Zielona mila", "Frank Darabont", 1999)

print(film.informacje())
print(film2.informacje())


        