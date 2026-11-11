"""
dogfitness/pdf_fonts.py

WSPOLNY modul dla generowania PDF w calym projekcie (uzywany przez
plans/document_generation.py ORAZ clients/views.py:dog_pdf).

Umieszczony na poziomie projektu (nie w konkretnej aplikacji), zeby
zachowac zasade modulowosci: 'clients' NIE powinien zalezec od 'plans'
(plans zalezy od clients, nie odwrotnie) - wspolna logika PDF idzie
wiec do neutralnego miejsca.

1) REJESTRACJA FONTOW TTF (DejaVu)
   Domyslne fonty Type1 w reportlab (Helvetica/Times/Courier) NIE
   wspieraja polskich znakow diakrytycznych (renderuja sie jako czarne
   kwadraty). Fonty TTF DejaVu maja pelne wsparcie Unicode i sa
   wizualnie zblizone do oryginalnych rodzin (Sans ~ Helvetica,
   Serif ~ Times, Mono ~ Courier).

2) BEZPIECZNE NAGLOWKI Content-Disposition Z POLSKIMI ZNAKAMI (RFC 6266)
   Gdy nazwa pliku w Content-Disposition zawiera znaki poza ASCII,
   NIE wolno ich wpisywac bezposrednio - HTTP headers musza byc ASCII/
   Latin-1. Bez odpowiedniego kodowania Python/Django automatycznie
   stosuje MIME encoded-word (RFC 2047, "=?utf-8?b?...?="), ktory jest
   przeznaczony dla nagłowkow e-mail, a WIELE przegladarek nie
   interpretuje go poprawnie w Content-Disposition - w efekcie uzytkownik
   widzi plik pobrany pod dziwna, zakodowana nazwa.
   Poprawny standard dla HTTP to RFC 6266: ASCII fallback + dodatkowy
   parametr filename*=UTF-8''<percent-encoded>, ktory wspolczesne
   przegladarki poprawnie dekodujA, zachowujac oryginalna nazwe.
"""

import os
import re
from urllib.parse import quote

from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============================================================
# REJESTRACJA FONTOW TTF
# ============================================================

FONTS_DIR = os.path.join(settings.BASE_DIR, 'static', 'fonts')

# kod wybrany w BrandingProfile.font_family (lub 'Helvetica' jako domyslny
# dla miejsc bez brandingu, np. karta psa) -> (regular, bold)
FONT_MAP = {
    'Helvetica': ('PL-Sans', 'PL-Sans-Bold'),
    'Times-Roman': ('PL-Serif', 'PL-Serif-Bold'),
    'Courier': ('PL-Mono', 'PL-Mono-Bold'),
}

_fonts_registered = False


def register_pdf_fonts():
    """Rejestruje fonty TTF w reportlab (raz na proces, idempotentne)."""
    global _fonts_registered
    if _fonts_registered:
        return
    font_files = [
        ('PL-Sans', 'DejaVuSans.ttf'),
        ('PL-Sans-Bold', 'DejaVuSans-Bold.ttf'),
        ('PL-Serif', 'DejaVuSerif.ttf'),
        ('PL-Serif-Bold', 'DejaVuSerif-Bold.ttf'),
        ('PL-Mono', 'DejaVuSansMono.ttf'),
        ('PL-Mono-Bold', 'DejaVuSansMono-Bold.ttf'),
    ]
    for font_name, file_name in font_files:
        font_path = os.path.join(FONTS_DIR, file_name)
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
            except Exception:
                pass
    _fonts_registered = True


def get_pdf_fonts(font_family='Helvetica'):
    """Zwraca (font_regular, font_bold) - nazwy fontow PL-* zarejestrowanych
    w reportlab, z pelnym wsparciem polskich znakow. Uzyj tej funkcji
    zawsze zamiast wbudowanych 'Helvetica'/'Times-Roman'/'Courier'."""
    register_pdf_fonts()
    return FONT_MAP.get(font_family, FONT_MAP['Helvetica'])


# ============================================================
# BEZPIECZNE NAGLOWKI Content-Disposition (RFC 6266) Z POLSKIMI ZNAKAMI
# ============================================================

_PL_ASCII_MAP = {
    'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
    'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z',
}


def to_ascii_filename(text):
    """Transliteruje polskie znaki na ASCII - uzywane TYLKO jako fallback
    dla starych klientow HTTP w Content-Disposition (nigdy do tresci
    dokumentu - tam zawsze uzywamy pelnego Unicode przez fonty TTF)."""
    if not text:
        return text
    ascii_text = ''.join(_PL_ASCII_MAP.get(ch, ch) for ch in str(text))
    # usuwamy wszystko poza ASCII na wszelki wypadek (inne jezyki/znaki specjalne)
    ascii_text = re.sub(r'[^\x20-\x7E]', '_', ascii_text)
    return ascii_text


def content_disposition(disposition_type, filename):
    """Buduje poprawny naglowek Content-Disposition (RFC 6266) wspierajacy
    polskie znaki w nazwie pliku - z fallbackiem ASCII dla starych klientow
    i poprawnie zakodowanym filename* dla wspolczesnych przegladarek.

    Przyklad uzycia:
        response['Content-Disposition'] = content_disposition(
            'attachment', 'plan_szczegółowy_Żaka.pdf'
        )
    """
    ascii_name = to_ascii_filename(filename)
    utf8_quoted = quote(filename, safe='')
    return f"{disposition_type}; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_quoted}"
