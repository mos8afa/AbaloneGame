// ============================================================
// HOME PAGE — animated background canvas
// ============================================================
(function () {
  const canvas = document.getElementById("home-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  // Floating marble particles
  const particles = Array.from({ length: 28 }, () => ({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    r: 6 + Math.random() * 14,
    vx: (Math.random() - 0.5) * 0.4,
    vy: (Math.random() - 0.5) * 0.4,
    white: Math.random() > 0.5,
  }));

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < -p.r) p.x = canvas.width + p.r;
      if (p.x > canvas.width + p.r) p.x = -p.r;
      if (p.y < -p.r) p.y = canvas.height + p.r;
      if (p.y > canvas.height + p.r) p.y = -p.r;

      const grad = ctx.createRadialGradient(
        p.x - p.r * 0.3, p.y - p.r * 0.3, p.r * 0.1,
        p.x, p.y, p.r
      );
      if (p.white) {
        grad.addColorStop(0, "rgba(255,255,255,0.9)");
        grad.addColorStop(1, "rgba(180,180,180,0.3)");
      } else {
        grad.addColorStop(0, "rgba(100,100,120,0.8)");
        grad.addColorStop(1, "rgba(20,20,30,0.2)");
      }
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }

  draw();

  // Scale home-inner to fit viewport
  const inner = document.getElementById("home-inner");
  function scaleInner() {
    if (!inner) return;
    const scaleX = window.innerWidth / (inner.offsetWidth + 80);
    const scaleY = window.innerHeight / (inner.offsetHeight + 80);
    const scale = Math.min(scaleX, scaleY, 1);
    inner.style.transform = `scale(${scale})`;
  }
  scaleInner();
  window.addEventListener("resize", scaleInner);
})();
