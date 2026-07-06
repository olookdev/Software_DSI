import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone

class Command(BaseCommand):
    help = 'Migrasi data SO dan TJ dengan status terupdate dan nama order akurat'

    def handle(self, *args, **options):
        from inventory.models import OrderUtama, Customer 

        file_path = 'TRANSAKSI.csv'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File '{file_path}' tidak ditemukan!"))
            return

        # =========================================================================
        # PROSES 1: AMBIL SEMUA DATA PESANAN (SO)
        # =========================================================================
        self.stdout.write(self.style.SUCCESS('🚀 Tahap 1: Memasukkan data Pesanan (SO)...'))
        
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                kode_jenis = row.get('KODE', '').strip()
                if kode_jenis != 'SO':
                    continue

                try:
                    notrans_so = row.get('NOTRANS', '').strip()
                    kode_pelanggan = row.get('KODEPELANGGAN', '').strip()
                    customer_obj = Customer.objects.filter(kode_customer=kode_pelanggan).first()
                    
                    if not customer_obj:
                        continue

                    tgl_str = row.get('TGLORDER') or row.get('TGLTRANS')
                    tgl_dt = datetime.strptime(tgl_str.strip(), '%Y-%m-%d') if tgl_str else datetime.now()
                    tgl_aware = timezone.make_aware(tgl_dt)

                    v_total = float(row.get('TOTALTRANS') or 0.0)
                    v_dp = float(row.get('DP') or row.get('JMLBAYAR') or 0.0)
                    
                    # AMBIL NAMA ORDER ASLI: dari kolom CATATAN di csv
                    catatan = row.get('CATATAN', '').strip()
                    nama_project = catatan if catatan else f"Order {notrans_so}"

                    OrderUtama.objects.update_or_create(
                        no_order=notrans_so,
                        defaults={
                            'tgl_order': tgl_aware,
                            'customer': customer_obj,
                            'nama_order': nama_project, # Tidak lagi berisi "-"
                            'total_harga': v_total,
                            'uang_muka': v_dp,
                            'sisa_bayar': v_total - v_dp,
                            'status': 'order',          # Menggunakan pilihan status baru Mas
                            'keterangan': f"Migrasi SO: {notrans_so}"
                        }
                    )
                except Exception:
                    pass

        # =========================================================================
        # PROSES 2: SINKRONISASI KEUANGAN & STATUS (TJ)
        # =========================================================================
        self.stdout.write(self.style.SUCCESS('🔥 Tahap 2: Sinkronisasi Pembayaran & Status (TJ)...'))
        
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            file.seek(0)
            reader = csv.DictReader(file)
            
            for row in reader:
                kode_jenis = row.get('KODE', '').strip()
                if kode_jenis != 'TJ':
                    continue

                try:
                    noref_so = row.get('NOREF', '').strip()
                    notrans_tj = row.get('NOTRANS', '').strip()

                    if not noref_so:
                        continue

                    order_target = OrderUtama.objects.filter(no_order=noref_so).first()
                    
                    if order_target:
                        v_total_tj = float(row.get('TOTALTRANS') or 0.0)
                        v_bayar_tj = float(row.get('JMLBAYAR') or 0.0)
                        v_dp_tj = float(row.get('DP') or 0.0)

                        uang_masuk = v_dp_tj + v_bayar_tj
                        sisa_tagihan = v_total_tj - uang_masuk

                        order_target.total_harga = v_total_tj
                        order_target.uang_muka = uang_masuk
                        order_target.sisa_bayar = sisa_tagihan if sisa_tagihan > 0 else 0.0
                        
                        # LOGIKA STATUS BARU MAS:
                        if sisa_tagihan > 0:
                            order_target.status = 'proses' # Masuk proses/piutang jika sisa uang masih ada
                        else:
                            order_target.status = 'selesai' # Selesai jika lunas total

                        order_target.keterangan = f"Migrasi Gabungan (SO: {noref_so} | TJ: {notrans_tj})"
                        order_target.save()

                except Exception:
                    pass

        self.stdout.write(self.style.SUCCESS('✅ Selesai! Sinkronisasi data utama berhasil.'))