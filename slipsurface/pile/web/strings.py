"""
Text of the interface shell.

Nothing is written into the page: the browser fetches this dictionary from
`/api/meta`, so changing the language is handled in one place and the wording
sits beside the rest of the program's translations. Whatever `i18n` already
says is reused; only what the web shell adds of its own is spelled out here.
"""

from __future__ import annotations

from ..i18n import TRANSLATIONS

#: Text the web shell needs and the rest of the program does not.
#: key -> (English, Turkish)
SHELL = {
    "tagline": ("axial capacity, groups, settlement and rock sockets of piles",
                "kazıkların eksenel taşıma gücü, grupları, oturması ve kaya soketleri"),
    "language": ("Language", "Dil"),
    "open": ("Open…", "Aç…"),
    "save": ("Save", "Kaydet"),
    "theme": ("Theme", "Tema"),
    "ready": ("Ready.", "Hazır."),
    "tab_inputs": ("1 · Pile and soil", "1 · Kazık ve zemin"),
    "tab_socket": ("2 · Rock socket", "2 · Kaya soketi"),
    "tab_study_inputs": ("3 · Study", "3 · Çalışma"),
    "add_row": ("+ Add row", "+ Satır ekle"),
    "del_row": ("− Remove row", "− Satır sil"),
    "soil_group": ("Soil profile (from the ground surface down)",
                   "Zemin profili (yüzeyden aşağı)"),
    "methods_title": ("Net ultimate capacity by method (kN)",
                      "Yönteme göre net nihai taşıma gücü (kN)"),
    "socket_table_title": ("Side shear and socket length by correlation",
                           "Bağıntılara göre yanal sürtünme ve soket boyu"),
    "socket_group_note": ("The water table is the one given under Pile and soil.",
                          "Su tablası, Kazık ve zemin sekmesinde girilen değerdir."),
    "view_summary": ("Summary", "Özet"),
    "view_text": ("Results", "Sonuçlar"),
    "view_figures": ("Figures", "Şekiller"),
    "view_study": ("Study", "Çalışma"),
    "figure": ("Figure", "Şekil"),
    "output": ("Output", "Çıktı"),
    "report_format": ("Report", "Rapor"),
    "report_pdf": ("PDF report", "PDF rapor"),
    "report_html": ("HTML report", "HTML rapor"),
    "report_docx": ("Word report", "Word rapor"),
    "no_results": ("Run the analysis.", "Analizi çalıştırın."),
    "no_socket": ("Run the rock socket analysis.", "Kaya soketi analizini çalıştırın."),
    "no_study": ("Define study variables and run the study.",
                 "Çalışma değişkenlerini tanımlayıp çalışmayı başlatın."),
    "error": ("Error", "Hata"),
    "saved": ("Saved.", "Kaydedildi."),
    "loaded": ("Project loaded.", "Proje yüklendi."),
    "bad_file": ("That file is not a SlipSurface IQ Pile project.",
                 "Bu dosya bir SlipSurface IQ Pile projesi değil."),
    "busy": ("An analysis is already running.", "Bir hesap zaten sürüyor."),
    "cancelled": ("Cancelled.", "İptal edildi."),
    "stop_hint": ("Press Ctrl+C to stop.", "Durdurmak için Ctrl+C."),
    "stopped": ("stopped", "durduruldu"),
}

#: Keys taken straight from the program's translations, under the same name.
REUSED = [
    "run_analysis_button", "run_socket_button", "running_analysis", "analysis_complete",
    "socket_complete", "report_action", "report_running", "warnings_title", "soil_note",
    "study_run", "study_cancel", "study_export_csv", "study_export_xlsx",
    "study_vars_group", "study_no_vars", "study_progress", "study_done", "study_failed",
    "study_no_data", "study_table_note",
]


def shell_strings(lang: str = "en") -> dict:
    """Every string the page needs, in one language."""
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    strings = {key: (tr if lang == "tr" else en) for key, (en, tr) in SHELL.items()}
    strings.update({key: translations[key] for key in REUSED})
    return strings
