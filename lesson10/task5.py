class Figura:

    def oblicz_pole(self):
        pass


class Kwadrat(Figura):

    def __init__(self, bok: float):

        self.bok = bok

    def oblicz_pole(self):

        return self.bok * self.bok


class Kolo(Figura):

    def __init__(self, promien: float):

        self.promien = promien

    def oblicz_pole(self):

        return 3.14159 * self.promien * self.promien


figury = [Kwadrat(23), Kolo(23)]

for figura in figury:
    
    print(figura.oblicz_pole())