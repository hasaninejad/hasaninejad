/**
 * Jalali (Persian) calendar helpers.
 *
 * Port of the same algorithm used in main.py. The cumulative month table keeps
 * February at 28 days on purpose: the leap day is handled by `gy2`, and using
 * the real February length here adds a spurious day after February in leap
 * years (the bug this port exists to avoid).
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.Jalali = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const G_DAYS_IN_MONTH = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

  const FA_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

  const MONTH_NAMES = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
  ];

  const WEEKDAYS = ['یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه'];

  function toJalali(gy, gm, gd) {
    let jy;
    if (gy > 1600) {
      jy = 979;
      gy -= 1600;
    } else {
      jy = 0;
      gy -= 621;
    }
    const gy2 = gm > 2 ? gy + 1 : gy;
    let days = 365 * gy
      + Math.floor((gy2 + 3) / 4)
      - Math.floor((gy2 + 99) / 100)
      + Math.floor((gy2 + 399) / 400)
      - 80 + gd + G_DAYS_IN_MONTH[gm - 1];

    jy += 33 * Math.floor(days / 12053);
    days %= 12053;
    jy += 4 * Math.floor(days / 1461);
    days %= 1461;

    if (days > 365) {
      jy += Math.floor((days - 1) / 365);
      days = (days - 1) % 365;
    }

    let jm;
    let jd;
    if (days < 186) {
      jm = 1 + Math.floor(days / 31);
      jd = 1 + (days % 31);
    } else {
      jm = 7 + Math.floor((days - 186) / 30);
      jd = 1 + ((days - 186) % 30);
    }
    return [jy, jm, jd];
  }

  function pad2(n) {
    return n < 10 ? '0' + n : String(n);
  }

  function faDigits(value) {
    return String(value).replace(/\d/g, (d) => FA_DIGITS[Number(d)]);
  }

  /** 1405/08/26 — the stored, sortable form. */
  function dateString(date) {
    const [jy, jm, jd] = toJalali(date.getFullYear(), date.getMonth() + 1, date.getDate());
    return `${jy}/${pad2(jm)}/${pad2(jd)}`;
  }

  /** ۲۶ آبان ۱۴۰۵ */
  function longDate(date) {
    const [jy, jm, jd] = toJalali(date.getFullYear(), date.getMonth() + 1, date.getDate());
    return `${faDigits(jd)} ${MONTH_NAMES[jm - 1]} ${faDigits(jy)}`;
  }

  function weekday(date) {
    return WEEKDAYS[date.getDay()];
  }

  /** ۲۶ آبان ۱۴۰۵، شنبه */
  function humanDate(date) {
    return `${weekday(date)}، ${longDate(date)}`;
  }

  function timeString(date) {
    return faDigits(`${pad2(date.getHours())}:${pad2(date.getMinutes())}`);
  }

  function todayString() {
    return dateString(new Date());
  }

  return {
    toJalali,
    pad2,
    faDigits,
    dateString,
    longDate,
    humanDate,
    timeString,
    todayString,
    MONTH_NAMES,
    WEEKDAYS,
  };
});
