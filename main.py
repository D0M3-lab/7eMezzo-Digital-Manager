import random
from typing import List
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- DATABASE SETUP ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./sette_e_mezzo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    balance = Column(Float, default=100.0)

# RESET ALL'AVVIO
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- LOGICA DI GIOCO ---
# Immaginiamo che il 10 rappresenti il Re di Denari (Matta) per semplicità
CARDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 4 
CARD_VALUES = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 0.5, 9: 0.5, 10: 0.5}

game_state = {
    "deck": [], "player_hand": [], "dealer_hand": [],
    "current_player_id": None, "bet": 0.0,
    "game_over": False, "result_message": "", "active": False
}

def calculate_score(hand: List[int]) -> float:
    """
    Calcola il punteggio. Il 10 è considerato la Matta.
    Regole Matta:
    - Da sola vale 0.5
    - Con altre carte, assume il valore intero necessario per arrivare a 7 o 7.5
    """
    # 1. Somma tutte le carte che NON sono la Matta (10)
    score = sum(CARD_VALUES[card] for card in hand if card != 10)
    
    # 2. Conta quante Matte ci sono nella mano
    num_matte = hand.count(10)

    # 3. Gestisci le Matte
    for _ in range(num_matte):
        if score == 0:
            # Caso: Matta da sola (o prima carta pescata se matta) -> vale 0.5
            score += 0.5
        elif score >= 7:
            # Caso: Punteggio già alto, la matta vale il minimo (0.5) per non sballare troppo
            score += 0.5
        else:
            # Caso: Matta usata come jolly per massimizzare il punteggio
            # Se lo score attuale è intero (es. 3.0), il massimo ottenibile è 7.0
            # Se lo score attuale è mezzo (es. 0.5), il massimo ottenibile è 7.5
            if score % 1 == 0:
                # Esempio: ho 3.0 -> Matta diventa 4 -> Totale 7.0
                score = 7.0
            else:
                # Esempio: ho 0.5 -> Matta diventa 7 -> Totale 7.5
                score = 7.5
                
    return score

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- ROTTE ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    players = db.query(Player).all()
    leaderboard = db.query(Player).order_by(Player.balance.desc()).limit(5).all()
    
    if game_state["active"]:
        player = db.query(Player).filter(Player.id == game_state["current_player_id"]).first()
        return templates.TemplateResponse("index.html", {
            "request": request, "player": player, "view": "game",
            "player_hand": game_state["player_hand"], 
            "dealer_hand": game_state["dealer_hand"] if game_state["game_over"] else [game_state["dealer_hand"][0]],
            "player_score": calculate_score(game_state["player_hand"]), 
            "game_over": game_state["game_over"],
            "result_message": game_state["result_message"], "bet": game_state["bet"]
        })
    return templates.TemplateResponse("index.html", {"request": request, "players": players, "leaderboard": leaderboard, "view": "menu"})

@app.post("/add-player")
async def add_player(username: str = Form(...), db: Session = Depends(get_db)):
    new_player = Player(username=username, balance=100.0)
    db.add(new_player)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/start-game")
async def start_game(player_id: int = Form(...), bet: float = Form(...), db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player or player.balance < bet or bet <= 0:
        return RedirectResponse(url="/", status_code=303)
    
    deck = CARDS.copy()
    random.shuffle(deck)
    game_state.update({
        "deck": deck, "player_hand": [deck.pop()], "dealer_hand": [deck.pop()],
        "current_player_id": player_id, "bet": bet,
        "game_over": False, "result_message": "", "active": True
    })
    return RedirectResponse(url="/", status_code=303)

@app.post("/hit")
async def hit(db: Session = Depends(get_db)): # Aggiunta dipendenza DB per gestire lo sballo
    if not game_state["game_over"]:
        game_state["player_hand"].append(game_state["deck"].pop())
        
        current_score = calculate_score(game_state["player_hand"])
        
        if current_score > 7.5:
            game_state["game_over"] = True
            game_state["result_message"] = "Hai Sballato! Vince il Banco."
            
            # --- FIX: Sottrazione soldi in caso di sballo immediato ---
            player = db.query(Player).filter(Player.id == game_state["current_player_id"]).first()
            if player:
                player.balance -= game_state["bet"]
                db.commit()
            # ----------------------------------------------------------

    return RedirectResponse(url="/", status_code=303)

@app.post("/stay")
async def stay(db: Session = Depends(get_db)):
    player_score = calculate_score(game_state["player_hand"])
    
    # Logica semplice Banco: pesca finché non supera il giocatore o arriva almeno a 6
    # Nota: Se il giocatore ha fatto 7.5 con 2 carte (reale), il banco dovrebbe perdere, 
    # ma qui teniamo la logica base del punteggio.
    while calculate_score(game_state["dealer_hand"]) < 7.5:
        ds = calculate_score(game_state["dealer_hand"])
        if ds > player_score and ds >= 6: # Se ha già vinto e ha un punteggio "decente", si ferma
             break
        if ds == player_score and ds >= 6: # Pareggio (vince banco), si ferma
             break
             
        game_state["dealer_hand"].append(game_state["deck"].pop())
    
    dealer_score = calculate_score(game_state["dealer_hand"])
    player = db.query(Player).filter(Player.id == game_state["current_player_id"]).first()

    # Logica vittoria:
    # 1. Giocatore non ha sballato (gestito prima, ma controlliamo)
    # 2. Banco sballa (> 7.5) OPPURE Giocatore > Banco
    if player_score <= 7.5 and (dealer_score > 7.5 or player_score > dealer_score):
        game_state["result_message"] = f"HAI VINTO! (Banco: {dealer_score})"
        player.balance += game_state["bet"]
    else:
        game_state["result_message"] = f"IL BANCO VINCE! (Banco: {dealer_score})"
        player.balance -= game_state["bet"]
    
    game_state["game_over"] = True
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/exit")
async def exit_game():
    game_state["active"] = False
    return RedirectResponse(url="/", status_code=303)
