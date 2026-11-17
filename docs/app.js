/**
 * HASANINEJAD — mission attendance tracker (offline PWA).
 *
 * Storage: localStorage, one JSON array under a versioned key. The dataset is
 * a handful of rows per day, so this stays far below any quota and survives
 * app restarts, reboots and offline use.
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'hasaninejad.missions.v1';
  const HISTORY_LIMIT = 50;

  const els = {
    today: document.getElementById('todayText'),
    status: document.getElementById('statusText'),
    start: document.getElementById('startBtn'),
    finish: document.getElementById('finishBtn'),
    location: document.getElementById('locationInput'),
    details: document.getElementById('detailsInput'),
    quick: document.getElementById('quickBtn'),
    exportBtn: document.getElementById('exportBtn'),
    history: document.getElementById('historyList'),
    historyEmpty: document.getElementById('historyEmpty'),
    toast: document.getElementById('toast'),
    dialog: document.getElementById('quickDialog'),
    quickForm: document.getElementById('quickForm'),
    quickLocation: document.getElementById('quickLocation'),
    quickDetails: document.getElementById('quickDetails'),
    quickSave: document.getElementById('quickSave'),
    quickCancel: document.getElementById('quickCancel'),
    install: document.getElementById('installBtn'),
  };

  let missions = load();
  let toastTimer = null;
  let installPrompt = null;

  // ------------------------------------------------------------------ storage
  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      console.warn('خواندن داده‌ها ناموفق بود', err);
      return [];
    }
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(missions));
      return true;
    } catch (err) {
      console.error('ذخیره ناموفق بود', err);
      toast('ذخیره روی این گوشی ممکن نشد.');
      return false;
    }
  }

  function nextId() {
    return missions.reduce((max, m) => Math.max(max, m.id || 0), 0) + 1;
  }

  function activeMission() {
    for (let i = missions.length - 1; i >= 0; i -= 1) {
      if (missions[i].status === 'active') return missions[i];
    }
    return null;
  }

  // --------------------------------------------------------------------- time
  function nowIso() {
    const d = new Date();
    const pad = (n) => (n < 10 ? '0' + n : String(n));
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
      + `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  function timeOf(iso) {
    if (!iso) return '—';
    return Jalali.faDigits(iso.slice(11, 16));
  }

  function minutesBetween(startIso, endIso) {
    const start = new Date(startIso);
    const end = new Date(endIso);
    const diff = Math.floor((end - start) / 60000);
    return Number.isFinite(diff) ? Math.max(0, diff) : 0;
  }

  function durationLabel(minutes) {
    const total = Number(minutes) || 0;
    const h = Math.floor(total / 60);
    const m = total % 60;
    if (h && m) return `${Jalali.faDigits(h)} ساعت و ${Jalali.faDigits(m)} دقیقه`;
    if (h) return `${Jalali.faDigits(h)} ساعت`;
    return `${Jalali.faDigits(m)} دقیقه`;
  }

  // --------------------------------------------------------------------- view
  function refreshClock() {
    const now = new Date();
    els.today.textContent = `${Jalali.humanDate(now)} — ساعت ${Jalali.timeString(now)}`;
  }

  function refresh() {
    refreshClock();

    const active = activeMission();
    els.finish.disabled = !active;
    els.start.disabled = Boolean(active);

    if (active) {
      els.status.textContent = `مأموریت باز از ساعت ${timeOf(active.startIso)}`
        + ` در تاریخ ${active.startJalali}؛ هنوز پایان ثبت نشده است.`;
      els.status.classList.add('is-active');
    } else {
      els.status.textContent = 'هنوز مأموریتی در جریان نیست.';
      els.status.classList.remove('is-active');
    }

    renderHistory();
  }

  function renderHistory() {
    const done = missions
      .filter((m) => m.status === 'done')
      .sort((a, b) => (b.id || 0) - (a.id || 0))
      .slice(0, HISTORY_LIMIT);

    els.history.textContent = '';
    els.historyEmpty.hidden = done.length > 0;

    done.forEach((m) => {
      els.history.appendChild(historyItem(m));
    });
  }

  function historyItem(mission) {
    const li = document.createElement('li');
    li.className = 'history-item';

    const head = document.createElement('div');
    head.className = 'history-head';

    const date = document.createElement('span');
    date.textContent = mission.startJalali || '—';

    const duration = document.createElement('span');
    duration.className = 'history-duration';
    duration.textContent = durationLabel(mission.durationMinutes);

    head.append(date, duration);

    const times = document.createElement('div');
    times.className = 'history-row';
    times.innerHTML = `<span>خروج: <b>${timeOf(mission.startIso)}</b></span>`
      + `<span>بازگشت: <b>${timeOf(mission.endIso)}</b></span>`;

    li.append(head, times);

    if (mission.location) {
      const loc = document.createElement('div');
      loc.className = 'history-row';
      loc.innerHTML = `<span>مکان: <b></b></span>`;
      loc.querySelector('b').textContent = mission.location;
      li.append(loc);
    }

    if (mission.details) {
      const details = document.createElement('p');
      details.className = 'history-details';
      details.textContent = mission.details;
      li.append(details);
    }

    return li;
  }

  function toast(message) {
    els.toast.textContent = message;
    els.toast.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => els.toast.classList.remove('is-visible'), 3200);
  }

  // ------------------------------------------------------------------ actions
  function startMission() {
    if (activeMission()) {
      toast('ابتدا مأموریت فعلی را به پایان برسان.');
      return;
    }
    const now = new Date();
    missions.push({
      id: nextId(),
      startIso: nowIso(),
      endIso: null,
      startJalali: Jalali.dateString(now),
      endJalali: null,
      location: els.location.value.trim(),
      details: els.details.value.trim(),
      durationMinutes: null,
      status: 'active',
    });
    if (!save()) return;

    els.location.value = '';
    els.details.value = '';
    refresh();
    toast('زمان خروج ثبت شد؛ مأموریت تا ثبت بازگشت محفوظ می‌ماند.');
  }

  function finishMission() {
    const active = activeMission();
    if (!active) {
      toast('ابتدا شروع مأموریت را ثبت کن.');
      return;
    }
    const now = new Date();
    const endIso = nowIso();

    active.endIso = endIso;
    active.endJalali = Jalali.dateString(now);
    active.durationMinutes = minutesBetween(active.startIso, endIso);
    active.status = 'done';

    const typedLocation = els.location.value.trim();
    const typedDetails = els.details.value.trim();
    if (typedLocation) active.location = typedLocation;
    if (typedDetails) active.details = typedDetails;

    if (!save()) return;

    els.location.value = '';
    els.details.value = '';
    refresh();
    toast('مأموریت تکمیل شد و در سوابق ذخیره شد.');
  }

  function openQuickDialog() {
    els.quickLocation.value = els.location.value;
    els.quickDetails.value = '';
    if (typeof els.dialog.showModal === 'function') {
      els.dialog.showModal();
    } else {
      els.dialog.setAttribute('open', '');
    }
    els.quickLocation.focus();
  }

  function saveQuickReport(event) {
    event.preventDefault();
    const now = new Date();
    const iso = nowIso();

    missions.push({
      id: nextId(),
      startIso: iso,
      endIso: iso,
      startJalali: Jalali.dateString(now),
      endJalali: Jalali.dateString(now),
      location: els.quickLocation.value.trim(),
      details: els.quickDetails.value.trim(),
      durationMinutes: 0,
      status: 'done',
    });

    if (!save()) return;
    els.dialog.close();
    refresh();
    toast('گزارش سریع ذخیره شد.');
  }

  // --------------------------------------------------------------------- CSV
  const CSV_HEADERS = [
    'تاریخ خروج', 'ساعت خروج', 'تاریخ بازگشت', 'ساعت بازگشت',
    'مدت (دقیقه)', 'مکان', 'توضیحات', 'وضعیت',
  ];

  function csvCell(value) {
    const text = value === null || value === undefined ? '' : String(value);
    return `"${text.replace(/"/g, '""')}"`;
  }

  function buildCsv() {
    const rows = [CSV_HEADERS.map(csvCell).join(',')];
    missions
      .slice()
      .sort((a, b) => (a.id || 0) - (b.id || 0))
      .forEach((m) => {
        rows.push([
          m.startJalali,
          m.startIso ? m.startIso.slice(11, 16) : '',
          m.endJalali || '',
          m.endIso ? m.endIso.slice(11, 16) : '',
          m.durationMinutes === null || m.durationMinutes === undefined ? '' : m.durationMinutes,
          m.location || '',
          m.details || '',
          m.status === 'done' ? 'ثبت نهایی' : 'باز',
        ].map(csvCell).join(','));
      });
    // BOM keeps Excel from mangling Persian text.
    return '\uFEFF' + rows.join('\r\n') + '\r\n';
  }

  async function exportCsv() {
    if (!missions.length) {
      toast('هنوز اطلاعاتی برای خروجی وجود ندارد.');
      return;
    }

    const csv = buildCsv();
    const fileName = `HASANINEJAD-report-${Jalali.todayString().replace(/\//g, '-')}.csv`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });

    // Prefer the native share sheet when the browser can share files.
    const file = new File([blob], fileName, { type: 'text/csv' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({
          files: [file],
          title: 'گزارش مأموریت‌ها',
          text: 'خروجی CSV مأموریت‌ها',
        });
        return;
      } catch (err) {
        if (err && err.name === 'AbortError') return;
      }
    }

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    toast('فایل CSV ساخته شد و دانلود می‌شود.');
  }

  // ------------------------------------------------------------------- events
  els.start.addEventListener('click', startMission);
  els.finish.addEventListener('click', finishMission);
  els.quick.addEventListener('click', openQuickDialog);
  els.exportBtn.addEventListener('click', exportCsv);
  els.quickForm.addEventListener('submit', saveQuickReport);

  els.quickCancel.addEventListener('click', () => els.dialog.close());

  els.location.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      els.details.focus();
    }
  });

  // -------------------------------------------------------------- PWA install
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    installPrompt = event;
    els.install.hidden = false;
  });

  els.install.addEventListener('click', async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    els.install.hidden = true;
  });

  window.addEventListener('appinstalled', () => {
    els.install.hidden = true;
    toast('اپ روی صفحهٔ اصلی نصب شد.');
  });

  // ------------------------------------------------------------ service worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js').catch((err) => {
        console.warn('ثبت service worker ناموفق بود', err);
      });
    });
  }

  // ---------------------------------------------------------------- bootstrap
  refresh();
  setInterval(refreshClock, 30000);

  // Recompute on tab focus so a mission started hours ago shows the new date.
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refresh();
  });
})();
