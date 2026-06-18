import csv
import os
from django.core.management.base import BaseCommand
from inventory.models import HargaJual  # Pastikan nama model Anda sesuai

class Command(BaseCommand):
    help = 'Migrasi data produk dari MDBARANG dengan filter JENIS = Produk'

    def handle(self, *args, **options):
        file_path = 'barang_lama.csv'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File '{file_path}' tidak ditemukan di root folder proyek!"))
            return

        self.stdout.write(self.style.SUCCESS('🚀 Memulai migrasi data Harga Jual (Format Pembatas: Koma)...'))
        
        sukses_count = 0
        diabaikan_count = 0
        gagal_count = 0

        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            # PENTING: Delimiter dilepas/default ke koma (,) karena file Anda menggunakan koma
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    v_jenis  = row.get('JENIS')
                    v_nama   = row.get('NAMABARANG')
                    v_harga_raw = row.get('HRGJUAL')

                    # 1. VALIDASI FILTER (Case Insensitive & Strip Spasi)
                    if v_jenis:
                        v_jenis_bersih = v_jenis.strip().lower()
                    else:
                        v_jenis_bersih = ''

                    if v_jenis_bersih != 'produk':
                        diabaikan_count += 1
                        continue

                    # Jika nama barang kosong, skip
                    if not v_nama:
                        continue

                    v_nama = v_nama.strip()

                    # 2. KONVERSI HARGA
                    if v_harga_raw:
                        v_harga_raw = v_harga_raw.strip()
                        try:
                            v_harga_jual = float(v_harga_raw)
                        except ValueError:
                            v_harga_jual = 0.0
                    else:
                        v_harga_jual = 0.0

                    # 3. SIMPAN / UPDATE KE POSTGRESQL SUBA BASE
                    HargaJual.objects.update_or_create(
                        nama_produk=v_nama,
                        defaults={
                            'harga_jual_akhir': v_harga_jual,
                        }
                    )
                    
                    self.stdout.write(f"  [PRODUK] {v_nama} -> Rp {v_harga_jual:,}")
                    sukses_count += 1

                except Exception as e:
                    gagal_count += 1
                    self.stdout.write(self.style.ERROR(f"❌ Gagal pada data '{v_nama}': {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f'\n✨ Selesai! Berhasil migrasi {sukses_count} produk ke tabel harga jual.'))
        self.stdout.write(f"ℹ️ Data non-produk (seperti 'Bahan') yang diabaikan: {diabaikan_count} baris.")
        if gagal_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️ Terjadi kegagalan pada {gagal_count} data.'))