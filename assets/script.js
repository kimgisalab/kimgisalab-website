// ===== Mobile nav =====
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const mobile = document.querySelector('.nav-mobile');
  if (toggle && mobile) {
    toggle.addEventListener('click', () => {
      mobile.classList.toggle('open');
      toggle.setAttribute('aria-expanded', mobile.classList.contains('open'));
    });
    mobile.querySelectorAll('a').forEach(a => a.addEventListener('click', () => mobile.classList.remove('open')));
  }

  // ===== Scroll reveal =====
  const revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach((el, i) => {
      el.style.transitionDelay = (i % 6) * 60 + 'ms';
      io.observe(el);
    });
  } else {
    revealEls.forEach(el => el.classList.add('in'));
  }

  // ===== Counter animation =====
  const counters = document.querySelectorAll('[data-count]');
  const animateCount = (el) => {
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || '';
    const dur = 1400;
    const start = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = Math.round(target * eased);
      el.textContent = val.toLocaleString('ko-KR') + suffix;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  if (counters.length && 'IntersectionObserver' in window) {
    const cio = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          animateCount(e.target);
          cio.unobserve(e.target);
        }
      });
    }, { threshold: 0.4 });
    counters.forEach(c => cio.observe(c));
  }

  // ===== Portfolio filter =====
  const filterBtns = document.querySelectorAll('.pf-filter button');
  const pfCards = document.querySelectorAll('.pf-card');
  if (filterBtns.length) {
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cat = btn.dataset.cat;
        pfCards.forEach(card => {
          const show = cat === 'all' || card.dataset.cat === cat;
          card.style.display = show ? '' : 'none';
        });
      });
    });
  }

  // ===== News pagination =====
  const pagination = document.querySelector('.pagination');
  if (pagination) {
    const newsItems = document.querySelectorAll('.news-item[data-page]');
    const pageBtns = pagination.querySelectorAll('.page-btn');
    const showPage = (page) => {
      newsItems.forEach(item => {
        item.style.display = (item.dataset.page === String(page)) ? '' : 'none';
      });
      pageBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.page === String(page));
      });
    };
    pageBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        showPage(btn.dataset.page);
        window.scrollTo({ top: pagination.closest('section').offsetTop - 90, behavior: 'smooth' });
      });
    });
    showPage(1);
  }

  // ===== Contact form -> Google Apps Script (자동 전송 + PDF 첨부) =====
  const form = document.querySelector('#ir-form');
  if (form) {
    const fileToBase64 = (file) => new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const status = document.querySelector('.form-status');
      const btn = form.querySelector('button[type="submit"]');
      const btnLabel = btn ? btn.textContent : '';
      const endpoint = form.dataset.endpoint;
      const fileInput = form.querySelector('input[type="file"][name="pitchFile"]');
      const file = fileInput && fileInput.files && fileInput.files[0];
      const fd = new FormData(form);
      fd.delete('pitchFile');

      if (btn) { btn.disabled = true; btn.textContent = '전송 중...'; }
      if (status) { status.classList.remove('show', 'error'); }

      try {
        if (!endpoint || endpoint.indexOf('YOUR_DEPLOYMENT_ID') !== -1) {
          throw new Error('endpoint not configured');
        }
        if (file) {
          const base64 = await fileToBase64(file);
          fd.append('pitchFileData', base64);
          fd.append('pitchFileName', file.name);
          fd.append('pitchFileType', file.type || 'application/pdf');
        }
        const res = await fetch(endpoint, { method: 'POST', body: fd });
        const data = await res.json();
        if (data && data.ok) {
          form.reset();
          if (status) {
            status.textContent = '문의가 정상적으로 접수되었습니다. 검토 후 2주 이내에 회신드리겠습니다.';
            status.classList.add('show');
          }
        } else {
          throw new Error((data && data.error) || 'submit failed');
        }
      } catch (err) {
        if (status) {
          status.textContent = '전송에 실패했습니다. IR@kimgisacompany.com으로 직접 메일 부탁드립니다.';
          status.classList.add('show', 'error');
        }
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = btnLabel; }
      }
    });
  }

  // ===== Active nav link =====
  const path = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a, .nav-mobile a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path || (path === '' && href === 'index.html')) {
      a.classList.add('active');
    }
  });
});
