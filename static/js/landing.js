(function () {
  const navbar = document.querySelector("[data-navbar]");
  const cursor = document.querySelector(".cursor-glow");
  const backdrop = document.querySelector(".video-backdrop");
  const video = document.getElementById("vault-video");
  const canvas = document.getElementById("network-canvas");
  const ctx = canvas ? canvas.getContext("2d") : null;

  let width = 0;
  let height = 0;
  let nodes = [];
  let rafId = null;

  function onScroll() {
    const y = window.scrollY || 0;
    if (navbar) navbar.classList.toggle("is-scrolled", y > 12);
    if (backdrop) backdrop.style.setProperty("--float-y", `${Math.sin(y * 0.006) * 10}px`);
  }

  function onPointerMove(event) {
    if (!cursor) return;
    cursor.animate(
      { transform: `translate3d(${event.clientX - 208}px, ${event.clientY - 208}px, 0)` },
      { duration: 550, fill: "forwards", easing: "cubic-bezier(.2,.8,.2,1)" }
    );
  }

  function resizeCanvas() {
    if (!canvas || !ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = Math.max(window.innerHeight, 720);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    nodes = Array.from({ length: Math.max(42, Math.floor(width / 24)) }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.28,
      vy: (Math.random() - 0.5) * 0.22,
      r: Math.random() * 1.8 + 0.8,
    }));
  }

  function drawNetwork(time) {
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);

    const gradient = ctx.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, "rgba(74, 214, 255, 0.42)");
    gradient.addColorStop(1, "rgba(151, 92, 255, 0.34)");

    nodes.forEach((node, index) => {
      node.x += node.vx + Math.sin(time * 0.00035 + index) * 0.02;
      node.y += node.vy + Math.cos(time * 0.00028 + index) * 0.02;

      if (node.x < -20) node.x = width + 20;
      if (node.x > width + 20) node.x = -20;
      if (node.y < -20) node.y = height + 20;
      if (node.y > height + 20) node.y = -20;

      for (let j = index + 1; j < nodes.length; j += 1) {
        const other = nodes[j];
        const dx = node.x - other.x;
        const dy = node.y - other.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 145) {
          ctx.strokeStyle = `rgba(93, 214, 255, ${0.18 * (1 - distance / 145)})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(node.x, node.y);
          ctx.lineTo(other.x, other.y);
          ctx.stroke();
        }
      }

      ctx.fillStyle = gradient;
      ctx.shadowColor = "rgba(89, 218, 255, .8)";
      ctx.shadowBlur = 16;
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    });

    rafId = requestAnimationFrame(drawNetwork);
  }

  function setupVideoLoop() {
    if (!video) return;
    const sourceUrl = video.dataset.src;
    if (!sourceUrl) return;

    fetch(sourceUrl, { method: "HEAD" })
      .then((response) => {
        if (!response.ok) return;
        const source = document.createElement("source");
        source.src = sourceUrl;
        source.type = "video/mp4";
        video.appendChild(source);
        video.load();
      })
      .catch(() => {});

    let fadingOut = false;
    video.addEventListener("canplay", () => {
      video.classList.add("is-visible");
      video.play().catch(() => {});
    });

    function tick() {
      if (video.duration && video.currentTime >= video.duration - 0.5 && !fadingOut) {
        fadingOut = true;
        video.classList.remove("is-visible");
      }

      if (video.duration && video.currentTime >= video.duration - 0.04) {
        video.currentTime = 0;
        fadingOut = false;
        requestAnimationFrame(() => video.classList.add("is-visible"));
      }

      requestAnimationFrame(tick);
    }

    video.addEventListener("loadedmetadata", () => requestAnimationFrame(tick));
    video.addEventListener("error", () => video.classList.remove("is-visible"));
    video.play().catch(() => {});
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("pointermove", onPointerMove, { passive: true });
  window.addEventListener("resize", resizeCanvas);

  resizeCanvas();
  drawNetwork(0);
  setupVideoLoop();
  onScroll();

  window.addEventListener("beforeunload", () => {
    if (rafId) cancelAnimationFrame(rafId);
  });
})();
