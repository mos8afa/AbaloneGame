// ══════════════════════════════════════════════════════════════
// 1. CANVAS
// ══════════════════════════════════════════════════════════════
const canvas = document.getElementById("board");
const ctx = canvas.getContext("2d");

const BOARD_W = 640;
const BOARD_H = 560;
canvas.width = BOARD_W;
canvas.height = BOARD_H;

// Board is shifted right/up to leave room for label strips
const CX = BOARD_W / 2 + 20;
const CY = BOARD_H / 2 - 10;

const ROW_COUNTS = [5, 6, 7, 8, 9, 8, 7, 6, 5];
const R = 25;   // marble radius
const DX = 58;   // horizontal cell spacing
const DY = 50;   // vertical   cell spacing
const ANIM_MS = 200;  // marble animation duration (ms)

// ══════════════════════════════════════════════════════════════
// 2. BOARD FLIP
// ══════════════════════════════════════════════════════════════
function cellPos(row, col) {
  const displayRow = 8 - row;
  const count = ROW_COUNTS[row];
  return {
    x: CX - ((count - 1) * DX) / 2 + col * DX,
    y: CY + (displayRow - 4) * DY,
  };
}

// ══════════════════════════════════════════════════════════════
// 3. UNIFIED COORDINATE DISPLAY LAYER
// ══════════════════════════════════════════════════════════════
const ORD_A = "a".charCodeAt(0);

function cellLabel({ row, col }) {
  return `${col + 1}${String.fromCharCode(ORD_A + row)}`;
}

function cellsLabel(cells) {
  return cells.map(cellLabel).join("-");
}

// ══════════════════════════════════════════════════════════════
// 4. HEX COORDINATE HELPERS
// ══════════════════════════════════════════════════════════════
const Q_MIN_MAP = {
  "-4": 0, "-3": -1, "-2": -2, "-1": -3,
  "0": -4, "1": -4, "2": -4, "3": -4, "4": -4,
};

const HEX_DIRS = [
  { dq: 1, dr: 0 }, { dq: -1, dr: 0 },
  { dq: 0, dr: 1 }, { dq: 0, dr: -1 },
  { dq: 1, dr: -1 }, { dq: -1, dr: 1 },
];

function frontendToBackend(row, col) {
  const r = row - 4;
  return { q: col + Q_MIN_MAP[String(r)], r };
}

function backendToFrontend(q, r) {
  return { row: r + 4, col: q - Q_MIN_MAP[String(r)] };
}

function isOnBoard(row, col) {
  return row >= 0 && row < 9 && col >= 0 && col < ROW_COUNTS[row];
}

// ══════════════════════════════════════════════════════════════
// 5. CSRF
// ══════════════════════════════════════════════════════════════
function getCSRFToken() {
  return (
    document.cookie
      .split("; ")
      .find((r) => r.startsWith("csrftoken="))
      ?.split("=")[1] || ""
  );
}

// ══════════════════════════════════════════════════════════════
// 6. SOUND  (Web Audio API — procedural, zero external files)
// ══════════════════════════════════════════════════════════════
let audioCtx = null;
let muted = false;

function _getAudioCtx() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
  return audioCtx;
}

function _tone(opts) {
  if (muted) return;
  try {
    const ac = _getAudioCtx();
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.connect(gain);
    gain.connect(ac.destination);
    osc.type = opts.type || "sine";
    osc.frequency.value = opts.freq || 440;
    gain.gain.setValueAtTime(opts.vol || 0.18, ac.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + (opts.dur || 0.18));
    if (opts.freqEnd) {
      osc.frequency.linearRampToValueAtTime(opts.freqEnd, ac.currentTime + (opts.dur || 0.18));
    }
    osc.start(ac.currentTime);
    osc.stop(ac.currentTime + (opts.dur || 0.18) + 0.02);
  } catch (_) { }
}

const SFX = {
  select() { _tone({ type: "sine", freq: 520, freqEnd: 620, dur: 0.10, vol: 0.12 }); },
  deselect() { _tone({ type: "sine", freq: 400, freqEnd: 320, dur: 0.08, vol: 0.08 }); },
  move() { _tone({ type: "triangle", freq: 300, freqEnd: 180, dur: 0.18, vol: 0.20 }); },
  push() {
    _tone({ type: "sawtooth", freq: 200, freqEnd: 100, dur: 0.22, vol: 0.18 });
    setTimeout(() => _tone({ type: "sine", freq: 160, dur: 0.14, vol: 0.12 }), 80);
  },
  capture() {
    _tone({ type: "sawtooth", freq: 180, freqEnd: 60, dur: 0.30, vol: 0.25 });
    setTimeout(() => _tone({ type: "sine", freq: 100, dur: 0.20, vol: 0.15 }), 120);
  },
  invalid() { _tone({ type: "square", freq: 160, freqEnd: 120, dur: 0.12, vol: 0.10 }); },
  win() {
    [0, 100, 200, 320].forEach((t, i) =>
      setTimeout(() => _tone({ type: "sine", freq: [523, 659, 784, 1047][i], dur: 0.25, vol: 0.18 }), t)
    );
  },
  lose() {
    [0, 150, 300].forEach((t, i) =>
      setTimeout(() => _tone({ type: "triangle", freq: [392, 330, 262][i], dur: 0.30, vol: 0.18 }), t)
    );
  },
};

function toggleMute() {
  muted = !muted;
  const btn = document.getElementById("mute-btn");
  if (btn) btn.textContent = muted ? "🔇" : "🔊";
}

// ══════════════════════════════════════════════════════════════
// 7. GAME STATE
// ══════════════════════════════════════════════════════════════
let gameState = {
  board: [],
  captured: { B: 0, W: 0 },
  turn: "player",
};
let isLoading = false;
let gameActive = false;
let selectedGroup = [];
let moveHistory = [];
let hoverCell = null;

// ── Difficulty selection ──────────────────────────────────────

const _urlParams        = new URLSearchParams(window.location.search);
const selectedDifficulty = parseInt(_urlParams.get("difficulty") || "3", 10);

const DIFFICULTY_LABELS = { 1: "Easy", 2: "King Mode", 3: "Expert" };
const DIFFICULTY_COLORS = {
  1: "rgba(130,255,150,0.85)",
  2: "rgba(255,210,80,0.90)",
  3: "rgba(255,130,130,0.85)",
};
const AI_SUB_LABELS = {
  1: "Black marbles · Easy",
  2: "Black king · King Mode",
  3: "Black marbles · Expert",
};

let animQueue = [];

let hintSet = new Set();

let animSet = new Set();

let invalidFlashUntil = 0;

// ══════════════════════════════════════════════════════════════
// 8. HINT CELL COMPUTATION
// ══════════════════════════════════════════════════════════════
function computeHintCells() {
  hintSet.clear();
  if (selectedGroup.length === 0) return;

  selectedGroup.forEach(({ row, col }) => {
    const { q, r } = frontendToBackend(row, col);
    HEX_DIRS.forEach(({ dq, dr }) => {
      const nf = backendToFrontend(q + dq, r + dr);
      if (!isOnBoard(nf.row, nf.col)) return;
      const inGroup = selectedGroup.some(g => g.row === nf.row && g.col === nf.col);
      if (!inGroup) hintSet.add(`${nf.row},${nf.col}`);
    });
  });
}


// ══════════════════════════════════════════════════════════════
// 9. RENDERING
// ══════════════════════════════════════════════════════════════

// Colour constants
const CLR = {
  hole: "#1a2a40",
  selRing: "#ffe066",
  hintRing: "rgba(100,220,255,0.55)",
  hintFill: "rgba(100,220,255,0.10)",
  hoverRing: "rgba(255,255,255,0.30)",
  invalidFlash: "rgba(255,80,80,0.55)",
};

// Label strip constants
const STRIP_W = 26;
const STRIP_FILL = "rgba(255,255,255,0.07)";
const STRIP_STROKE = "rgba(255,255,255,0.20)";
const STRIP_TEXT = "rgba(255,255,255,0.85)";
const STRIP_SHADOW = "rgba(0,0,0,0.70)";

function render() {
  ctx.clearRect(0, 0, BOARD_W, BOARD_H);
  _drawBoardBackground();
  _drawCells();
  _drawAnimatingMarbles();
}

function _drawBoardBackground() {
  const grad = ctx.createRadialGradient(CX, CY, 10, CX, CY, 260);
  grad.addColorStop(0, "#2a3d55");
  grad.addColorStop(1, "#1a2535");
  ctx.beginPath();
  ctx.arc(CX, CY, 258, 0, Math.PI * 2);
  ctx.fillStyle = grad;
  ctx.fill();
}


// ── Cells + marbles ───────────────────────────────────────────
function _drawCells() {
  const now = performance.now();
  const showInvalid = now < invalidFlashUntil;

  for (let row = 0; row < 9; row++) {
    for (let col = 0; col < ROW_COUNTS[row]; col++) {
      const { x, y } = cellPos(row, col);
      const key = `${row},${col}`;
      const piece = gameState.board[row]?.[col];
      const inSel = _isInGroup(row, col);
      const isHover = hoverCell && hoverCell.row === row && hoverCell.col === col;
      const isHint = hintSet.has(key);   // O(1) — was O(n)

      // drop shadow
      ctx.beginPath();
      ctx.arc(x, y + 2, R + 1, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0,0,0,0.38)";
      ctx.fill();

      // hole
      ctx.beginPath();
      ctx.arc(x, y, R, 0, Math.PI * 2);
      ctx.fillStyle = CLR.hole;
      ctx.fill();

      // hint ring
      if (isHint) {
        ctx.beginPath();
        ctx.arc(x, y, R, 0, Math.PI * 2);
        ctx.fillStyle = CLR.hintFill;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x, y, R + 4, 0, Math.PI * 2);
        ctx.strokeStyle = CLR.hintRing;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(100,220,255,0.45)";
        ctx.fill();
      }

      // invalid flash
      if (showInvalid && inSel) {
        ctx.beginPath();
        ctx.arc(x, y, R, 0, Math.PI * 2);
        ctx.fillStyle = CLR.invalidFlash;
        ctx.fill();
      }

      // marble 
      if (piece && piece !== "" && !animSet.has(key)) {
        _drawMarble(x, y, piece);
      }

      // selection ring
      if (inSel) {
        ctx.beginPath();
        ctx.arc(x, y, R + 6, 0, Math.PI * 2);
        ctx.strokeStyle = CLR.selRing;
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(x, y, R + 3, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255,224,102,0.35)";
        ctx.lineWidth = 5;
        ctx.stroke();
      }

      // hover ring
      if (isHover && (piece === "W" || piece === "WK") && !inSel) {
        ctx.beginPath();
        ctx.arc(x, y, R + 4, 0, Math.PI * 2);
        ctx.strokeStyle = CLR.hoverRing;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
  }
}

function _drawMarble(x, y, piece) {
  const isWhite     = piece === "W";
  const isWhiteKing = piece === "WK";  // ===== MEDIUM: player king =====
  const isBlackKing = piece === "BK";  // ===== MEDIUM: AI king =====

  const g = ctx.createRadialGradient(x - R * 0.32, y - R * 0.36, R * 0.04, x, y, R);
  if (isWhite) {
    g.addColorStop(0, "#ffffff");
    g.addColorStop(0.55, "#e0e0e0");
    g.addColorStop(1, "#a8a8a8");
  } else if (isWhiteKing) {
    // Gold / amber — clearly distinct from white
    g.addColorStop(0, "#fff8b0");
    g.addColorStop(0.45, "#d4a000");
    g.addColorStop(1, "#6a4000");
  } else if (isBlackKing) {
    // Purple / violet — clearly distinct from black
    g.addColorStop(0, "#d8a8ff");
    g.addColorStop(0.45, "#7010c8");
    g.addColorStop(1, "#200050");
  } else {
    // Normal black marble
    g.addColorStop(0, "#6a6a6a");
    g.addColorStop(0.45, "#252525");
    g.addColorStop(1, "#080808");
  }
  ctx.beginPath();
  ctx.arc(x, y, R, 0, Math.PI * 2);
  ctx.fillStyle = g;
  ctx.fill();

  // rim
  ctx.beginPath();
  ctx.arc(x, y, R, 0, Math.PI * 2);
  if (isWhiteKing)      ctx.strokeStyle = "rgba(255,200,0,0.55)";
  else if (isBlackKing) ctx.strokeStyle = "rgba(180,80,255,0.55)";
  else ctx.strokeStyle = isWhite ? "rgba(0,0,0,0.10)" : "rgba(255,255,255,0.06)";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // primary specular
  ctx.beginPath();
  ctx.arc(x - R * 0.28, y - R * 0.30, R * 0.22, 0, Math.PI * 2);
  if (isWhiteKing)      ctx.fillStyle = "rgba(255,255,190,0.80)";
  else if (isBlackKing) ctx.fillStyle = "rgba(220,160,255,0.55)";
  else ctx.fillStyle = isWhite ? "rgba(255,255,255,0.80)" : "rgba(255,255,255,0.20)";
  ctx.fill();

  // secondary specular
  ctx.beginPath();
  ctx.arc(x - R * 0.10, y - R * 0.55, R * 0.10, 0, Math.PI * 2);
  ctx.fillStyle = (isWhite || isWhiteKing) ? "rgba(255,255,255,0.50)" : "rgba(255,255,255,0.10)";
  ctx.fill();

  // Crown symbol on king pieces
  if (isWhiteKing || isBlackKing) {
    ctx.font = `bold ${Math.round(R * 0.82)}px serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = isWhiteKing ? "rgba(50,25,0,0.90)" : "rgba(240,200,255,0.95)";
    ctx.fillText("♛", x, y + R * 0.06);
  }
}

function _drawAnimatingMarbles() {
  animQueue.forEach(a => {
    const t = _easeInOut(a.t);
    _drawMarble(
      a.fromX + (a.toX - a.fromX) * t,
      a.fromY + (a.toY - a.fromY) * t,
      a.piece
    );
  });
}

function _easeInOut(t) {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

// ══════════════════════════════════════════════════════════════
// 10. ANIMATION ENGINE
// ══════════════════════════════════════════════════════════════
function animateMove(oldBoard, newBoard) {
  return new Promise(resolve => {
    const disappeared = [], appeared = [];

    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < ROW_COUNTS[r]; c++) {
        const oldP = oldBoard[r]?.[c] || "";
        const newP = newBoard[r]?.[c] || "";
        if (oldP !== "" && newP === "") disappeared.push({ row: r, col: c, piece: oldP });
        if (oldP === "" && newP !== "") appeared.push({ row: r, col: c, piece: newP });
      }
    }

    const matched = new Set();
    const entries = [];

    disappeared.forEach(d => {
      let best = null, bestDist = Infinity;
      appeared.forEach((a, i) => {
        if (matched.has(i) || a.piece !== d.piece) return;
        const dist = Math.hypot(a.row - d.row, a.col - d.col);
        if (dist < bestDist) { bestDist = dist; best = i; }
      });
      if (best !== null) {
        matched.add(best);
        const a = appeared[best];
        const from = cellPos(d.row, d.col);
        const to = cellPos(a.row, a.col);
        entries.push({ row: a.row, col: a.col, fromX: from.x, fromY: from.y, toX: to.x, toY: to.y, piece: d.piece, t: 0 });
      }
    });

    if (entries.length === 0) { resolve(); return; }

    animQueue = entries;
    animSet = new Set(entries.map(e => `${e.row},${e.col}`));

    let startTime = null;
    function step(ts) {
      if (!startTime) startTime = ts;
      const progress = Math.min((ts - startTime) / ANIM_MS, 1);
      animQueue.forEach(a => { a.t = progress; });
      render();
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        animQueue = [];
        animSet = new Set();
        resolve();
      }
    }
    requestAnimationFrame(step);
  });
}

// ══════════════════════════════════════════════════════════════
// 11. SELECTION
// ══════════════════════════════════════════════════════════════
function _isInGroup(row, col) {
  return selectedGroup.some(g => g.row === row && g.col === col);
}

function triggerInvalidFlash() {
  SFX.invalid();
  invalidFlashUntil = performance.now() + 350;
  let frames = 0;
  (function flashFrame() {
    render();
    if (++frames < 20) requestAnimationFrame(flashFrame);
  })();
}

// ══════════════════════════════════════════════════════════════
// 12. SCORE / TRAY
// ══════════════════════════════════════════════════════════════
function updateScoreDisplay() {
  const bEl = document.getElementById("score-black");
  const wEl = document.getElementById("score-white");
  if (bEl) bEl.textContent = gameState.captured.B;
  if (wEl) wEl.textContent = gameState.captured.W;
  _renderTray("tray-black", gameState.captured.B, "black", 6);
  _renderTray("tray-white", gameState.captured.W, "white", 6);
}

function _renderTray(id, count, cls, max) {
  const tray = document.getElementById(id);
  if (!tray) return;
  tray.innerHTML = "";
  for (let i = 0; i < max; i++) {
    const el = document.createElement("div");
    el.className = i < count ? `tray-marble ${cls}` : "tray-slot";
    if (i < count) el.style.animationDelay = `${i * 0.05}s`;
    tray.appendChild(el);
  }
}

function _flashScore(side) {
  const el = document.getElementById(side === "you" ? "score-side-you" : "score-side-ai");
  if (!el) return;
  el.classList.remove("flash");
  void el.offsetWidth;
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 600);
}

function _popScore(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("pop");
  void el.offsetWidth;
  el.classList.add("pop");
  setTimeout(() => el.classList.remove("pop"), 400);
}

// ══════════════════════════════════════════════════════════════
// 13. HINT TEXT
// ══════════════════════════════════════════════════════════════
function setHint(text) {
  const el = document.getElementById("hint");
  if (el) el.textContent = text;
}

// ══════════════════════════════════════════════════════════════
// 14. MOVE HISTORY
// ══════════════════════════════════════════════════════════════
function addHistory(who, cells, capture) {
  // cellsLabel() is the single coordinate display source of truth.
  // Same formula as drawLabels(): chr(ORD_A + row), col+1.
  moveHistory.push({ who, notation: cellsLabel(cells), capture });
  _renderHistory();
}

function _renderHistory() {
  const list = document.getElementById("history-list");
  const countEl = document.getElementById("history-count");
  if (!list) return;

  list.innerHTML = "";
  const pairs = [];
  let pair = null;

  moveHistory.forEach(m => {
    if (m.who === "you") {
      pair = { num: pairs.length + 1, you: m, ai: null };
      pairs.push(pair);
    } else if (pair && pair.ai === null) {
      pair.ai = m;
    } else {
      pairs.push({ num: pairs.length + 1, you: null, ai: m });
    }
  });

  pairs.forEach((p, idx) => {
    const rowEl = document.createElement("div");
    rowEl.className = "move-pair";

    const numEl = document.createElement("div");
    numEl.className = "move-num";
    numEl.textContent = p.num;
    rowEl.appendChild(numEl);

    ["you", "ai"].forEach(side => {
      const cell = document.createElement("div");
      const m = p[side];
      cell.className = `move-cell ${side}${idx === pairs.length - 1 ? " latest" : ""}`;
      if (m) {
        const dot = document.createElement("div");
        dot.className = `move-dot ${side === "you" ? "white" : "black"}`;
        cell.appendChild(dot);
        cell.appendChild(document.createTextNode(m.notation));
        if (m.capture) {
          const cap = document.createElement("span");
          cap.className = "move-capture";
          cap.textContent = "✕";
          cell.appendChild(cap);
        }
      }
      rowEl.appendChild(cell);
    });

    list.appendChild(rowEl);
  });

  list.scrollTop = list.scrollHeight;
  if (countEl) countEl.textContent = `${moveHistory.length} moves`;
}

// ══════════════════════════════════════════════════════════════
// 15. GAME OVER OVERLAY
// ══════════════════════════════════════════════════════════════
function showGameOver(winner) {
  const existing = document.getElementById("gameover-overlay");
  if (existing) existing.remove();

  const isWin = winner === "W";
  if (isWin) SFX.win(); else SFX.lose();

  const overlay = document.createElement("div");
  overlay.id = "gameover-overlay";
  overlay.style.cssText = [
    "position:fixed;inset:0;z-index:999;",
    "display:flex;flex-direction:column;",
    "align-items:center;justify-content:center;",
    "background:rgba(0,0,0,0.75);",
    "font-family:'Nunito',sans-serif;",
    "animation:fadeIn 0.4s ease;",
  ].join("");

  const color = isWin ? "#ffe066" : "#ff8888";
  const shadow = isWin ? "#ffe066" : "#ff6666";
  overlay.innerHTML = `
    <style>@keyframes fadeIn{from{opacity:0;transform:scale(0.92)}to{opacity:1;transform:scale(1)}}</style>
    <div style="font-size:72px;margin-bottom:18px;filter:drop-shadow(0 0 24px ${shadow})">${isWin ? "🏆" : "🤖"}</div>
    <div style="font-size:40px;font-weight:900;color:${color};margin-bottom:10px;letter-spacing:2px">${isWin ? "You Win!" : "AI Wins!"}</div>
    <div style="font-size:14px;color:rgba(255,255,255,0.45);margin-bottom:40px">${isWin ? "Excellent strategy!" : "Better luck next time!"}</div>
    <button onclick="restartGame()" style="padding:15px 52px;font-family:'Nunito',sans-serif;font-size:15px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#fff;background:linear-gradient(135deg,#4a6ad8,#2e4ab0);border:none;border-radius:50px;cursor:pointer;box-shadow:0 6px 28px rgba(50,80,200,0.55);transition:transform 0.15s" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform=''">▶ &nbsp;Play Again</button>
  `;
  document.body.appendChild(overlay);
}

function restartGame() {
  const overlay = document.getElementById("gameover-overlay");
  if (overlay) overlay.remove();
  moveHistory = [];
  _renderHistory();
  startGame();
}

// ══════════════════════════════════════════════════════════════
// 16. STATE UPDATE FROM BACKEND
// ══════════════════════════════════════════════════════════════
async function updateFromBackend(data, opts = {}) {
  const s = data.state || data;
  const oldBoard = gameState.board.map(r => [...r]);

  if (s.board) gameState.board = s.board;
  if (s.captured) gameState.captured = s.captured;
  if (s.turn) gameState.turn = s.turn;

  if (opts.animate && oldBoard.length > 0) {
    await animateMove(oldBoard, gameState.board);
  }

  selectedGroup = [];
  hintSet.clear();
  render();

  const prevB = opts.prevB ?? 0;
  const prevW = opts.prevW ?? 0;
  if (gameState.captured.B > prevB) { _popScore("score-black"); _flashScore("you"); }
  if (gameState.captured.W > prevW) { _popScore("score-white"); _flashScore("ai"); }

  updateScoreDisplay();
  setHint(
    gameState.turn === "player"
      ? "Select up to 3 white marbles, then click a destination"
      : "AI is thinking…"
  );
}

// ══════════════════════════════════════════════════════════════
// 17. API CALLS
// ══════════════════════════════════════════════════════════════
function _post(url, body) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
    body: JSON.stringify(body),
  });
}

async function startGame() {
  isLoading = true;
  setHint("Starting game…");

  // ── Apply difficulty labels to UI ────────────────────────────
  const label = DIFFICULTY_LABELS[selectedDifficulty] || "Expert";
  const color = DIFFICULTY_COLORS[selectedDifficulty] || DIFFICULTY_COLORS[3];
  const badge = document.getElementById("level-badge");
  if (badge) { badge.textContent = label; badge.style.color = color; }
  const aiSub = document.getElementById("ai-sub");
  if (aiSub) aiSub.textContent = AI_SUB_LABELS[selectedDifficulty] || AI_SUB_LABELS[3];

  try {
    // Pass selectedDifficulty to the backend (1=easy, 2=medium, 3=hard)
    const res = await _post("/game/start/", { difficulty: selectedDifficulty });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    gameActive = true;
    selectedGroup = [];
    hintSet.clear();
    await updateFromBackend(data, { animate: false });
  } catch (err) {
    setHint("Failed to start game — refresh the page.");
  } finally {
    isLoading = false;
  }
}

async function sendMove(group, target) {
  if (isLoading || !gameActive || gameState.turn !== "player") return;

  isLoading = true;
  canvas.style.cursor = "wait";
  setHint("Processing move…");

  const prevB = gameState.captured.B;
  const prevW = gameState.captured.W;

  try {
    const res = await _post("/game/move/", { group, target });
    const data = await res.json();

    if (!res.ok) {
      triggerInvalidFlash();
      setHint(data.error || "Invalid move — try again");
      return;
    }

    if (data.captured) SFX.capture(); else SFX.move();
    addHistory("you", group, data.captured);
    await updateFromBackend(data, { prevB, prevW, animate: true });

    if (data.game_over) { gameActive = false; showGameOver(data.winner); return; }

    await _requestAiMove();
  } catch (_) {
    setHint("Move failed — try again");
  } finally {
    isLoading = false;
    canvas.style.cursor = "default";
  }
}

async function _requestAiMove() {
  setHint("AI is thinking…");
  const prevB = gameState.captured.B;
  const prevW = gameState.captured.W;

  try {
    const res = await _post("/game/ai/", {});
    const data = await res.json();
    if (!res.ok) return;

    if (data.captured) SFX.push(); else SFX.move();
    if (data.ai_move) addHistory("ai", data.ai_move, data.captured);
    await updateFromBackend(data, { prevB, prevW, animate: true });

    if (data.game_over) { gameActive = false; showGameOver(data.winner); }
  } catch (_) {
    setHint("AI move failed — your turn");
  }
}

// ══════════════════════════════════════════════════════════════
// 18. INPUT HANDLING
// ══════════════════════════════════════════════════════════════
function _hitTest(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  const px = (clientX - rect.left) * (BOARD_W / rect.width);
  const py = (clientY - rect.top) * (BOARD_H / rect.height);
  let best = null, minD = Infinity;
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < ROW_COUNTS[r]; c++) {
      const { x, y } = cellPos(r, c);
      const d = Math.hypot(px - x, py - y);
      if (d < minD) { minD = d; best = { row: r, col: c }; }
    }
  }
  return (best && minD <= R + 10) ? best : null;
}

// Hover — compare row/col directly instead of JSON.stringify
canvas.addEventListener("mousemove", (e) => {
  if (isLoading || !gameActive) return;
  const cell = _hitTest(e.clientX, e.clientY);
  const prev = hoverCell;
  hoverCell = cell;
  const changed = !prev !== !cell
    || (prev && cell && (prev.row !== cell.row || prev.col !== cell.col));
  if (changed) render();
});

canvas.addEventListener("mouseleave", () => {
  hoverCell = null;
  render();
});

canvas.addEventListener("click", async (e) => {
  if (isLoading || !gameActive || gameState.turn !== "player") return;

  const cell = _hitTest(e.clientX, e.clientY);
  if (!cell) return;

  const { row, col } = cell;
  const piece = gameState.board[row]?.[col];

  // deselect
  if (_isInGroup(row, col)) {
    selectedGroup = selectedGroup.filter(g => !(g.row === row && g.col === col));
    SFX.deselect();
    computeHintCells();
    render();
    return;
  }

  // select own marble
  if ((piece === "W" || piece === "WK") && selectedGroup.length < 3) {
    selectedGroup.push({ row, col });
    SFX.select();
    computeHintCells();
    setHint(
      selectedGroup.length === 1
        ? "Select more marbles or click a highlighted destination"
        : "Click a highlighted destination to move"
    );
    render();
    return;
  }

  // send move
  if (selectedGroup.length > 0) {
    const group = [...selectedGroup];
    selectedGroup = [];
    hintSet.clear();
    render();
    await sendMove(group, { row, col });
    return;
  }

  // clicked empty/opponent with nothing selected
  if (piece !== "W") triggerInvalidFlash();
});

// ══════════════════════════════════════════════════════════════
// 19. RESPONSIVE SCALING
// ══════════════════════════════════════════════════════════════
function scaleGame() {
  const inner = document.getElementById("game-inner");
  if (!inner) return;
  const panelW = window.innerWidth > 820 ? 220 : 0;
  const availW = window.innerWidth - panelW - 24;
  const availH = window.innerHeight - 24;
  const scale = Math.min(availW / (BOARD_W + 20), availH / (BOARD_H + 280), 1);
  inner.style.transform = `scale(${scale})`;
}

window.addEventListener("resize", () => { scaleGame(); render(); });

// ══════════════════════════════════════════════════════════════
// 20. INIT
// ══════════════════════════════════════════════════════════════
function initGame() {
  scaleGame();
  _renderTray("tray-black", 0, "black", 6);
  _renderTray("tray-white", 0, "white", 6);
  render();
  startGame();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initGame);
} else {
  initGame();
}
