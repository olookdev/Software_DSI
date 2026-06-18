import csv
import os
from django.core.management.base import BaseCommand
from inventory.models import Suplier  # Pastikan nama model 'Suplier' sudah sesuai

class Command(BaseCommand):
    help = 'Migrasi data suplier tertentu dari CSV Firebird ke PostgreSQL'

    def handle(self, *args, **options):
        # Nama file CSV yang ditaruh sejajar dengan manage.py
        file_path = 'suplier_lama.csv'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File '{file_path}' tidak ditemukan di root folder proyek!"))
            self.stdout.write(self.style.WARNING("Pastikan Anda sudah menaruh file CSV hasil ekspor DBeaver sejajar dengan file manage.py"))
            return

        self.stdout.write(self.style.SUCCESS('🚀 Memulai migrasi data suplier...'))
        
        sukses_count = 0
        gagal_count = 0

        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            # DictReader membaca baris pertama sebagai nama kolom (Header)
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    # =========================================================================
                    # MAPPING KOLOM SESUAI PERMINTAAN ANDA
                    # =========================================================================
                    v_kode    = row.get('KODEPEMASOK')
                    v_nama    = row.get('NAMAPEMASOK')
                    v_alamat  = row.get('ALAMAT')
                    v_telepon = row.get('TLP1')
                    v_email   = row.get('EMAIL')

                    # Validasi minimal: Jika nama supplier kosong, lewati baris ini
                    if not v_nama:
                        continue

                    # Bersihkan spasi kosong (whitespace) di awal/akhir teks jika ada
                    v_kode = v_kode.strip() if v_kode else ''
                    v_nama = v_nama.strip()
                    v_alamat = v_alamat.strip() if v_alamat else '-'
                    v_telepon = v_telepon.strip() if v_telepon else '-'
                    v_email = v_email.strip() if v_email else '-'

                    # Jika kode suplier kosong dari database lama, buat otomatis agar tidak error
                    if not v_kode:
                        jumlah_data = Suplier.objects.count() + 1
                        v_kode = f"S-{str(jumlah_data).zfill(3)}"

                    # Simpan ke database PostgreSQL / Supabase Anda
                    # Menggunakan update_or_create berdasarkan kode_suplier agar tidak duplikat
                    Suplier.objects.update_or_create(
                        kode_suplier=v_kode,
                        defaults={
                            'nama_suplier': v_nama,
                            'alamat': v_alamat,
                            'telepon': v_telepon,
                            'email': v_email,
                        }
                    )
                    sukses_count += 1

                except Exception as e:
                    gagal_count += 1
                    self.stdout.write(self.style.ERROR(f"❌ Gagal migrasi suplier '{v_nama}': {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f'\n✨ Selesai! Berhasil migrasi {sukses_count} suplier.'))
        if gagal_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️ Terjadi kegagalan pada {gagal_count} data.'))