class Pracownik:
    
    def __init__(self, name:str, hour_wage:float):
        
        self.name = name
        self.hour_wage = hour_wage
        

    def oblicz_pensje(self, hours:int):
        
        return self.hour_wage*hours
    


class Programista(Pracownik):
    
    def __init__(self, name, hour_wage,programming_lang:list):
        super().__init__(name, hour_wage)
        
        self.programming_lang = programming_lang
        
        

developer = Programista("Jan", 35.45, ["Python", "C++", "Java"])

print(developer.oblicz_pensje(23))

