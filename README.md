# 🎮 Abalone Game (Django + JavaScript + AI Engine)

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Django](https://img.shields.io/badge/Django-Backend-green?logo=django)
![JavaScript](https://img.shields.io/badge/JavaScript-Frontend-yellow?logo=javascript)
![AI](https://img.shields.io/badge/AI-Minimax-orange)

A full-stack implementation of the classic strategic board game **Abalone**, built with a custom hex-grid engine, interactive web interface, and AI opponent using Minimax + Alpha-Beta pruning.

---

# 🚀 Features

## 🎯 Core Game

* 🟣 Hexagonal board (61 cells)
* ⚫⚪ Two-player system (White vs Black)
* 💥 Push mechanics (inline & lateral moves)
* 🎯 Capture system (push marbles off board)
* 🔄 Turn-based gameplay

---

## 🧠 AI System

* 🤖 Minimax algorithm
* ⚡ Alpha-Beta pruning optimization
* 📊 Evaluation function:

  * Captured marbles
  * Piece advantage
  * Positional strength

---

## 🌐 Frontend (JavaScript + Canvas)

* 🎮 Interactive hex board rendering
* 🖱️ Click-to-move system
* 📜 Move history tracking
* 🎬 Smooth animations
* 🔊 Sound effects (Web Audio API)

---

## ⚙️ Backend (Django)

* 🔌 REST-style game API
* 💾 Session-based persistence
* 📦 Game state serialization
* ✅ Move validation engine
* 🤖 AI move endpoint

---

# 🧩 Project Structure

```
src/
│
├── project/              # ⚙️ Settings & main URLs
│   ├── settings.py
│   ├── urls.py
│
├── game/                # 🎮 Game app
│   ├── game_engine.py   # 🧠 Core logic + AI
│   ├── views.py         # 🔌 API endpoints
│   ├── urls.py
│   ├── templates/
│   │   └── game/
│
├── home/                # 🏠 Home app
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   │   └── home/
│
├── static/              # 🎨 Static files
│   ├── script.js        # 🖥️ Game frontend logic
│   ├── home.js
│
├── db.sqlite3
└── manage.py
```

---

# 🎮 How to Run

## 1️⃣ Clone project

```bash
git clone <repo-url>
cd AbaloneGame
```

## 2️⃣ Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

## 3️⃣ Install dependencies

```bash
pip install django
```

## 4️⃣ Run migrations

```bash
python manage.py migrate
```

## 5️⃣ Start server

```bash
python manage.py runserver
```

## 6️⃣ Open browser

```
http://127.0.0.1:8000/
```

---

# 🧠 Game Rules

* Each player starts with 14 marbles
* 🎯 Objective: push 6 opponent marbles off the board
* Move 1–3 marbles per turn
* Two move types:

  * ↔️ Lateral move (sideways)
  * ➡️ Inline move (push)

---

# ⚙️ AI Algorithm

## 🧠 Minimax

AI simulates future moves to choose optimal decision:

* Maximize its score
* Minimize opponent score

## ⚡ Alpha-Beta Pruning

Optimizes search by cutting unnecessary branches.

## 📊 Evaluation Function

```
Score = (captured * 1000)
      + (piece advantage * 10)
      + positional advantage
```

---

# 🧠 Engine Highlights

* 🧭 Axial coordinates (q, r)
* 💥 Push & collision system
* 📏 Group validation (1–3 marbles)
* 📡 Line detection algorithm
* 🔄 Deep cloning for AI simulation

---

# 🎨 UI Features

* 🟣 Canvas hex board
* 🏷️ External coordinate labels
* ➡️ Move hints & arrows
* 🎬 Animations for moves
* 🔊 Sound effects
* 📜 Move history panel

---

# 📊 Architecture

```
Frontend (JS)
     ↓
Django API (Views)
     ↓
Game Engine (Python)
     ↓
AI System (Minimax)
```
