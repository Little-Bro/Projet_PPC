import random

class Card:
    def __init__(self, number, colour):
        self.number = number
        self.colour = colour
    def toString(self):
        return str(self.number) + ':' + self.colour

liste_cartes = []
pioche = []

for i in range(1,11):
    liste_cartes.append(Card(i, "R"))
    liste_cartes.append(Card(i, "B"))

#print(random.choice(liste_cartes).toString())

while len(liste_cartes) != 0:
    pioche.append(liste_cartes.pop(random.randint(0, len(liste_cartes)-1)))

def givePile():
    return pioche
#affichage des cartes pour tester
# for elt in pioche:
#     print(elt.toString())
