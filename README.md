# 🃏 7 e Mezzo Digital 

Un'applicazione web gestionale per il gioco del **7 e Mezzo**, sviluppata con **FastAPI** e **SQLAlchemy**.

## 🚀 Funzionalità
- **Gestione Giocatori:** Registrazione nuovi profili con budget iniziale di €100.
- **Scommesse Personalizzate:** Il giocatore sceglie quanto puntare ogni mano.
- **Leaderboard:** Classifica in tempo reale dei giocatori basata sul saldo.
- **Database Persistence:** I dati dei giocatori sono salvati su SQLite.
- **Session Reset:** Il database si azzera automaticamente a ogni riavvio del server per sessioni di test pulite.

## 🛠️ Stack Tecnologico
- **Backend:** FastAPI (Python 3.x)
- **Database:** SQLAlchemy con SQLite
- **Frontend:** HTML5, Bootstrap 5, Jinja2 Templates

## 💻 Come avviare il progetto
1. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   
2. Avvia il server:

  Bash
  python -m uvicorn main:app --reload

3. Vai all'indirizzo: http://127.0.0.1:8000

4. Nuova partita: Prima di avviare una nuova partita è necessario chiudere il terminale aperto in precedenza per avviarne uno nuovo, successivamente il gioco potrà continuare avviando nuovamente il server.

