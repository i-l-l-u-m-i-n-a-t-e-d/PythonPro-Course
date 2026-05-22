from dataclasses import dataclass

@dataclass
class Film:
    
    title: str
    director: str
    year_of_production: int
    
    

film = Film("Hustle", "Jeremiah Zagar", 2022)
film2 = Film("The Green Mile", "Frank Darabont", 1999)

print(film)
print(film2)
