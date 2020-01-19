import threading
import sysv_ipc
import sys
import os
from multiprocessing import Process, Lock, Manager
from generePioche import * 

pile = givePile()
number_of_players = 2
lock1 = Lock() # lock pour la première message queue
lock2 = Lock() # lock pour la deuxième message queue
option = int(sys.argv[1]) # sert à savoir si on lance le board où les joueurs

# ---------PLAYER---------
def player(player_number, fileno, lock1, lock2): 
    sys.stdin = os.fdopen(fileno) # sert à utiliser input() dans le process
    mq = sysv_ipc.MessageQueue(420) # message queue pour les cartes
    pile_mq = sysv_ipc.MessageQueue(666) # message queue pour la pioche
    hand = [] # main du joueur

    # recupération de la main
    for i in range(5):
        with lock1:
            card, t = mq.receive(player_number)
        card = card.decode()
        card = makeCard(card)
        hand.append(card)
    displayCards(hand) # affichage de la main

    with Manager() as manager:
        hand = manager.list(hand) # la main est une ressource partagée avec le process time
        time = Process(target=timer, args=(pile_mq, lock2, hand))
        time.start()

        # boucle de jeu
        while len(hand) > 0:
            # demande au joueur d'entrer sa carte
            move =input("Enter your move : ")
            card_move = makeCard(move)

            # vérifie que la carte jouée est bien dans la main du joueur
            while not cardInHand(card_move, hand):
                print("You do not have this card in your hand, try again")
                move =input("Enter your move : ")
                card_move = makeCard(move)
            
            # envoi de la carte
            time.terminate()
            attempt = move.encode()   
            with lock1:    
                mq.send(attempt,True, player_number)
            print("message sent !")
            
            # reception du message du board
            with lock1:    
                message, t = mq.receive(True, player_number + 2)
            message = message.decode()

            print("received : ", message)

            # réaction au message du board
            if message == "valid":
                del hand[removeCard(card_move, hand)]
                displayCards(hand)
            elif message == "invalid":
                with lock2:    
                    new_card, t = pile_mq.receive()
                new_card = new_card.decode()
                new_card = makeCard(new_card)
                hand.append(new_card)
                displayCards(hand)
        
        # le joueur a gagné, sa main est vide 
        time    .terminate()
        print("YOU WIN ! ")
        win_message = "WIN".encode()
        with lock1:    
            mq.send(win_message, True, player_number + 4)

# ---------FONCTIONS UTILES---------

# process timer qui compte le temps entre chaque carte proposée
def timer(pile_mq, lock2, hand):
    while True:
        temps = 0
        while temps < 10:
            temps = temps + 0.0000001
        # QUOI
        with lock2:    
                new_card, t = pile_mq.receive()
        new_card = new_card.decode()
        new_card = makeCard(new_card)
        hand.append(new_card)
        print("\n")
        displayCards(hand)
        print("Enter your move : ")

# vérifie si la carte jouée est valide
def isValid(move_c, move_n, board_c, board_n):
    same_colour = move_c == board_c
    adjacent_numbers = move_n == board_n + 1 or move_n == board_n - 1

    if (move_n == board_n and not same_colour) or (adjacent_numbers and same_colour):
        return True
    else:
        return False

# vérifie si la carte jouée est bien dans la main du joueur
def cardInHand(card, hand):
    for elt in hand:
        if card.toString() == elt.toString():
            return True
    return False

class WrongColourError(Exception):
    pass

# affiche les cartes d'une main
def displayCards(hand):
    for elt in hand:
        print(elt.toString())

# retire une carte d'une main
def removeCard(card, hand):
    a = 0
    for i in range(len(hand)):
        if card.toString() == hand[i].toString():
            a = i
    return a

# initialise une liste de mains pour les joueurs en début de partie (une main par joueur)
def hands_initialisation():
    list_hands = []
    for i in range(number_of_players):
        hand = []
        for j in range(5):
            hand.append(pile.pop(0))
        list_hands.append(hand)
    return list_hands

# créé un objet Card à partir d'une chaine de caractères
def makeCard(strCard):
    split_card = strCard.split(':')
    try:
        colour = split_card[1]
        if colour != "R" and colour != "B":
            raise WrongColourError
        number = int(split_card[0])
        assert number > 0 and number <= 10
        card = Card(number, colour)
        
    except IndexError:
        print("Move must be of type number:colour")
    except AssertionError:
        print("Number must be between 1 and 10")
    except ValueError:
        print("Move must be of type number:colour")
    except WrongColourError:
        print("Colour must be R or B")
    except AttributeError:
        print("Card could not be made")
    finally:
        return card   



# ---------BOARD---------
def board(list_hands, lock1, lock2):
    message_queue = sysv_ipc.MessageQueue(420, sysv_ipc.IPC_CREAT) # message queue pour les cartes
    pile_message_queue = sysv_ipc.MessageQueue(666, sysv_ipc.IPC_CREAT) # message queue pour la pioche
    # message_queue.remove()
    # pile_message_queue.remove()

    #envoi des mains aux joueurs connectés
    for i in range(number_of_players):
        for j in range(5):
            distributed_hand = list_hands[i][j].toString().encode()
            with lock1:
                message_queue.send(distributed_hand, i)
    
    #initialisation 
    board_card = pile.pop(0)

    # on remplit la deuxième message queue avec la pioche (9 cartes)
    for elt in pile:
        encoded_card = elt.toString().encode()
        with lock2:    
            pile_message_queue.send(encoded_card)

    # on attend que chaque joueur ait reçu ses cartes avant d'écouter à nouveau
    while message_queue.current_messages != 0:
        pass

    # les deux joueurs sont connectés
    print("**************************")
    print("THE GAME IS READY TO START")
    print("**************************")

    print("BOARD CARD : " +board_card.toString())

    # tant qu'il reste des cartes dans la pioche
    while pile_message_queue.current_messages > 0:
        # print("nombre de cartes dans la pioche ",  pile_message_queue.current_messages)
        if len(pile) == 0:
            break

        with lock1: 
            move, t = message_queue.receive()

        # prise en compte de la carte proposée par le joueur
        if t == 1 or t == 2:
            move = move.decode()
            player_move = move.split(':')
            card_played = Card(int(player_move[0]), player_move[1])

            # vérification de la validité de la carte proposée par le joueur        
            if isValid(card_played.colour, card_played.number, board_card.colour, board_card.number):
                board_card = card_played
                print("BOARD CARD : " +board_card.toString())
                confirmation = "valid".encode()
                with lock1:    
                    message_queue.send(confirmation, True, t + 2)
            else:
                denial = "invalid".encode()
                with lock1:    
                    message_queue.send(denial, True, t + 2)
        
        # si un des joueurs a gagné
        if t == 5 or t == 6:
            print("\n PLAYER ", t - 4," WINS \n")
            break
    print("**************************")
    print("        GAME OVER")
    print("**************************")
    pile_message_queue.remove()
    message_queue.remove()

# création d'un process board
if option == 0:
    print("BOARD IS ALIVE")
    list_hands = hands_initialisation()
    board = Process(target=board, args=(list_hands, lock1, lock2))
    board.start()
    board.join()

# création d'un process joueur
if option > 0:
    print("PLAYER ", option, " IS ALIVE")
    fn = sys.stdin.fileno()
    player = Process(target=player, args=(option, fn, lock1, lock2))
    player.start()    
    player.join()