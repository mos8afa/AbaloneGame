// ============================================================
// ABALONE GAME - FRONTEND (PURE VIEW LAYER)
// ============================================================
// All game logic lives in Django backend. This is ONLY the view/renderer.

// ---------------------- CSRF ----------------------
function getCSRFToken() {
    return document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1];
}

// ---------------------- GAME STATE (from backend) ----------------------
let gameState = {
    board: [],
    captured: { B: 0, W: 0 },
    turn: "player"
};
let isLoading = false;
let gameActive = false;

// ---------------------- RENDER STATE FROM BACKEND ----------------------
function updateFromBackend(state) {
    gameState = state;
    render();
    updateScoreDisplay();
    updateTurnIndicator();
}

function updateScoreDisplay() {
    const blackScore = document.getElementById("score-black");
    const whiteScore = document.getElementById("score-white");
    if (blackScore) blackScore.textContent = gameState.captured.B;
    if (whiteScore) whiteScore.textContent = gameState.captured.W;
}

function updateTurnIndicator() {
    const turnEl = document.getElementById("turn-indicator");
    if (turnEl) {
        turnEl.textContent = gameState.turn === "player" ? "Your turn" : "AI thinking...";
        turnEl.className = gameState.turn === "player" ? "turn-player" : "turn-ai";
    }
}

// ---------------------- API: START GAME ----------------------
async function startGame() {
    try {
        const response = await fetch("/api/start/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify({}),
        });

        if (!response.ok) throw new Error("Failed to start game");

        const data = await response.json();
        gameActive = true;
        updateFromBackend(data.state || data);
    } catch (error) {
        console.error("Start game error:", error);
        alert("Failed to start game: " + error.message);
    }
}

// ---------------------- API: GET STATE ----------------------
async function fetchState() {
    try {
        const response = await fetch("/api/state/");
        if (!response.ok) throw new Error("Failed to fetch state");

        const data = await response.json();
        if (data.status === "no_game") {
            // No active game, prompt to start
            return null;
        }
        updateFromBackend(data.state || data);
    } catch (error) {
        console.error("Fetch state error:", error);
    }
}

// ---------------------- API: SEND MOVE ----------------------
async function sendMove(group, target) {
    if (isLoading || !gameActive || gameState.turn !== "player") return;

    isLoading = true;
    canvas.style.cursor = "wait";

    try {
        const response = await fetch("/api/move/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify({ group, target }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || "Invalid move");
        }

        const data = await response.json();

        // Update UI with new state (includes AI move already)
        updateFromBackend(data.state || data);

        // Check for game over
        if (data.winner) {
            gameActive = false;
            const winnerMsg = data.winner === "W" ? "You win!" : "AI wins!";
            setTimeout(() => alert(winnerMsg), 100);
        }
    } catch (error) {
        console.error("Move error:", error);
        alert(`Move failed: ${error.message}`);
    } finally {
        isLoading = false;
        canvas.style.cursor = "default";
    }
}

// ---------------------- CANVAS SETUP ----------------------
const canvas = document.getElementById("board");
const ctx = canvas.getContext("2d");

const W = canvas.width,
    H = canvas.height;
const CX = W / 2,
    CY = H / 2;

const ROW_COUNTS = [5, 6, 7, 8, 9, 8, 7, 6, 5];

const R = 26;
const DX = 62;
const DY = 54;

// ---------------------- BOARD POSITION ----------------------
function cellPos(row, col) {
    const count = ROW_COUNTS[row];
    return {
        x: CX - ((count - 1) * DX) / 2 + col * DX,
        y: CY + (row - 4) * DY,
    };
}

// ---------------------- RENDER (PURE VIEW) ----------------------
function drawBoard() {
    ctx.clearRect(0, 0, W, H);

    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < ROW_COUNTS[r]; c++) {
            const { x, y } = cellPos(r, c);

            // hole
            ctx.beginPath();
            ctx.arc(x, y, R, 0, Math.PI * 2);
            ctx.fillStyle = "#1a2a40";
            ctx.fill();

            const p = gameState.board[r]?.[c];

            if (p && p !== "") {
                ctx.beginPath();
                ctx.arc(x, y, R, 0, Math.PI * 2);
                ctx.fillStyle = p === "W" ? "#eee" : "#111";
                ctx.fill();
            }
        }
    }

    drawSelection();
}

function render() {
    drawBoard();
}

// ---------------------- SELECTION (UI only, no game logic) ----------------------
let selectedGroup = [];

function isInGroup(row, col) {
    return selectedGroup.some((g) => g.row === row && g.col === col);
}

function drawSelection() {
    selectedGroup.forEach(({ row, col }) => {
        const { x, y } = cellPos(row, col);

        ctx.beginPath();
        ctx.arc(x, y, R + 6, 0, Math.PI * 2);
        ctx.strokeStyle = "gold";
        ctx.lineWidth = 3;
        ctx.stroke();
    });
}

// ---------------------- CLICK HANDLER ----------------------
canvas.addEventListener("click", async (e) => {
    if (isLoading || !gameActive || gameState.turn !== "player") return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (W / rect.width);
    const y = (e.clientY - rect.top) * (H / rect.height);

    let clicked = null,
        min = Infinity;

    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < ROW_COUNTS[r]; c++) {
            const p = cellPos(r, c);
            const d = Math.hypot(x - p.x, y - p.y);
            if (d < min) {
                min = d;
                clicked = { row: r, col: c };
            }
        }
    }

    if (!clicked || min > R + 10) return;

    const { row, col } = clicked;
    const piece = gameState.board[row]?.[col];

    // deselect
    if (isInGroup(row, col)) {
        selectedGroup = selectedGroup.filter(
            (g) => !(g.row === row && g.col === col),
        );
        render();
        return;
    }

    // select (only own pieces - assuming player is White)
    if (piece && piece === "W" && selectedGroup.length < 3) {
        selectedGroup.push({ row, col });
        render();
        return;
    }

    // send move to backend (backend validates rules)
    if (selectedGroup.length > 0) {
        await sendMove(selectedGroup, { row, col });
        selectedGroup = [];
        render();
    }
});

// ---------------------- INITIALIZE ----------------------
function initGame() {
    selectedGroup = [];
    startGame();
}

// Auto-start when loaded
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGame);
} else {
    initGame();
