/* TAP-DEV Phase 2 — Frontend JavaScript */
(function () {
  'use strict';

  /* ── THEME ──────────────────────────────────────────────────────── */
  const savedTheme = localStorage.getItem('tapdev-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);

  window.toggleTheme = function () {
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('tapdev-theme', next);
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.innerHTML = next === 'dark' ? '☀' : '🌙';
  };

  /* ── DROP ZONE ──────────────────────────────────────────────────── */
  function initDropZone() {
    const zone = document.getElementById('drop-zone');
    const input = document.getElementById('id_file');
    const preview = document.getElementById('dz-preview');
    if (!zone || !input) return;

    ['dragenter', 'dragover'].forEach(ev =>
      zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add('drag-over'); })
    );
    ['dragleave', 'drop'].forEach(ev =>
      zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove('drag-over'); })
    );
    zone.addEventListener('drop', e => { if (e.dataTransfer.files[0]) showPreview(e.dataTransfer.files[0]); input.files = e.dataTransfer.files; });
    input.addEventListener('change', () => { if (input.files[0]) showPreview(input.files[0]); });

    function showPreview(f) {
      if (!preview) return;
      preview.style.display = 'block';
      const kb = f.size < 1024 * 1024 ? (f.size / 1024).toFixed(1) + ' KB' : (f.size / 1048576).toFixed(1) + ' MB';
      preview.textContent = `${f.name}  (${kb})`;
    }
  }

  /* ── FLASH AUTO-DISMISS ─────────────────────────────────────────── */
  function initFlash() {
    document.querySelectorAll('.flash').forEach(el => {
      setTimeout(() => {
        el.style.transition = 'opacity .4s, transform .3s';
        el.style.opacity = '0';
        el.style.transform = 'translateX(10px)';
        setTimeout(() => el.remove(), 400);
      }, 5000);
    });
  }

  /* ── HASH COPY ──────────────────────────────────────────────────── */
  function initHashCopy() {
    document.querySelectorAll('.int-hash, .tl-hash, .hash-chip').forEach(el => {
      el.style.cursor = 'pointer';
      el.title = 'Click to copy';
      el.addEventListener('click', () => {
        navigator.clipboard.writeText(el.textContent.trim()).then(() => {
          const orig = el.textContent;
          el.textContent = '✓ Copied';
          el.style.color = 'var(--green)';
          setTimeout(() => { el.textContent = orig; el.style.color = ''; }, 1500);
        });
      });
    });
  }

  /* ── TIMELINE STAGGER ───────────────────────────────────────────── */
  function initTimeline() {
    document.querySelectorAll('.tl-event').forEach((el, i) => {
      el.style.animationDelay = `${i * 60}ms`;
    });
  }

  /* ── TRUST BAR ANIMATION ────────────────────────────────────────── */
  function initBars() {
    document.querySelectorAll('.stat-fill, .mini-fill, .tb-fill').forEach(el => {
      const target = el.style.width;
      el.style.width = '0%';
      requestAnimationFrame(() => setTimeout(() => { el.style.width = target; }, 80));
    });
  }

  /* ── FAQ ACCORDION ──────────────────────────────────────────────── */
  function initFAQ() {
    document.querySelectorAll('.faq-q').forEach(btn => {
      btn.addEventListener('click', () => {
        const item = btn.closest('.faq-item');
        const isOpen = item.classList.contains('open');
        document.querySelectorAll('.faq-item.open').forEach(o => o.classList.remove('open'));
        if (!isOpen) item.classList.add('open');
      });
    });
  }

  /* ── MOBILE SIDEBAR ─────────────────────────────────────────────── */
  function initMobileSidebar() {
    const toggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (!toggle || !sidebar) return;
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    document.addEventListener('click', e => {
      if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== toggle)
        sidebar.classList.remove('open');
    });
  }

  /* ── SUBMIT LOADING ─────────────────────────────────────────────── */
  function initSubmitBtn() {
    const form = document.getElementById('upload-form');
    const btn  = document.getElementById('submit-btn');
    if (!form || !btn) return;
    form.addEventListener('submit', () => {
      btn.disabled = true;
      btn.innerHTML = '<span style="display:inline-block;animation:spin .8s linear infinite">↻</span> Processing…';
    });
  }

  /* ── COUNTER ANIMATION ──────────────────────────────────────────── */
  function initCounters() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const target = parseInt(el.dataset.count, 10);
        if (isNaN(target)) return;
        let start = 0;
        const duration = 1200;
        const step = target / (duration / 16);
        const timer = setInterval(() => {
          start = Math.min(start + step, target);
          el.textContent = Math.floor(start).toLocaleString();
          if (start >= target) clearInterval(timer);
        }, 16);
        observer.unobserve(el);
      });
    }, { threshold: 0.3 });
    document.querySelectorAll('[data-count]').forEach(el => observer.observe(el));
  }

  /* ── NAV ACTIVE ─────────────────────────────────────────────────── */
  function initNavActive() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
      if (link.getAttribute('href') && path.startsWith(link.getAttribute('href')) && link.getAttribute('href') !== '/') {
        link.classList.add('active');
      }
    });
    document.querySelectorAll('.navbar-link').forEach(link => {
      if (link.getAttribute('href') === path) link.classList.add('active');
    });
  }

  /* ── CHARTS (Chart.js) ──────────────────────────────────────────── */
  window.initCharts = function (configs) {
    if (typeof Chart === 'undefined') return;
    const style = getComputedStyle(document.documentElement);
    const accent = '#00d4ff';
    const green  = '#10b981';
    const amber  = '#f59e0b';
    const red    = '#ef4444';
    const text2  = style.getPropertyValue('--text-2').trim() || '#8fafc8';
    const border = style.getPropertyValue('--border').trim() || '#1a2535';

    Chart.defaults.color = text2;
    Chart.defaults.borderColor = border;
    Chart.defaults.font.family = "'DM Mono', monospace";
    Chart.defaults.font.size   = 11;

    configs.forEach(({ id, type, labels, datasets, options }) => {
      const canvas = document.getElementById(id);
      if (!canvas) return;
      new Chart(canvas, {
        type,
        data: { labels, datasets: datasets.map(ds => ({ ...ds, borderWidth: ds.borderWidth || 2 })) },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: datasets.length > 1 }, tooltip: { mode: 'index', intersect: false } },
          scales: type !== 'doughnut' ? {
            x: { grid: { color: border }, ticks: { color: text2 } },
            y: { grid: { color: border }, ticks: { color: text2 }, beginAtZero: true },
          } : {},
          ...options,
        },
      });
    });
  };

  /* ── INIT ───────────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    initDropZone();
    initFlash();
    initHashCopy();
    initTimeline();
    initBars();
    initFAQ();
    initMobileSidebar();
    initSubmitBtn();
    initCounters();
    initNavActive();

    // Theme toggle icon
    const th = document.getElementById('theme-toggle');
    if (th) th.textContent = (localStorage.getItem('tapdev-theme') || 'dark') === 'dark' ? '☀' : '🌙';
  });

  // Spin keyframes
  const style = document.createElement('style');
  style.textContent = '@keyframes spin{to{transform:rotate(360deg)}}';
  document.head.appendChild(style);
})();
