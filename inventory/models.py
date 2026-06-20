from django.db import models
from django.utils import timezone
from datetime import datetime

class Suplier(models.Model):
    kode_suplier = models.CharField(max_length=20, unique=True)
    nama_suplier = models.CharField(max_length=100)
    alamat = models.TextField(blank=True, null=True)
    telepon = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kode_suplier} - {self.nama_suplier}"
    
class Customer(models.Model):
    kode_customer = models.CharField(max_length=20, unique=True)
    nama_customer = models.CharField(max_length=100)
    alamat = models.TextField(blank=True, null=True)
    telepon = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    total_transaksi = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):  
        return f"{self.kode_customer} - {self.nama_customer}"
    
class JenisBarang(models.Model):
    nama = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nama
    
class List_Stok(models.Model):
    kode_barang = models.CharField(max_length=20, unique=True)
    nama_barang = models.CharField(max_length=100, db_index=True)
    jenis = models.ForeignKey(JenisBarang, on_delete=models.SET_NULL, null=True, blank=True)
    satuan = models.CharField(max_length=50, blank=True, null=True)
    ukuran = models.CharField(max_length=50, blank=True, null=True)
    keterangan = models.CharField(max_length=255, blank=True, null=True)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):  
        return f"{self.kode_barang} - {self.nama_barang}"

class HargaStok(models.Model):
    barang = models.ForeignKey('List_Stok', on_delete=models.CASCADE, related_name='daftar_harga')
    suplier = models.ForeignKey('Suplier', on_delete=models.CASCADE, related_name='harga_suplier')
    harga_satuan = models.DecimalField(max_digits=12, decimal_places=2, default=0)    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.barang.nama_barang} - {self.suplier.nama_suplier} (Rp {self.harga_satuan})"

class HargaJual(models.Model):
    kode_produk = models.CharField(max_length=50, unique=True, blank=True, null=True)
    nama_produk = models.CharField(max_length=150) 
    biaya_tenaga_kerja = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    biaya_listrik = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    keterangan_produk = models.TextField(blank=True, null=True)
    harga_jual_akhir = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    bahan_baku = models.ManyToManyField('List_Stok', through='HargaJualBahan', related_name='produk_jual')

    def save(self, *args, **kwargs):
        if not self.kode_produk:
            sekarang = timezone.now()
            tahun_bulan = sekarang.strftime('%y%m')
            prefix = f"PRD-{tahun_bulan}-"
            
            jumlah_produk_bulan_ini = HargaJual.objects.filter(kode_produk__startswith=prefix).count()
            nomor_urut = jumlah_produk_bulan_ini + 1
            
            self.kode_produk = f"{prefix}{nomor_urut:04d}"
            
        super().save(*args, **kwargs)

    @property
    def total_modal(self):
        total_bahan = sum(item.harga_stok_terpilih.harga_satuan for item in self.list_bahan.all())
        return total_bahan + self.biaya_tenaga_kerja + self.biaya_listrik

    @property
    def laba(self):
        return self.harga_jual_akhir - self.total_modal

    @property
    def laba_persen(self):
        if self.harga_jual_akhir > 0:
            return (self.laba / self.harga_jual_akhir) * 100
        return 0

    def __str__(self):
        return f"{self.kode_produk} - {self.nama_produk}"


class HargaJualBahan(models.Model):
    harga_jual = models.ForeignKey(HargaJual, on_delete=models.CASCADE, related_name='list_bahan')
    barang = models.ForeignKey('List_Stok', on_delete=models.CASCADE)
    
    harga_stok_terpilih = models.ForeignKey('HargaStok', on_delete=models.RESTRICT)

    def __str__(self):
        return f"Bahan: {self.barang.nama_barang} di {self.harga_jual.nama_produk}"
    
class ArusStok(models.Model):
    JENIS_ARUS_CHOICES = [
        ('Pembelian', 'Pembelian (Stok Masuk)'),
        ('Pemakaian', 'Pemakaian (Stok Keluar)'),
    ]
    tanggal = models.DateTimeField(default=timezone.now)
    jenis_arus = models.CharField(max_length=20, choices=JENIS_ARUS_CHOICES)
    barang = models.ForeignKey('List_Stok', on_delete=models.CASCADE, related_name='arus_stok')
    qty_arus = models.IntegerField(default=0)
    keterangan_arus = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.jenis_arus} - {self.barang.nama_barang} ({self.qty_arus})"
    
class OrderUtama(models.Model):
    STATUS_CHOICES = [
        ('order', 'Order (Antrean)'),
        ('desain', 'Proses Desain'),
        ('produksi', 'Proses Produksi/Cetak'),
        ('selesai', 'Selesai'),
        ('diambil', 'Sudah Diambil'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='order', verbose_name="Status Order")
    no_order = models.CharField(max_length=50, unique=True, verbose_name="No Order", editable=False)
    tgl_order = models.DateTimeField(default=timezone.now, verbose_name="Tanggal Order")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name="Customer")
    nama_order = models.CharField(max_length=255, verbose_name="Nama Order / Judul Project")
    total_harga = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Total Harga")
    uang_muka = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Uang Muka (DP)")
    sisa_bayar = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Sisa Pembayaran")
    keterangan = models.TextField(blank=True, null=True, verbose_name="Keterangan")

    def save(self, *args, **kwargs):
        if not self.no_order:
            sekarang = datetime.now()
            tahun_bulan = sekarang.strftime('%Y%m') 
            order_terakhir = OrderUtama.objects.filter(
                no_order__contains=f"ORD-{tahun_bulan}-"
            ).order_by('-no_order').first()

            if order_terakhir:
                nomor_terakhir_str = order_terakhir.no_order.split('-')[-1]
                nomor_baru = int(nomor_terakhir_str) + 1
            else:
                nomor_baru = 1
            self.no_order = f"ORD-{tahun_bulan}-{str(nomor_baru).zfill(3)}"
            
        super(OrderUtama, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.no_order} - {self.nama_order}"

    class Meta:
        verbose_name_plural = "Data Order Utama"

class OrderDetail(models.Model):
    order_utama = models.ForeignKey(OrderUtama, on_delete=models.CASCADE, related_name='items')
    nama_pesanan = models.CharField(max_length=255, help_text="Nama cetakan/job, misal: Banner Warung Pecel")
    nama_item = models.CharField(max_length=255, help_text="Nama produk dari tabel harga_jual, misal: BANNER OUTDOOR")
    kode_item = models.CharField(max_length=50, blank=True, null=True, help_text="Kode barang/bahan, misal: 0500900001")  
    qty = models.IntegerField(default=1)
    panjang = models.DecimalField(max_digits=10, decimal_places=2, default=1.00, help_text="Dalam meter")
    lebar = models.DecimalField(max_digits=10, decimal_places=2, default=1.00, help_text="Dalam meter")
    harga_dasar = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Harga modal/beli bahan")
    harga_jual = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Harga jual per meter/satuan")
    jasa_desain = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    biaya_lain = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    keterangan = models.TextField(blank=True, null=True, help_text="Catatan finishing: mata ayam, lipat pres, dll")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_utama.no_order} - {self.nama_pesanan} ({self.nama_item})"

    class Meta:
        verbose_name = "Order Detail"
        verbose_name_plural = "Order Detail"