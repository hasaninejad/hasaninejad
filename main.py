# -*- coding: utf-8 -*-
"""HASANINEJAD - mission attendance tracker built with Kivy.

Single-file prototype:
  * SQLite storage inside the app's private directory
  * Jalali (Persian) dates
  * RTL Persian UI with arabic_reshaper + python-bidi
  * CSV export (UTF-8 BOM, opens in Excel)
"""
import csv
import os
import re
import sqlite3
from datetime import date, datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

APP_TITLE = 'HASANINEJAD'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, 'Vazirmatn-Regular.ttf')

# Persian/Arabic code points: a string containing one of these needs reshaping.
FA_RANGE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')
KV_TAG = re.compile(r'(\[[^\]]*\])')


def register_persian_font():
    """Use the bundled Persian TTF as Kivy's default family.

    Kivy's stock Roboto ships no Arabic glyphs, so every Persian label would
    render as empty boxes on Android. Overriding the default family keeps the
    KV file free of per-widget `font_name` lines.
    """
    if not os.path.exists(FONT_PATH):
        return False
    try:
        LabelBase.register(name='Roboto', fn_regular=FONT_PATH)
        return True
    except Exception:
        return False


HAS_PERSIAN_FONT = register_persian_font()


# --------------------------------------------------------------------------
# dates
# --------------------------------------------------------------------------
def gregorian_to_jalali(gy, gm, gd):
    """Gregorian -> Jalali (33-year cycle algorithm, jdf/Borkowski).

    The cumulative month table keeps February at 28 days on purpose: the leap
    day is accounted for by ``gy2``, so using the real February length here
    would add an extra day for every date after February in a leap year.
    """
    g_days_in_month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100
            + (gy2 + 399) // 400 - 80 + gd + g_days_in_month[gm - 1])
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_today():
    d = date.today()
    y, m, day = gregorian_to_jalali(d.year, d.month, d.day)
    return f'{y:04d}/{m:02d}/{day:02d}'


def fa_digits(s):
    return str(s).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))


# --------------------------------------------------------------------------
# RTL / shaping
# --------------------------------------------------------------------------
def rtl(s):
    """Reshape and reorder one Persian string for Kivy's non-shaping text engine."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(str(s)))
    except Exception:
        return str(s)


def _shape_segment(segment):
    """Shape Persian runs while leaving Kivy markup tags (`[b]`, `[font=..]`) intact."""
    if not FA_RANGE.search(segment):
        return segment
    parts = KV_TAG.split(segment)
    return ''.join(p if p.startswith('[') else rtl(p) for p in parts)


def shape_kv(kv_text):
    """Shape every Persian literal inside a KV source string.

    The KV file is loaded from a Python string, so the shaping can happen once
    at startup instead of repeating `font_name`/`rtl()` on every widget.
    """
    return re.sub(r"'([^']*)'", lambda m: "'" + _shape_segment(m.group(1)) + "'", kv_text)


KV = r'''
#:import dp kivy.metrics.dp
<MainUI>:
    orientation: 'vertical'
    padding: dp(12)
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: (0.95, 0.965, 0.98, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        size_hint_y: None
        height: dp(54)
        canvas.before:
            Color:
                rgba: (0.08, 0.20, 0.34, 1)
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(12)]
        Label:
            text: '[b]HASANINEJAD[/b]\n[font=Roboto]سامانه ثبت مأموریت و تردد[/font]'
            markup: True
            color: 1,1,1,1
            halign: 'center'
            valign: 'middle'
            text_size: self.size
    Label:
        text: root.today_text
        size_hint_y: None
        height: dp(28)
        color: (0.15,0.22,0.3,1)
        bold: True
    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(8)
        Button:
            text: 'شروع مأموریت / خروج'
            background_normal: ''
            background_color: (0.12,0.42,0.68,1)
            on_release: root.start_mission()
            disabled: root.has_active
        Button:
            text: 'پایان مأموریت / بازگشت'
            background_normal: ''
            background_color: (0.12,0.52,0.36,1)
            on_release: root.finish_mission()
            disabled: not root.has_active
    Label:
        text: root.status_text
        size_hint_y: None
        height: dp(34)
        color: (0.12,0.28,0.38,1)
        halign: 'center'
        valign: 'middle'
        text_size: self.size
    Label:
        text: 'مکان مأموریت'
        size_hint_y: None
        height: dp(22)
        color: (0.15,0.2,0.25,1)
        halign: 'right'
        text_size: self.size
    TextInput:
        id: location
        hint_text: 'مثلاً: شعبه مرکزی، اداره ...'
        multiline: False
        size_hint_y: None
        height: dp(42)
        padding: [dp(10),dp(10)]
    Label:
        text: 'توضیحات فنی / شرح مأموریت'
        size_hint_y: None
        height: dp(22)
        color: (0.15,0.2,0.25,1)
        halign: 'right'
        text_size: self.size
    TextInput:
        id: details
        hint_text: 'شرح کوتاه مأموریت را وارد کن'
        multiline: True
        size_hint_y: None
        height: dp(74)
        padding: [dp(10),dp(10)]
    BoxLayout:
        size_hint_y: None
        height: dp(42)
        spacing: dp(8)
        Button:
            text: 'گزارش سریع جداگانه'
            background_normal: ''
            background_color: (0.38,0.42,0.48,1)
            on_release: root.quick_report()
        Button:
            text: 'خروجی Excel (CSV)'
            background_normal: ''
            background_color: (0.12,0.48,0.34,1)
            on_release: root.export_csv()
    Label:
        text: 'سوابق مأموریت‌ها'
        size_hint_y: None
        height: dp(28)
        color: (0.08,0.20,0.34,1)
        bold: True
        halign: 'right'
        text_size: self.size
    ScrollView:
        do_scroll_x: False
        GridLayout:
            id: history
            cols: 1
            spacing: dp(7)
            size_hint_y: None
            height: self.minimum_height
'''


class MainUI(BoxLayout):
    today_text = StringProperty('')
    status_text = StringProperty('')
    has_active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        data_dir = app.user_data_dir if app else os.getcwd()
        self.db_path = os.path.join(data_dir, 'missions.db')
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('''CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, start_iso TEXT NOT NULL, end_iso TEXT,
            start_jalali TEXT NOT NULL, end_jalali TEXT, location TEXT, details TEXT,
            duration_minutes INTEGER, status TEXT NOT NULL DEFAULT 'active')''')
        self.conn.commit()
        self.refresh()
        Clock.schedule_interval(lambda *_: self.refresh_clock(), 30)

    # -- state ------------------------------------------------------------
    def refresh_clock(self):
        self.today_text = rtl(
            'امروز: ' + fa_digits(jalali_today())
            + '   ساعت: ' + datetime.now().strftime('%H:%M')
        )

    def refresh(self):
        self.refresh_clock()
        row = self.conn.execute(
            "SELECT * FROM missions WHERE status='active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.has_active = bool(row)
        if row:
            self.status_text = rtl(
                'مأموریت باز از ساعت ' + row['start_iso'][11:16]
                + ' در تاریخ ' + row['start_jalali'] + '؛ هنوز پایان ثبت نشده است.'
            )
        else:
            self.status_text = rtl('هنوز مأموریتی در جریان نیست.')

        self.ids.history.clear_widgets()
        rows = self.conn.execute(
            "SELECT * FROM missions WHERE status='done' ORDER BY id DESC LIMIT 50"
        ).fetchall()
        for r in rows:
            self._add_history_card(r)

    def _add_history_card(self, r):
        from kivy.graphics import Color, RoundedRectangle

        duration = r['duration_minutes'] or 0
        h, m = divmod(duration, 60)
        txt = (
            f"تاریخ: {r['start_jalali']}\n"
            f"خروج: {r['start_iso'][11:16]}   "
            f"بازگشت: {r['end_iso'][11:16] if r['end_iso'] else '-'}\n"
            f"مدت: {h} ساعت و {m} دقیقه\n"
            f"مکان: {r['location'] or '-'}\n"
            f"توضیحات: {r['details'] or '-'}\n"
            f"وضعیت: ثبت نهایی"
        )
        card = Label(
            text=rtl(txt),
            size_hint_y=None,
            height=dp(150),
            halign='right',
            valign='middle',
            color=(0.1, 0.17, 0.23, 1),
            padding=(dp(10), dp(8)),
            font_size=dp(13),
        )
        card.text_size = (card.width - dp(20), None)
        card.bind(width=lambda w, v: setattr(w, 'text_size', (v - dp(20), None)))
        with card.canvas.before:
            Color(1, 1, 1, 1)
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
        card.bind(pos=lambda w, p: setattr(w._bg, 'pos', p),
                  size=lambda w, s: setattr(w._bg, 'size', s))
        self.ids.history.add_widget(card)

    # -- ui helpers -------------------------------------------------------
    def popup(self, title, message):
        lbl = Label(text=rtl(message), halign='center', valign='middle')
        lbl.bind(size=lambda w, s: setattr(w, 'text_size', (s[0] * 0.9, None)))
        Popup(title=rtl(title), content=lbl, size_hint=(.86, .34)).open()

    # -- actions ----------------------------------------------------------
    def start_mission(self):
        active = self.conn.execute(
            "SELECT id FROM missions WHERE status='active'"
        ).fetchone()
        if active:
            self.popup('مأموریت فعال', 'ابتدا مأموریت فعلی را به پایان برسان.')
            return
        now = datetime.now()
        jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
        jdate = f'{jy:04d}/{jm:02d}/{jd:02d}'
        self.conn.execute(
            'INSERT INTO missions(start_iso,start_jalali,location,details,status) '
            'VALUES(?,?,?,?,?)',
            (now.isoformat(timespec='seconds'), jdate,
             self.ids.location.text.strip(), self.ids.details.text.strip(), 'active'),
        )
        self.conn.commit()
        self.ids.location.text = ''
        self.ids.details.text = ''
        self.refresh()
        self.popup('ثبت خروج',
                   'زمان خروج با موفقیت ثبت شد. مأموریت تا زمان ثبت بازگشت محفوظ می‌ماند.')

    def finish_mission(self):
        row = self.conn.execute(
            "SELECT * FROM missions WHERE status='active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            self.popup('مأموریت فعال نیست', 'ابتدا شروع مأموریت را ثبت کن.')
            return
        now = datetime.now()
        jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
        jdate = f'{jy:04d}/{jm:02d}/{jd:02d}'
        start = datetime.fromisoformat(row['start_iso'])
        minutes = max(0, int((now - start).total_seconds() // 60))
        loc = self.ids.location.text.strip() or row['location'] or ''
        details = self.ids.details.text.strip() or row['details'] or ''
        self.conn.execute(
            "UPDATE missions SET end_iso=?,end_jalali=?,location=?,details=?,"
            "duration_minutes=?,status='done' WHERE id=?",
            (now.isoformat(timespec='seconds'), jdate, loc, details, minutes, row['id']),
        )
        self.conn.commit()
        self.refresh()
        self.popup('ثبت بازگشت', 'مأموریت با موفقیت تکمیل و در سوابق ذخیره شد.')

    def quick_report(self):
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button

        box = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))
        loc = TextInput(hint_text='مکان', multiline=False, size_hint_y=None, height=dp(42))
        desc = TextInput(hint_text='شرح گزارش سریع', multiline=True)
        box.add_widget(loc)
        box.add_widget(desc)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        save = Button(text=rtl('ذخیره گزارش'))
        back = Button(text=rtl('بازگشت'))
        row.add_widget(save)
        row.add_widget(back)
        box.add_widget(row)
        pop = Popup(title=rtl('گزارش سریع جداگانه'), content=box, size_hint=(.92, .62))

        def save_report(*_):
            now = datetime.now()
            jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
            jdate = f'{jy:04d}/{jm:02d}/{jd:02d}'
            self.conn.execute(
                'INSERT INTO missions(start_iso,end_iso,start_jalali,end_jalali,'
                'location,details,duration_minutes,status) VALUES(?,?,?,?,?,?,?,?)',
                (now.isoformat(timespec='seconds'), now.isoformat(timespec='seconds'),
                 jdate, jdate, loc.text.strip(), desc.text.strip(), 0, 'done'),
            )
            self.conn.commit()
            pop.dismiss()
            self.refresh()

        save.bind(on_release=save_report)
        back.bind(on_release=lambda *_: pop.dismiss())
        pop.open()

    def export_csv(self):
        rows = self.conn.execute(
            'SELECT start_jalali,start_iso,end_jalali,end_iso,duration_minutes,'
            'location,details,status FROM missions ORDER BY id'
        ).fetchall()
        if not rows:
            self.popup('گزارش', 'هنوز اطلاعاتی برای خروجی وجود ندارد.')
            return
        path = os.path.join(
            App.get_running_app().user_data_dir, 'HASANINEJAD-report.csv'
        )
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['تاریخ خروج', 'ساعت خروج', 'تاریخ بازگشت', 'ساعت بازگشت',
                        'مدت (دقیقه)', 'مکان', 'توضیحات', 'وضعیت'])
            for r in rows:
                w.writerow([
                    r['start_jalali'],
                    r['start_iso'][11:16],
                    r['end_jalali'] or '',
                    r['end_iso'][11:16] if r['end_iso'] else '',
                    r['duration_minutes'] or '',
                    r['location'] or '',
                    r['details'] or '',
                    r['status'],
                ])
        self.popup(
            'فایل گزارش ساخته شد',
            'گزارش CSV در حافظه داخلی برنامه ذخیره شد:\n' + path
            + '\nمی‌توانی آن را با Excel باز کنی. در نسخه بعدی انتخاب محل ذخیره'
              ' و فایل XLSX/PDF اضافه می‌شود.',
        )


class HasaninejadApp(App):
    title = APP_TITLE

    def build(self):
        if platform == 'android':
            from kivy.core.window import Window
            # Keep the text fields visible while the on-screen keyboard is up.
            Window.softinput_mode = 'below_target'
        Builder.load_string(shape_kv(KV))
        return MainUI()

    def on_stop(self):
        try:
            self.root.conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    HasaninejadApp().run()
