"""Zero-dependency motion runtime for generated sites.

Features are feature-detected from the DOM: no elements -> no work.
Everything is gated behind prefers-reduced-motion, and every animation
is transform/opacity based so it stays off the layout thread.
"""
from __future__ import annotations

MOTION_JS = r"""'use strict';
(function () {
  var doc = document.documentElement;
  var reduce = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  doc.classList.remove('no-js');
  var reveal = Array.prototype.slice.call(
    document.querySelectorAll('[data-reveal]'));

  if (reduce) {
    doc.classList.add('reduced-motion');
    reveal.forEach(function (el) { el.classList.add('in'); });
    return;
  }
  doc.classList.add('motion');

  /* scroll reveal */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        var delay = el.getAttribute('data-delay') || '0';
        el.style.transitionDelay = delay + 'ms';
        el.classList.add('in');
        io.unobserve(el);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    reveal.forEach(function (el) { io.observe(el); });
  } else {
    reveal.forEach(function (el) { el.classList.add('in'); });
  }

  var fine = window.matchMedia && window.matchMedia('(pointer: fine)').matches;

  /* pointer tilt */
  if (fine) {
    document.querySelectorAll('[data-tilt]').forEach(function (el) {
      var max = parseFloat(el.getAttribute('data-tilt')) || 8;
      el.addEventListener('pointermove', function (ev) {
        var r = el.getBoundingClientRect();
        var px = (ev.clientX - r.left) / r.width - 0.5;
        var py = (ev.clientY - r.top) / r.height - 0.5;
        el.style.transform = 'perspective(900px) rotateY(' +
          (px * max).toFixed(2) + 'deg) rotateX(' +
          (-py * max).toFixed(2) + 'deg)';
        el.style.setProperty('--mx', ((px + 0.5) * 100).toFixed(1) + '%');
        el.style.setProperty('--my', ((py + 0.5) * 100).toFixed(1) + '%');
      });
      el.addEventListener('pointerleave', function () {
        el.style.transform = '';
      });
    });

    /* magnetic buttons */
    document.querySelectorAll('[data-magnet]').forEach(function (el) {
      el.addEventListener('pointermove', function (ev) {
        var r = el.getBoundingClientRect();
        var x = (ev.clientX - r.left - r.width / 2) * 0.18;
        var y = (ev.clientY - r.top - r.height / 2) * 0.18;
        el.style.transform = 'translate(' + x.toFixed(1) + 'px,' +
          y.toFixed(1) + 'px)';
      });
      el.addEventListener('pointerleave', function () {
        el.style.transform = '';
      });
    });

    /* cursor glow */
    var glow = document.querySelector('.cursor-glow');
    if (glow) {
      document.addEventListener('pointermove', function (ev) {
        glow.style.transform = 'translate3d(' + ev.clientX + 'px,' +
          ev.clientY + 'px,0)';
        glow.classList.add('on');
      }, { passive: true });
      document.addEventListener('pointerleave', function () {
        glow.classList.remove('on');
      });
    }
  }

  /* number counters */
  function count(el) {
    var target = parseInt(el.getAttribute('data-count'), 10) || 0;
    var dur = 1100;
    var start = null;
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min(1, (ts - start) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased)
        .toLocaleString('ru-RU');
      if (p < 1) window.requestAnimationFrame(step);
    }
    window.requestAnimationFrame(step);
  }
  var counters = Array.prototype.slice.call(
    document.querySelectorAll('[data-count]'));
  if (counters.length && 'IntersectionObserver' in window) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        count(entry.target);
        cio.unobserve(entry.target);
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { cio.observe(el); });
  } else {
    counters.forEach(count);
  }

  /* parallax */
  var parallax = Array.prototype.slice.call(
    document.querySelectorAll('[data-parallax]'));
  if (parallax.length) {
    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        var vh = window.innerHeight;
        parallax.forEach(function (el) {
          var r = el.getBoundingClientRect();
          var speed = parseFloat(el.getAttribute('data-parallax')) || 0.08;
          var off = (r.top + r.height / 2 - vh / 2) * speed;
          el.style.setProperty('--py', off.toFixed(1) + 'px');
        });
        ticking = false;
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* particles */
  var canvas = document.querySelector('canvas[data-particles]');
  if (canvas && canvas.getContext) {
    var ctx = canvas.getContext('2d');
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var points = [];
    var accent = getComputedStyle(doc).getPropertyValue('--accent').trim() ||
      '#5eead4';
    function rgb(hex) {
      var h = hex.replace('#', '');
      if (h.length === 3) {
        h = h.split('').map(function (c) { return c + c; }).join('');
      }
      var n = parseInt(h, 16) || 0;
      return [n >> 16 & 255, n >> 8 & 255, n & 255];
    }
    var tint = rgb(accent);
    function size() {
      canvas.width = Math.max(1, window.innerWidth * dpr);
      canvas.height = Math.max(1, window.innerHeight * dpr);
    }
    function seed() {
      points = [];
      var n = Math.min(70, Math.max(24, Math.round(window.innerWidth / 24)));
      for (var i = 0; i < n; i++) {
        points.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          vx: (Math.random() - 0.5) * 0.18 * dpr,
          vy: (Math.random() - 0.5) * 0.18 * dpr,
          r: (Math.random() * 1.6 + 0.6) * dpr
        });
      }
    }
    size();
    seed();
    window.addEventListener('resize', function () { size(); seed(); });
    var raf = 0;
    function loop() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var i = 0; i < points.length; i++) {
        var p = points[i];
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(' + tint[0] + ',' + tint[1] + ',' +
          tint[2] + ',0.42)';
        ctx.fill();
      }
      raf = window.requestAnimationFrame(loop);
    }
    loop();
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        window.cancelAnimationFrame(raf);
      } else {
        loop();
      }
    });
  }
})();
"""
