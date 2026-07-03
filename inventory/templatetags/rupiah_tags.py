from django import template
from num2words import num2words

register = template.Library()

@register.filter(name='terbilang_rupiah')
def terbilang_rupiah(value):
    if not value:
        return "# NOL RUPIAH #"
    
    try:
        # Konversi ke integer untuk membuang desimal .00
        angka = int(float(value))
        
        # Mengubah angka menjadi kata dalam bahasa Indonesia
        kata = num2words(angka, lang='id')
        
        # Format menjadi huruf besar semua dan dibungkus pagar
        return f"# {kata.upper()} RUPIAH #"
    except (ValueError, TypeError):
        return "# DATA TIDAK VALID #"