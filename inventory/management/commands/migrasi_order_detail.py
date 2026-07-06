import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction

def ke_angka(teks, default=0.0):
    if not teks:
        return default
    try:
        return float(teks.strip())
    except (ValueError, TypeError):
        return default

class Command(BaseCommand):
    help = 'Migrasi detail barang sekaligus validasi nama order utama'

    def handle(self, *args, **options):
        from inventory.models import OrderUtama, OrderDetail

        file_transaksi = 'TRANSAKSI.csv'
        file_detail = 'TRANSAKSIDETIL.csv'

        if not os.path.exists(file_transaksi) or not os.path.exists(file_detail):
            self.stdout.write(self.style.ERROR("File TRANSAKSI.csv atau TRANSAKSIDETIL.csv tidak ditemukan!"))
            return

        self.stdout.write(self.style.SUCCESS('🚀 Langkah 1: Memetakan relasi TJ -> SO...'))
        peta_tj_ke_so = {}
        with open(file_transaksi, mode='r', encoding='utf-8-sig') as f_trans:
            reader_trans = csv.DictReader(f_trans)
            for row in reader_trans:
                kode = row.get('KODE', '').strip()
                if kode == 'TJ':
                    notrans_tj = row.get('NOTRANS', '').strip()
                    noref_so = row.get('NOREF', '').strip()
                    if notrans_tj and noref_so:
                        peta_tj_ke_so[notrans_tj] = noref_so

        self.stdout.write(self.style.SUCCESS('🚀 Langkah 2: Memproses detail item barang...'))

        count_sukses = 0

        with open(file_detail, mode='r', encoding='utf-8-sig') as f_detil:
            reader_detil = csv.DictReader(f_detil)
            
            with transaction.atomic():
                for row in reader_detil:
                    notrans_csv = row.get('NOTRANS', '').strip()
                    kode_jenis = row.get('KODE', '').strip()
                    
                    target_no_order = None
                    if kode_jenis == 'SO':
                        target_no_order = notrans_csv
                    elif kode_jenis == 'TJ':
                        target_no_order = peta_tj_ke_so.get(notrans_csv)

                    if not target_no_order:
                        continue

                    order_target = OrderUtama.objects.filter(no_order=target_no_order).first()
                    
                    if order_target:
                        try:
                            nama_barang = row.get('NAMABARANG', '').strip()
                            nama_pesanan = row.get('NAMAPESANAN', '').strip() or nama_barang
                            kode_barang = row.get('KODEBARANG', '').strip()
                            uraian = row.get('URAIAN', '').strip()
                            
                            panjang = ke_angka(row.get('PANJANG'), 1.0)
                            lebar = ke_angka(row.get('LEBAR'), 1.0)
                            
                            qty = int(ke_angka(row.get('JML'), 1.0))
                            if qty == 0:
                                qty = int(ke_angka(row.get('JMLJUAL'), 1.0))
                                
                            harga_dasar = ke_angka(row.get('HRGBELI'), 0.0)
                            harga_jual = ke_angka(row.get('HRGJUAL'), 0.0)
                            if harga_jual == 0:
                                harga_jual = ke_angka(row.get('HRGTERJUAL'), 0.0)
                                
                            jasa_desain = ke_angka(row.get('JASADESAIN'), 0.0)
                            biaya_lain = ke_angka(row.get('BIAYALAIN'), 0.0)

                            if panjang > 0 and lebar > 0 and kode_jenis == 'SO':
                                subtotal = panjang * lebar * float(qty) * harga_jual + jasa_desain + biaya_lain
                            else:
                                subtotal = float(qty) * harga_jual + jasa_desain + biaya_lain

                            # UPDATE OTOMATIS: Jika nama_order bawaan masih berupa teks "Order SOxxx", ganti dengan nama item asli cetakannya!
                            if order_target.nama_order.startswith("Order SO"):
                                order_target.nama_order = nama_pesanan
                                order_target.save()

                            OrderDetail.objects.create(
                                order_utama=order_target,
                                nama_pesanan=nama_pesanan,
                                nama_item=nama_barang,
                                kode_item=kode_barang,
                                qty=qty,
                                panjang=panjang,
                                lebar=lebar,
                                harga_dasar=harga_dasar,
                                harga_jual=harga_jual,
                                jasa_desain=jasa_desain,
                                biaya_lain=biaya_lain,
                                total=subtotal,
                                keterangan=uraian
                            )
                            count_sukses += 1

                        except Exception:
                            pass

        self.stdout.write(self.style.SUCCESS(f"✅ Selesai! Berhasil memigrasi {count_sukses} baris detail barang dengan nama order akurat!"))