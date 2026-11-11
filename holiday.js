// Holiday theme: string lights in the header + falling snow behind the page.
// Self-contained — remove this file's <script> tag (and the #snow / #lights
// elements in index.html) to switch the decorations off after the season.

(function () {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- String lights ------------------------------------------------------
  const lights = document.getElementById('lights');
  const COLORS = ['red', 'gold', 'green', 'white'];

  function buildLights() {
    if (!lights) return;
    const count = Math.max(8, Math.round(lights.clientWidth / 44));
    if (lights.childElementCount === count) return;
    lights.innerHTML = '';
    for (let i = 0; i < count; i++) {
      const bulb = document.createElement('span');
      bulb.className = 'bulb ' + COLORS[i % COLORS.length];
      // bulbs hang lower in the middle of each scallop of wire
      bulb.style.setProperty('--drop', (10 + Math.abs(Math.sin(i * 1.1)) * 8).toFixed(1) + 'px');
      bulb.style.setProperty('--delay', (-Math.random() * 3).toFixed(2) + 's');
      bulb.style.setProperty('--dur', (1.6 + Math.random() * 1.8).toFixed(2) + 's');
      bulb.style.transform = `rotate(${(Math.random() * 16 - 8).toFixed(1)}deg)`;
      lights.appendChild(bulb);
    }
  }

  // ---- Falling snow -------------------------------------------------------
  const canvas = document.getElementById('snow');
  const ctx = canvas && canvas.getContext('2d');
  let flakes = [];
  let width = 0, height = 0, dpr = 1;

  function makeFlake(randomY) {
    const depth = Math.random(); // 0 = far, 1 = near
    return {
      x: Math.random() * width,
      y: randomY ? Math.random() * height : -10,
      r: 1 + depth * 2.6,
      speed: 0.25 + depth * 0.9,
      drift: Math.random() * Math.PI * 2,
      sway: 0.3 + Math.random() * 0.6,
      alpha: 0.5 + depth * 0.45
    };
  }

  function resize() {
    if (!canvas) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#ffffff'; // resizing the canvas resets context state

    const target = Math.round(Math.min(160, (width * height) / 7000) * (reduceMotion ? 0.5 : 1));
    while (flakes.length < target) flakes.push(makeFlake(true));
    flakes.length = target;
    if (reduceMotion) draw(); // static snowfall
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);
    for (const f of flakes) {
      ctx.globalAlpha = f.alpha;
      ctx.beginPath();
      ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  let wind = 0, last = 0;
  function tick(now) {
    const dt = Math.min(3, last ? (now - last) / 16.67 : 1);
    last = now;
    wind = Math.sin(now / 6000) * 0.35;
    for (const f of flakes) {
      f.drift += 0.01 * dt;
      f.y += f.speed * dt;
      f.x += (Math.sin(f.drift) * f.sway + wind) * dt * 0.6;
      if (f.y > height + 6) Object.assign(f, makeFlake(false));
      if (f.x > width + 6) f.x = -6;
      if (f.x < -6) f.x = width + 6;
    }
    draw();
    requestAnimationFrame(tick);
  }

  if (ctx) {
    resize();
    if (!reduceMotion) requestAnimationFrame(tick);
  }

  buildLights();

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      buildLights();
      if (ctx) resize();
    }, 150);
  });
})();
