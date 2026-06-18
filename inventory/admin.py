from django.contrib import admin
from .models import Suplier, Customer, List_Stok, JenisBarang, HargaStok, HargaJual, ArusStok, OrderUtama

admin.site.register(Suplier)
admin.site.register(Customer)
admin.site.register(List_Stok)
admin.site.register(JenisBarang)
admin.site.register(HargaStok)
admin.site.register(HargaJual)
admin.site.register(ArusStok)
admin.site.register(OrderUtama)
