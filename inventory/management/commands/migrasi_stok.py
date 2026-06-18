import csv
import os
from django.core.management.base import BaseCommand
from inventory.models import List_Stok 

class Command(BaseCommand):
    help = 'Migrasi data master stok bahan dari CSV ke PostgreSQL'

    def handle(self, *args, **options):
        file_path = 'stok.csv'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File '{file_path}' tidak ditemukan!"))
            return

        self.stdout.write(self.style.SUCCESS('🚀 Memulai ulang migrasi data List Stok (Perbaikan Akurasi)...'))
        sukses_count = 0

        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            # Gunakan reader biasa dengan pemisah titik koma
            reader = csv.reader(file, delimiter=';')
            
            # Lewati baris pertama (Header: No;Nama Bahan;Jumlah)
            next(reader)
            
            for row in reader:
                try:
                    # Lewati jika baris kosong atau rusak
                    if not row or len(row) < 3:
                        continue

                    # Ambil data mutlak berdasarkan nomor kolom/index posisi
                    # row[1] adalah kolom ke-2 (Nama Bahan)
                    # row[2] adalah kolom ke-3 (Jumlah)
                    v_nama = row[1].strip()
                    v_qty_mentah = row[2].strip()

                    if not v_nama:
                        continue

                    # Bersihkan angka dan konversi ke float secara aman
                    try:
                        v_qty = float(v_qty_mentah)
                    except ValueError:
                        v_qty = 0.0

                    # Generate Kode Barang Otomatis
                    jumlah_data = List_Stok.objects.count() + 1
                    v_kode = f"B-{str(jumlah_data).zfill(3)}"

                    # Simpan / Update ke PostgreSQL Supabase
                    List_Stok.objects.update_or_create(
                        nama_barang=v_nama,
                        defaults={
                            'kode_barang': v_kode,
                            'qty': v_qty,
                        }
                    )
                    
                    self.stdout.write(f"  [SUKSES] {v_kode} - {v_nama} (Stok Aktual: {v_qty})")
                    sukses_count += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Gagal pada baris data: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f'\n✨ Selesai! Berhasil memperbaiki dan memindahkan {sukses_count} data bahan.'))