from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Max, Sum
from django.http import JsonResponse
from .models import Suplier, Customer,List_Stok,JenisBarang, HargaStok, HargaJual, HargaJualBahan, ArusStok, OrderUtama, OrderDetail, PiutangPelanggan, CicilanPiutang, Transaksi, Hutang, Kegiatan, StokOpname
from django.db import transaction
from django.utils import timezone
from decimal import Decimal,ROUND_HALF_UP
import json
from datetime import datetime
from django.core.paginator import Paginator

def login_view(request):

    # default user   
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(username="admin", password="030504", email=None)

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            login(request, user)
            return redirect('home')   
        else:
            messages.error(request, "Username atau Password salah!")
            
    return render(request, 'inventory/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

# ========================Stok========================
@login_required(login_url='login')
def list_stok(request):
    if request.method == "POST":
        v_nama = request.POST.get('nama_barang')
        v_satuan = request.POST.get('satuan')
        v_ukuran = request.POST.get('ukuran')
        v_keterangan = request.POST.get('keterangan')
        v_jenis_id = request.POST.get('jenis')

        if not v_nama or not v_jenis_id:
            messages.error(request, "Gagal! Nama dan Jenis Barang wajib diisi.")
            return redirect('list_stok')

        obj_jenis = JenisBarang.objects.get(id=v_jenis_id)
        nama_jenis = obj_jenis.nama.upper()
        prefix = nama_jenis[0]
        
        bentrok = JenisBarang.objects.filter(nama__istartswith=prefix).exclude(id=v_jenis_id).exists()
        if bentrok:
            prefix = nama_jenis[:2]

        nomor = 1
        while True:
            v_kode = f"{prefix}-{str(nomor).zfill(3)}"
            if not List_Stok.objects.filter(kode_barang=v_kode).exists():
                break 
            nomor += 1

        List_Stok.objects.create(
            kode_barang = v_kode,
            nama_barang = v_nama,
            jenis_id = v_jenis_id,
            satuan = v_satuan,
            ukuran = v_ukuran,
            keterangan = v_keterangan,
            qty = 0
        )
        messages.success(request, f"Barang {v_nama} berhasil ditambahkan dengan kode {v_kode}!")
        return redirect('list_stok')

    tab_aktif = request.GET.get('tab', 'list')
    context = {
        'tab_aktif': tab_aktif,
        'semua_jenis': JenisBarang.objects.all(),
    }
    
    if tab_aktif == 'list':
        query = request.GET.get('search')
        
        if query:
            stok = List_Stok.objects.filter(
                Q(nama_barang__icontains=query) | 
                Q(kode_barang__icontains=query) |
                Q(jenis__nama__icontains=query)
            ).select_related('jenis').order_by('id')
        else:
            stok = List_Stok.objects.all().select_related('jenis').order_by('id')
            
        for s in stok:
            if s.nama_barang:
                s.nama_barang = s.nama_barang.replace('\r', '').replace('\n', ' ').replace("'", "\\'")
            if s.keterangan:
                s.keterangan = s.keterangan.replace('\r', '').replace('\n', ' ').replace("'", "\\'")
            if s.ukuran:
                s.ukuran = s.ukuran.replace('\r', '').replace('\n', ' ').replace("'", "\\'")
        
        total_qty_data = stok.aggregate(Sum('qty'))['qty__sum']
        total_stok = int(total_qty_data) if total_qty_data else 0 
        barang_terbanyak = stok.order_by('-qty').first() 
        
        if barang_terbanyak and barang_terbanyak.qty > 0:
            pemakaian_info = f"{barang_terbanyak.nama_barang}"
        else:
            pemakaian_info = "-"
            
        context.update({
            'stok_barang': stok,
            'query': query,
            'total_seluruh_stok': total_stok,
            'pemakaian_terbanyak': pemakaian_info,
        })
        
    elif tab_aktif == 'arus':
        arus_stok_list = ArusStok.objects.all().select_related('barang').order_by('-tanggal')
        semua_barang = List_Stok.objects.all().order_by('nama_barang')
        semua_suplier = []
        try:
            semua_suplier = Suplier.objects.all().order_by('nama_suplier')
        except Exception:
            pass
        context.update({
            'arus_stok_list': arus_stok_list,
            'semua_barang': semua_barang,
            'semua_suplier': semua_suplier,
        })
        
    elif tab_aktif == 'opname':
        context.update({
            'data_opname_list': [], 
        })
        
    return render(request, 'inventory/list_stok.html', context)

def edit_stok(request):
    if request.method == "POST":
        v_id = request.POST.get('id_barang')
        v_nama = request.POST.get('nama_barang')
        v_satuan = request.POST.get('satuan')
        v_ukuran = request.POST.get('ukuran') 
        v_keterangan = request.POST.get('keterangan')
        v_jenis_id = request.POST.get('jenis')

        barang = List_Stok.objects.get(id=v_id)
        
        old_prefix = barang.nama_barang[:2].upper()
        new_prefix = v_nama[:2].upper()

        if old_prefix != new_prefix:
            nomor = 1
            while True:
                v_kode_baru = f"{new_prefix}-{str(nomor).zfill(3)}"
                if not List_Stok.objects.filter(kode_barang=v_kode_baru).exists():
                    barang.kode_barang = v_kode_baru
                    break
                nomor += 1
        
        barang.nama_barang = v_nama
        barang.jenis_id = v_jenis_id 
        barang.satuan = v_satuan
        barang.ukuran = v_ukuran
        barang.keterangan = v_keterangan
        barang.save()
        
        return redirect('list_stok')
    
def tambah_jenis(request):
    if request.method == "POST":
        nama_jenis = request.POST.get('nama_jenis')
        if nama_jenis:
            jenis_baru, created = JenisBarang.objects.get_or_create(nama=nama_jenis)
            if created:
                return JsonResponse({
                    'status': 'success',
                    'id': jenis_baru.id,
                    'nama': jenis_baru.nama
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Jenis sudah ada'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def hapus_stok(request, id):
    barang = get_object_or_404(List_Stok, id=id)
    barang.delete()
    return redirect('list_stok')
    
# ======================Customer======================
def data_customer(request):
    if request.method == "POST":
        v_nama = request.POST.get('nama_customer')
        v_alamat = request.POST.get('alamat')
        v_telp = request.POST.get('telepon')
        v_email = request.POST.get('email')

        jumlah_data = Customer.objects.count() + 1
        v_kode = f"C-{str(jumlah_data).zfill(3)}"

        Customer.objects.create(
            kode_customer = v_kode,
            nama_customer= v_nama,
            alamat = v_alamat,
            telepon = v_telp,
            email = v_email,
        )

        return redirect('data_customer') 

    tgl_mulai = request.GET.get('start_date')
    tgl_akhir = request.GET.get('end_date')
    query = request.GET.get('search')

    semua_customer = Customer.objects.all()


    if tgl_mulai and tgl_akhir:
        semua_customer = semua_customer.filter(created_at__date__range=[tgl_mulai, tgl_akhir])

    if query:
        semua_customer = semua_customer.filter(
            Q(nama_customer__icontains=query) | Q(kode_customer__icontains=query)
        )

    max_nominal = semua_customer.aggregate(Max('total_transaksi'))['total_transaksi__max']    
    
    if max_nominal and max_nominal > 0:
        top_cust = semua_customer.filter(total_transaksi=max_nominal).first()
        penjualan_terbanyak = f"{top_cust.nama_customer} (Rp {max_nominal})"
    else:
        penjualan_terbanyak = "Tidak ada data"

    return render(request, 'inventory/data_customer.html', {
        'customer': semua_customer.order_by('id'),
        'query': query,
        'start_date': tgl_mulai,
        'end_date': tgl_akhir,
        'customer_terbanyak': penjualan_terbanyak 
    })

def edit_customer(request):
    if request.method == "POST":
        v_id = request.POST.get('id_customer')
        v_nama = request.POST.get('nama_customer')
        v_alamat = request.POST.get('alamat')
        v_telp = request.POST.get('telepon')
        v_email = request.POST.get('email')

        customer = Customer.objects.get(id=v_id)
        customer.nama_customer = v_nama
        customer.alamat = v_alamat
        customer.telepon = v_telp
        customer.email = v_email
        customer.save()

        return redirect('data_customer')
    
def hapus_customer(request, pk):
    try:
        customer = Customer.objects.get(id=pk)
        nama_cust = customer.nama_customer
        customer.delete()
        messages.success(request, f"Berhasil menghapus data customer '{nama_cust}'.")
    except Customer.DoesNotExist:
        messages.error(request, "Gagal! Data customer tidak ditemukan.")
    except Exception as e:
        messages.error(request, f"Terjadi kesalahan sistem: {str(e)}")
        
    return redirect('data_customer')

# ======================suplier======================
def data_suplier(request):
    if request.method == "POST":
        v_nama = request.POST.get('nama_suplier')
        v_alamat = request.POST.get('alamat')
        v_telp = request.POST.get('telepon')
        v_email = request.POST.get('email')

        jumlah_data = Suplier.objects.count() + 1
        v_kode = f"S-{str(jumlah_data).zfill(3)}"

        Suplier.objects.create(
            kode_suplier = v_kode,
            nama_suplier = v_nama,
            alamat = v_alamat,
            telepon = v_telp,
            email = v_email
        )

        return redirect('data_suplier') 
    query = request.GET.get('search') 
    
    if query:
        semua_suplier = Suplier.objects.filter(
            Q(nama_suplier__icontains=query) | 
            Q(kode_suplier__icontains=query)
        ).order_by('id')
    else:
        semua_suplier = Suplier.objects.all().order_by('id')

    return render(request, 'inventory/data_suplier.html', {
        'supliers': semua_suplier, 
        'query': query
    })

def edit_suplier(request):
    if request.method == "POST":
        v_id = request.POST.get('id_suplier')
        v_nama = request.POST.get('nama_suplier')
        v_alamat = request.POST.get('alamat')
        v_telp = request.POST.get('telepon')
        v_email = request.POST.get('email')

        suplier = Suplier.objects.get(id=v_id)
        suplier.nama_suplier = v_nama
        suplier.alamat = v_alamat
        suplier.telepon = v_telp
        suplier.email = v_email
        suplier.save()

        return redirect('data_suplier')

def hapus_suplier(request, pk):
    try:
        suplier = Suplier.objects.get(id=pk)
        nama_sup = suplier.nama_suplier
        suplier.delete()
        messages.success(request, f"Berhasil menghapus data supplier '{nama_sup}'.")
    except Suplier.DoesNotExist:
        messages.error(request, "Gagal! Data supplier tidak ditemukan.")
    except Exception as e:
        messages.error(request, f"Terjadi kesalahan sistem: {str(e)}")
        
    return redirect('data_suplier')

# ========================HargaStok==========================
def daftar_harga(request):
    if request.method == "POST":
        barang_id = request.POST.get('barang')
        suplier_id = request.POST.get('suplier') 
        harga = request.POST.get('harga_satuan')

        HargaStok.objects.create(
            barang_id=barang_id,
            suplier_id=suplier_id,
            harga_satuan=harga
        )
        return redirect('daftar_harga')
    query = request.GET.get('search', '')
    
    data_harga_stok = HargaStok.objects.all().select_related('barang', 'suplier')

    if query:
        data_harga_stok = data_harga_stok.filter(
            Q(barang__nama_barang__icontains=query) |
            Q(barang__kode_barang__icontains=query)
        )
    
    data_harga_stok = data_harga_stok.order_by('-id')
    termahal_obj = HargaStok.objects.all().select_related('barang').order_by('-harga_satuan').first()
    termurah_obj = HargaStok.objects.all().select_related('barang').order_by('harga_satuan').first()
    stok_termahal = f"{termahal_obj.barang.nama_barang}" if termahal_obj else "-"
    stok_termurah = f"{termurah_obj.barang.nama_barang}" if termurah_obj else "-"
    pilihan_barang = List_Stok.objects.all().select_related('jenis').order_by('nama_barang')
    barang_data = []

    # 2. Ambil data dari List_Stok (Bahan Baku)
    pilihan_barang = List_Stok.objects.all().order_by('nama_barang')
    for barang in pilihan_barang:
        stok_termahal = HargaStok.objects.filter(barang_id=barang.id).order_by('-harga_satuan').first()
        barang_data.append({
            'id': str(barang.id),
            'nama_tampilan': barang.nama_barang, 
            'harga': float(stok_termahal.harga_satuan) if stok_termahal else 0,
        })

    # 3. Ambil data dari HargaJual (Produk Jadi)
    # PASTIKAN bagian ini tidak terlewat dan tidak dibungkus 'if' yang salah
    semua_jual = HargaJual.objects.all()
    for p in semua_jual:
        barang_data.append({
            'id': f"jual_{p.id}",
            'nama_tampilan': p.nama_produk, 
            'harga': float(p.harga_jual_akhir),
        })

    # 4. Pastikan barang_data dikirim ke context
    context = {
        'barang_data': barang_data,
        'harga_list': data_harga_stok, 
        'barang_data': barang_data,     
        'semua_suplier': Suplier.objects.all(),        
        'semua_barang': pilihan_barang, 
        'harga_jual_list': HargaJual.objects.prefetch_related('list_bahan__barang', 'list_bahan__harga_stok_terpilih').all().order_by('id'),
        'stok_termahal': stok_termahal,
        'stok_termurah': stok_termurah,
        'query': query,
    }
    return render(request, 'inventory/daftar_harga.html', context)

def edit_harga_stok(request):
    if request.method == "POST":
        id_harga = request.POST.get('id_harga')
        id_barang = request.POST.get('barang')
        id_suplier = request.POST.get('suplier')
        harga_satuan = request.POST.get('harga_satuan')
        harga_stok = get_object_or_404(HargaStok, id=id_harga)
        harga_stok.barang_id = id_barang
        harga_stok.suplier_id = id_suplier
        harga_stok.harga_satuan = harga_satuan
        harga_stok.save()
        return redirect('daftar_harga')

def hapus_harga(request, id):
    harga_entry = HargaStok.objects.get(id=id)
    harga_entry.delete()
    return redirect('daftar_harga')

# =====================harga jual=====================
def daftar_harga_jual(request):
    if request.method == "POST":
        if 'nama_produk' in request.POST:
            v_nama_produk = request.POST.get('nama_produk')
            v_tenaga = float(request.POST.get('biaya_tenaga') or 0)
            v_listrik = float(request.POST.get('biaya_listrik') or 0)
            v_keterangan = request.POST.get('keterangan_produk')
            v_jual = float(request.POST.get('harga_jual_akhir') or 0)
            id_bahan_terpilih = request.POST.getlist('bahan_terpilih')
            print("DEBUG: BAHAN TERPILIH:", id_bahan_terpilih)

            if v_nama_produk and id_bahan_terpilih:
                produk_baru = HargaJual.objects.create(
                    nama_produk=v_nama_produk,
                    biaya_tenaga_kerja=v_tenaga,
                    biaya_listrik=v_listrik,
                    keterangan_produk=v_keterangan,
                    harga_jual_akhir=v_jual
                )

                for item_id in id_bahan_terpilih:
                    if not item_id: continue
                    
                    if item_id.startswith('jual_'):
                        id_asli = item_id.replace('jual_', '')
                        # Gunakan cara ini agar kolom terisi secara eksplisit
                        jual_bahan = HargaJualBahan(harga_jual=produk_baru)
                        jual_bahan.produk_jadi_terpilih_id = int(id_asli) # Pastikan nama kolom ini benar sesuai database
                        jual_bahan.barang = None
                        jual_bahan.harga_stok_terpilih = None
                        jual_bahan.save()
                        
                    else:
                        stok_termahal = HargaStok.objects.filter(barang_id=item_id).order_by('-harga_satuan').first()
                        if stok_termahal:
                            jual_bahan = HargaJualBahan(harga_jual=produk_baru)
                            jual_bahan.barang_id = int(item_id)
                            jual_bahan.harga_stok_terpilih = stok_termahal
                            jual_bahan.produk_jadi_terpilih = None
                            jual_bahan.save()
                return redirect('/daftar_harga/#harga-jual')
        
        # Else jika POST untuk menambah stok (barang, suplier, harga_satuan)
        else:
            barang_id = request.POST.get('barang')
            suplier_id = request.POST.get('suplier') 
            harga = request.POST.get('harga_satuan')
            if barang_id and suplier_id and harga:
                HargaStok.objects.create(barang_id=barang_id, suplier_id=suplier_id, harga_satuan=harga)
            return redirect('daftar_harga')

    # --- BAGIAN GET / TAMPILAN ---
    query_jual = request.GET.get('search_jual', '')
    harga_jual_query = HargaJual.objects.prefetch_related(
        'list_bahan__barang', 
        'list_bahan__harga_stok_terpilih', 
        'list_bahan__produk_jadi_terpilih'
    ).all()

    if query_jual:
        harga_jual_query = harga_jual_query.filter(
            Q(nama_produk__icontains=query_jual) |
            Q(kode_produk__icontains=query_jual)
        )
    
    harga_jual_list = harga_jual_query.order_by('id')
    
    # Statistik
    jual_termahal_obj = HargaJual.objects.all().order_by('-harga_jual_akhir').first()
    jual_termurah_obj = HargaJual.objects.all().order_by('harga_jual_akhir').first()

    produk_termahal = f"{jual_termahal_obj.nama_produk} (Rp {int(jual_termahal_obj.harga_jual_akhir):,})" if jual_termahal_obj else "-"
    produk_termurah = f"{jual_termurah_obj.nama_produk} (Rp {int(jual_termurah_obj.harga_jual_akhir):,})" if jual_termurah_obj else "-"

    # Data untuk Datalist (Stok + Produk Jadi)
    data_harga_stok = HargaStok.objects.all().select_related('barang', 'suplier').order_by('-id')
    pilihan_barang = List_Stok.objects.all().select_related('jenis').order_by('nama_barang')
    barang_data = []

    # 2. Ambil data dari List_Stok (Bahan Baku)
    pilihan_barang = List_Stok.objects.all().order_by('nama_barang')
    for barang in pilihan_barang:
        stok_termahal = HargaStok.objects.filter(barang_id=barang.id).order_by('-harga_satuan').first()
        barang_data.append({
            'id': str(barang.id),
            'nama_tampilan': barang.nama_barang, 
            'harga': float(stok_termahal.harga_satuan) if stok_termahal else 0,
        })

    # 3. Ambil data dari HargaJual (Produk Jadi)
    # PASTIKAN bagian ini tidak terlewat dan tidak dibungkus 'if' yang salah
    semua_jual = HargaJual.objects.all()
    for p in semua_jual:
        barang_data.append({
            'id': f"jual_{p.id}",
            'nama_tampilan': p.nama_produk, 
            'harga': float(p.harga_jual_akhir),
        })

    # 4. Pastikan barang_data dikirim ke context
    context = {
        'barang_data': barang_data,
        'harga_list': data_harga_stok, 
        'semua_suplier': Suplier.objects.all(),        
        'semua_barang': pilihan_barang, 
        'harga_jual_list': harga_jual_list,
        'produk_termahal': produk_termahal,
        'produk_termurah': produk_termurah,
        'query_jual': query_jual,
    }
    return render(request, 'inventory/daftar_harga.html', context)

def edit_harga_jual(request):
    if request.method == "POST":
        id_jual = request.POST.get('id_harga_jual')
        v_nama_produk = request.POST.get('nama_produk')
        v_tenaga = float(request.POST.get('biaya_tenaga') or 0)
        v_listrik = float(request.POST.get('biaya_listrik') or 0)
        v_keterangan = request.POST.get('keterangan_produk')
        v_jual = float(request.POST.get('harga_jual_akhir') or 0)
        id_bahan_terpilih = request.POST.getlist('bahan_terpilih')

        try:
            produk = HargaJual.objects.get(id=id_jual)
            produk.nama_produk = v_nama_produk
            produk.biaya_tenaga_kerja = v_tenaga
            produk.biaya_listrik = v_listrik
            produk.keterangan_produk = v_keterangan
            produk.harga_jual_akhir = v_jual
            produk.save()

            # Hapus relasi lama
            HargaJualBahan.objects.filter(harga_jual=produk).delete()

            # Simpan relasi baru
            for item_id in id_bahan_terpilih:
                if not item_id: continue
                
                if item_id.startswith('jual_'):
                    id_asli = item_id.replace('jual_', '')
                    # MENGGUNAKAN FIELD YANG BENAR
                    HargaJualBahan.objects.create(
                        harga_jual=produk,
                        produk_jadi_terpilih_id=int(id_asli),
                        barang=None,
                        harga_stok_terpilih=None
                    )
                else:
                    stok_termahal = HargaStok.objects.filter(barang_id=item_id).order_by('-harga_satuan').first()
                    if stok_termahal:
                        HargaJualBahan.objects.create(
                            harga_jual=produk,
                            barang_id=int(item_id),
                            harga_stok_terpilih=stok_termahal,
                            produk_jadi_terpilih=None
                        )
        except HargaJual.DoesNotExist:
            pass

        return redirect('/daftar_harga/#harga-jual')
    return redirect('/daftar_harga/#harga-jual')

def hapus_harga_jual(request, id):
    hj = HargaJual.objects.get(id=id)
    hj.delete()
    return redirect('/daftar_harga/#harga-jual')

# ======================== ARUS STOK ========================
def log_arus_stok(request):
    query = request.GET.get('search', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_filter = request.GET.get('status', 'Semua')
    hari_ini = timezone.now().date()
    
    arus_stok_list = ArusStok.objects.all().select_related('barang', 'suplier')

    if start_date and end_date:
        arus_stok_list = arus_stok_list.filter(tanggal__date__range=[start_date, end_date])
    else:
        arus_stok_list = arus_stok_list.filter(tanggal__date=hari_ini)
        start_date = hari_ini.strftime('%Y-%m-%d')
        end_date = hari_ini.strftime('%Y-%m-%d')

    if query:
        arus_stok_list = arus_stok_list.filter(
            Q(barang__nama_barang__icontains=query) |
            Q(barang__kode_barang__icontains=query)
        )

    total_masuk_data = arus_stok_list.filter(jenis_arus__iexact='Pembelian').aggregate(Sum('qty_arus'))['qty_arus__sum']
    total_masuk = int(total_masuk_data) if total_masuk_data else 0
    total_keluar_data = arus_stok_list.filter(jenis_arus__iexact='Pemakaian').aggregate(Sum('qty_arus'))['qty_arus__sum']
    total_keluar = int(total_keluar_data) if total_keluar_data else 0

    if status_filter and status_filter != 'Semua':
        if status_filter == 'masuk':
            arus_stok_list = arus_stok_list.filter(jenis_arus__iexact='Pembelian')
        elif status_filter == 'keluar':
            arus_stok_list = arus_stok_list.filter(jenis_arus__iexact='Pemakaian')

    arus_stok_list = arus_stok_list.order_by('-tanggal')

    baris_tabel_gabung = []
    nota_pembelian_terproses = set() 

    for arus in arus_stok_list:
        if arus.jenis_arus == 'Pemakaian':
            baris_tabel_gabung.append({
                'id': arus.id,
                'tanggal': arus.tanggal,
                'jenis_arus': arus.jenis_arus,
                'kode_barang_tampil': arus.barang.kode_barang if arus.barang else '-',
                'nama_barang_tampil': arus.barang.nama_barang if arus.barang else '-',
                'qty_tampil': f"{arus.qty_arus} Pcs",
                'keterangan': arus.keterangan_arus or '-',
                'suplier_nama': '-',
                'harga': 0,
                'pembayaran': 0,
                'sisa': 0,
                'tenggat': '-'
            })
        elif arus.jenis_arus == 'Pembelian':
            key_nota = f"{arus.suplier_id}_{arus.keterangan_arus}_{arus.tanggal.strftime('%Y%m%d%H%M%S')}"
            
            if key_nota not in nota_pembelian_terproses:
                nota_pembelian_terproses.add(key_nota)
                
                items_serumpun = arus_stok_list.filter(
                    suplier=arus.suplier,
                    keterangan_arus=arus.keterangan_arus,
                    jenis_arus='Pembelian',
                    tanggal=arus.tanggal
                )
                
                total_qty_nota = sum(item.qty_arus for item in items_serumpun)
                total_biaya_nota = sum(item.qty_arus * item.harga_satuan for item in items_serumpun)
                total_bayar_nota = sum(item.pembayaran for item in items_serumpun)
                total_sisa_nota = total_biaya_nota - total_bayar_nota
                
                jumlah_item = items_serumpun.count()
                item_pertama = items_serumpun.first() 
                
                if item_pertama and item_pertama.barang:
                    kode_barang_tampil = item_pertama.barang.kode_barang
                    nama_barang_tampil = item_pertama.barang.nama_barang
                    
                    if jumlah_item > 1:
                        nama_barang_tampil += f" (+{jumlah_item - 1} item lainnya)"
                else:
                    kode_barang_tampil = "-"
                    nama_barang_tampil = "-"
                
                baris_tabel_gabung.append({
                    'id': arus.id,
                    'tanggal': arus.tanggal,
                    'jenis_arus': arus.jenis_arus,
                    'kode_barang_tampil': kode_barang_tampil,
                    'nama_barang_tampil': nama_barang_tampil, 
                    'qty_tampil': f"{total_qty_nota} Pcs",      
                    'keterangan': arus.keterangan_arus or '-',
                    'suplier_nama': arus.suplier.nama_suplier if arus.suplier else '-',
                    'harga': total_biaya_nota,
                    'pembayaran': total_bayar_nota,
                    'sisa': total_sisa_nota if total_sisa_nota > 0 else 0,
                    'tenggat': arus.tenggat_pembayaran.strftime('%Y-%m-%d') if arus.tenggat_pembayaran else '-'
                })

    semua_barang = List_Stok.objects.all().order_by('nama_barang')
    semua_suplier = Suplier.objects.all().order_by('nama_suplier')

    context = {
        'arus_stok_list': baris_tabel_gabung,  
        'semua_barang': semua_barang,
        'semua_suplier': semua_suplier,
        'query': query,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'status_aktif': status_filter,
        'card_masuk': total_masuk,
        'card_keluar': total_keluar,
    }
    return render(request, 'inventory/arus_stok.html', context)

def tambah_arus_stok(request):
    if request.method == "POST":
        v_jenis_arus = request.POST.get('jenis_arus')      
        v_keterangan = request.POST.get('keterangan_arus')
        v_suplier_id = request.POST.get('suplier')       
        v_pembayaran = request.POST.get('pembayaran')
        v_tenggat = request.POST.get('tenggat_pembayaran')
        v_tanggal_custom = request.POST.get('tanggal')
        v_no_invoice = request.POST.get('no_invoice') 

        try:
            with transaction.atomic():
                waktu_transaksi = v_tanggal_custom if v_tanggal_custom else timezone.now()
                
                if v_jenis_arus == 'Pemakaian':
                    v_barang_id = request.POST.get('barang')
                    v_qty = request.POST.get('qty_arus')
                    
                    if not v_barang_id or not v_qty:
                        raise ValueError("Barang dan kuantitas pemakaian wajib diisi.")
                        
                    barang = List_Stok.objects.get(id=v_barang_id)
                    qty_arus = int(v_qty)
                    
                    if int(barang.qty) < qty_arus:
                        raise ValueError(f"Stok '{barang.nama_barang}' tidak mencukupi.")
                    
                    barang.qty = int(barang.qty) - qty_arus
                    barang.save()

                    ArusStok.objects.create(
                        no_invoice=v_no_invoice,
                        tanggal=waktu_transaksi,
                        barang=barang,
                        jenis_arus=v_jenis_arus,
                        qty_arus=qty_arus,
                        keterangan_arus=v_keterangan,
                        suplier=None,
                        harga_satuan=0,
                        pembayaran=0,
                        tenggat_pembayaran=None
                    )
                    messages.success(request, f"Berhasil mencatat pemakaian barang.")

                elif v_jenis_arus == 'Pembelian':
                    arr_barang_id = request.POST.getlist('arr_barang_id[]')
                    arr_qty = request.POST.getlist('arr_qty[]')
                    arr_harga = request.POST.getlist('arr_harga[]')

                    if not arr_barang_id or not v_suplier_id:
                        raise ValueError("Supplier dan minimal 1 item barang pembelian wajib diisi.")

                    suplier_obj = Suplier.objects.get(id=v_suplier_id)
                    v_pembayaran_bersih = v_pembayaran.strip() if v_pembayaran else ""
                    pembayaran_total = Decimal(v_pembayaran_bersih) if v_pembayaran_bersih else Decimal('0')
                    tenggat_pembayaran = v_tenggat if v_tenggat else None
                    grand_total_pembelian = Decimal('0')
                    list_data_item = []

                    for i in range(len(arr_barang_id)):
                        b_id = arr_barang_id[i]
                        qty = int(arr_qty[i])
                        harga = Decimal(arr_harga[i] or 0)
                        
                        if b_id:
                            barang_obj = List_Stok.objects.get(id=b_id)
                            grand_total_pembelian += (qty * harga)
                            list_data_item.append({
                                'obj_barang': barang_obj,
                                'qty': qty,
                                'harga': harga
                            })

                    for item in list_data_item:
                        brg = item['obj_barang']
                        q_arus = item['qty']
                        h_satuan = item['harga']
                        total_item = q_arus * h_satuan

                        if pembayaran_total >= grand_total_pembelian:
                            item_pembayaran = total_item
                        else:
                            if grand_total_pembelian > 0:
                                item_pembayaran = (pembayaran_total * total_item) / grand_total_pembelian
                                item_pembayaran = item_pembayaran.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            else:
                                item_pembayaran = Decimal('0')

                        brg.qty = int(brg.qty) + q_arus
                        brg.save()

                        ArusStok.objects.create(
                            no_invoice=v_no_invoice, 
                            tanggal=waktu_transaksi,
                            barang=brg,
                            jenis_arus=v_jenis_arus,
                            qty_arus=q_arus,
                            keterangan_arus=v_keterangan,
                            suplier=suplier_obj,
                            harga_satuan=h_satuan,
                            pembayaran=item_pembayaran,
                            tenggat_pembayaran=tenggat_pembayaran
                        )

                    messages.success(request, f"Berhasil memborong {len(list_data_item)} item barang dari supplier {suplier_obj.nama_suplier}.")

        except Exception as e:
            import traceback
            traceback.print_exc() 
            
            messages.error(request, f"Gagal memproses transaksi: {str(e)}")

    return redirect('log_arus_stok')

def edit_arus_stok(request, pk):
    if request.method == "POST":
        try:
            arus = ArusStok.objects.get(id=pk)
            v_keterangan = request.POST.get('keterangan_arus')
            v_suplier_id = request.POST.get('suplier')
            v_harga = request.POST.get('harga_satuan')
            
            v_pembayaran = request.POST.get('pembayaran')
            v_tenggat = request.POST.get('tenggat_pembayaran')

            arus.keterangan_arus = v_keterangan

            if arus.jenis_arus == 'Pembelian':
                arus.harga_satuan = float(v_harga or 0)
                arus.pembayaran = float(v_pembayaran or 0)
                arus.tenggat_pembayaran = v_tenggat if v_tenggat else None
                
                if v_suplier_id:
                    arus.suplier = Suplier.objects.get(id=v_suplier_id)
                else:
                    arus.suplier = None

            arus.save()
            messages.success(request, f"Berhasil memperbarui data riwayat arus stok.")

        except ArusStok.DoesNotExist:
            messages.error(request, "Gagal! Data transaksi tidak ditemukan.")
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan sistem: {str(e)}")

    return redirect('log_arus_stok')

def detail_arus_stok(request, pk):
    try:
        target_arus = ArusStok.objects.get(id=pk)
        
        if target_arus.jenis_arus == 'Pemakaian':
            data = {
                'jenis_arus': 'Pemakaian',
                'barang_nama': target_arus.barang.nama_barang if target_arus.barang else '-',
                'qty_arus': target_arus.qty_arus,
                'keterangan_arus': target_arus.keterangan_arus or '-',
            }
            return JsonResponse({'status': 'success', 'data': data})
        
        semua_item_nota = ArusStok.objects.filter(
            suplier=target_arus.suplier,
            keterangan_arus=target_arus.keterangan_arus,
            jenis_arus='Pembelian',
            tanggal=target_arus.tanggal 
        ).select_related('barang')

        grand_total = 0
        total_pembayaran = 0
        items_list = []

        for item in semua_item_nota:
            total_baris = float(item.qty_arus) * float(item.harga_satuan)
            grand_total += total_baris
            total_pembayaran += float(item.pembayaran or 0)
            
            items_list.append({
                'barang_nama': item.barang.nama_barang if item.barang else '-',
                'qty_arus': item.qty_arus,
                'harga_satuan': float(item.harga_satuan),
                'total_baris': total_baris
            })

        sisa_hutang = grand_total - total_pembayaran

        data = {
            'jenis_arus': 'Pembelian',
            'suplier_nama': target_arus.suplier.nama_suplier if target_arus.suplier else '-',
            'keterangan_arus': target_arus.keterangan_arus or '-',
            'pembayaran': total_pembayaran,
            'sisa_hutang': sisa_hutang if sisa_hutang > 0 else 0,
            'tenggat_pembayaran': target_arus.tenggat_pembayaran.strftime('%Y-%m-%d') if target_arus.tenggat_pembayaran else '-',
            'items': items_list
        }

        return JsonResponse({'status': 'success', 'data': data})

    except ArusStok.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Data tidak ditemukan'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def hapus_arus_stok(request, pk):
    try:
        with transaction.atomic():
            arus = ArusStok.objects.get(id=pk)
            barang = arus.barang
            qty_arus = float(arus.qty_arus)

            if arus.jenis_arus == 'Pembelian':
                if float(barang.qty) < qty_arus:
                    messages.error(request, f"Gagal menghapus! Stok '{barang.nama_barang}' saat ini ({barang.qty}) tidak mencukupi jika dikurangi {qty_arus} dari pembatalan pembelian ini.")
                    return redirect('log_arus_stok')
                barang.qty = float(barang.qty) - qty_arus
            else:
                barang.qty = float(barang.qty) + qty_arus
                
            barang.save()
            arus.delete()
            
            messages.success(request, "Berhasil menghapus riwayat arus stok dan menyesuaikan ulang master stok barang.")

    except ArusStok.DoesNotExist:
        messages.error(request, "Gagal! Data riwayat arus stok tidak ditemukan.")
    except Exception as e:
        messages.error(request, f"Terjadi kesalahan sistem: {str(e)}")

    return redirect('log_arus_stok')


def ambil_harga_satuan(request):
    barang_id = request.GET.get('barang_id')
    suplier_id = request.GET.get('suplier_id')
    
    if barang_id and suplier_id:
        try:
            harga_obj = HargaStok.objects.get(barang_id=barang_id, suplier_id=suplier_id)
            return JsonResponse({'status': 'success', 'harga_satuan': float(harga_obj.harga_satuan)})
        except HargaStok.DoesNotExist:
            return JsonResponse({'status': 'not_found', 'harga_satuan': 0})
            
    return JsonResponse({'status': 'error', 'message': 'Parameter tidak lengkap'}, status=400)

#================================================Order================================================
def titik_uang(nilai_string):
    if not nilai_string or nilai_string == '':
        return 0.0
    clean_string = str(nilai_string).replace('.', '').replace(',', '.')
    try:
        return float(clean_string)
    except ValueError:
        return 0.0
def list_order(request):
    query = request.GET.get('search')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_filter = request.GET.get('status', 'Semua')
    
    # 💡 1. Tangkap parameter filter keaktifan baru (default: aktif)
    keaktifan_filter = request.GET.get('keaktifan', 'aktif')
    
    hari_ini = timezone.now().date()
    semua_order = OrderUtama.objects.all()

    # --- Filter Berdasarkan Tanggal ---
    if start_date and end_date:
        semua_order = semua_order.filter(tgl_order__date__range=[start_date, end_date])
    else:
        semua_order = semua_order.filter(tgl_order__date=hari_ini)
        start_date = hari_ini.strftime('%Y-%m-%d')
        end_date = hari_ini.strftime('%Y-%m-%d')
        
    # --- Filter Berdasarkan Search Bar ---
    if query:
        semua_order = semua_order.filter(
            Q(no_order__icontains=query) | 
            Q(nama_order__icontains=query) |
            Q(customer__nama_customer__icontains=query)
        )

    # 💡 2. LOGIKA BARU: Filter Keaktifan Data (Soft Delete) sebelum hitung data Card Ringkasan
    # Kita pisahkan data base pencarian untuk Card (hanya yang aktif) agar angka summary tetap akurat
    order_untuk_card = semua_order.filter(is_active=True)

    total_orderan = order_untuk_card.count()
    total_status_order = order_untuk_card.filter(status__iexact='order').count()
    total_status_proses = order_untuk_card.filter(status__iexact='proses').count()
    total_status_selesai = order_untuk_card.filter(status__iexact='selesai').count()
 
    # 💡 3. Terapkan filter keaktifan sesungguhnya ke QuerySet utama tabel
    if keaktifan_filter == 'aktif':
        semua_order = semua_order.filter(is_active=True)
    elif keaktifan_filter == 'tidak_aktif':
        semua_order = semua_order.filter(is_active=False)
    # Jika keaktifan_filter == 'semua', jalurnya dilewati (menampilkan aktif & dihapus sekaligus)

    # --- Filter Berdasarkan Status Pengerjaan ---
    if status_filter and status_filter != 'Semua':
        semua_order = semua_order.filter(status__iexact=status_filter)

    semua_order = semua_order.order_by('-id')

    return render(request, 'inventory/list_order.html', {
        'orders': semua_order,
        'query': query,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'status_aktif': status_filter,
        
        'keaktifan_aktif': keaktifan_filter, 
        
        'card_total': total_orderan,
        'card_order': total_status_order,
        'card_proses': total_status_proses,
        'card_selesai': total_status_selesai,
    })

def tambah_order(request):
    if request.method == "POST":
        customer_id = request.POST.get('customer_id')
        v_nama_order = request.POST.get('nama_order')
        v_keterangan = request.POST.get('keterangan', '')
        v_no_order = request.POST.get('no_order')
        v_status = request.POST.get('status', 'order')
        
        v_tgl_order = request.POST.get('tgl_order')
        if not v_tgl_order:
            v_tgl_order = timezone.now()

        v_total_harga = titik_uang(request.POST.get('total_harga', 0))
        v_uang_muka = titik_uang(request.POST.get('uang_muka', 0))
        v_sisa_bayar = titik_uang(request.POST.get('sisa_bayar', 0))
        
        items_json = request.POST.get('items_json')

        if not customer_id:
            messages.error(request, "Customer wajib dipilih!")
            return redirect('list_order')

        customer_obj = get_object_or_404(Customer, id=customer_id)
        
        try:
            order_utama = OrderUtama.objects.create(
                no_order=v_no_order,
                customer=customer_obj,
                nama_order=v_nama_order,
                status=v_status,
                keterangan=v_keterangan,
                total_harga=v_total_harga,
                uang_muka=v_uang_muka,   
                sisa_bayar=v_sisa_bayar,
                tgl_order=v_tgl_order 
            )
            
            if items_json:
                daftar_item = json.loads(items_json)
                for item in daftar_item:
                    OrderDetail.objects.create(
                        order_utama=order_utama,
                        nama_pesanan=item.get('nama_pesanan'),
                        nama_item=item.get('nama_item'),
                        kode_item=item.get('kode_item', '-'),
                        qty=int(item.get('qty') if str(item.get('qty')).isdigit() else 1),
                        panjang=float(item.get('panjang') if item.get('panjang') != '-' else 1.0),
                        lebar=float(item.get('lebar') if item.get('lebar') != '-' else 1.0),
                        harga_dasar=0.0,
                        harga_jual=float(item.get('harga_jual', 0) if item.get('harga_jual') != '-' else 0),
                        jasa_desain=0.0,
                        biaya_lain=0.0,
                        total=float(item.get('total', 0)),
                        keterangan=item.get('keterangan', '-')
                    )
                messages.success(request, f"Order {v_no_order} berhasil disimpan dengan seluruh itemnya!")
            else:
                messages.warning(request, f"Order {v_no_order} disimpan tanpa ada item pesanan.")
                
        except Exception as e:
            import traceback
            traceback.print_exc() 
            
            messages.error(request, f"Terjadi kesalahan saat menyimpan data: {str(e)}")
        
        return redirect('list_order')
    return redirect('list_order')

def cari_customer(request):
    term = request.GET.get('q', '') 
    customers = Customer.objects.filter(nama_customer__icontains=term)[:10]
    results = []
    for c in customers:
        results.append({
            'id': c.id,
            'nama': c.nama_customer,
            'kode': c.kode_customer if hasattr(c, 'kode_customer') else f"CUST-{c.id}",
            'alamat': c.alamat if c.alamat else '-',
            'telepon': c.telepon if c.telepon else '-'
        })
    return JsonResponse({'results': results}, safe=False)

def kode_order(request):
    sekarang = timezone.now()
    tahun_bulan = sekarang.strftime('%Y%m')
    prefix = f"ORD-{tahun_bulan}-"
    order_terakhir = OrderUtama.objects.filter(no_order__startswith=prefix).order_by('-no_order').first()
    if order_terakhir:
        nomor_terakhir_str = order_terakhir.no_order.split('-')[-1]
        nomor_baru = int(nomor_terakhir_str) + 1
    else:
        nomor_baru = 1
    next_no_order = f"{prefix}{str(nomor_baru).zfill(3)}"
    return JsonResponse({'next_no_order': next_no_order})

def cari_produk(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        produk_queryset = HargaJual.objects.filter(nama_produk__icontains=query)[:10]
        for produk in produk_queryset:
            results.append({
                'id': produk.id,
                'nama_produk': produk.nama_produk,
                'harga_jual': int(produk.harga_jual_akhir) if produk.harga_jual_akhir else 0,  
                'kode_barang': produk.kode_produk if produk.kode_produk else "PRD"
            })
    return JsonResponse({'results': results})

def get_order_items(request, order_id):
    order_utama = get_object_or_404(OrderUtama, id=order_id)
    items_queryset = OrderDetail.objects.filter(order_utama=order_utama)
    
    daftar_item = []
    for item in items_queryset:
        daftar_item.append({
            'kode_item': item.kode_item if item.kode_item else '-',
            'nama_item': item.nama_item,
            'nama_pesanan': item.nama_pesanan,
            'qty': item.qty,
            'panjang': float(item.panjang),
            'lebar': float(item.lebar),
            'harga_dasar': float(item.harga_dasar),
            'harga_jual': float(item.harga_jual),
            'jasa_desain': float(item.jasa_desain),
            'biaya_lain': float(item.biaya_lain),
            'total': float(item.total),
            'keterangan': item.keterangan if item.keterangan else ''
        })
        
    return JsonResponse({'items': daftar_item})

def edit_order(request, order_id):
    if request.method == "POST":
        order_utama = get_object_or_404(OrderUtama, id=order_id)
        
        try:
            customer_id = request.POST.get('customer_id')       
            nama_order = request.POST.get('nama_order')         
            status = request.POST.get('status')                 
            keterangan = request.POST.get('keterangan')         
            v_tgl_order = request.POST.get('tgl_order')  
            
            total_harga_raw = request.POST.get('total_harga', '0')
            uang_muka_raw = request.POST.get('uang_muka', '0')
            
            total_harga = float(str(total_harga_raw).replace('.', '').replace(',', '.')) if total_harga_raw else 0.0
            uang_muka = float(str(uang_muka_raw).replace('.', '').replace(',', '.')) if uang_muka_raw else 0.0
            
            items_json_data = request.POST.get('items_json')
            total_kalkulasi_json = 0.0
            
            if items_json_data:
                items_list = json.loads(items_json_data)
                for item in items_list:
                    total_kalkulasi_json += float(item.get('total', 0))
            
            if total_harga == 0 and total_kalkulasi_json > 0:
                total_harga = total_kalkulasi_json
            
            sisa_bayar = total_harga - uang_muka
        
            if customer_id:
                order_utama.customer = get_object_or_404(Customer, id=customer_id)
            
            if nama_order:
                order_utama.nama_order = nama_order
            
            if v_tgl_order:
                order_utama.tgl_order = v_tgl_order

            order_utama.status = status
            order_utama.total_harga = total_harga
            order_utama.uang_muka = uang_muka
            order_utama.sisa_bayar = sisa_bayar
            order_utama.keterangan = keterangan if keterangan else ''
                
            order_utama.save() 
            
            if items_json_data:
                OrderDetail.objects.filter(order_utama=order_utama).delete()
                for item in items_list:
                    OrderDetail.objects.create(
                        order_utama=order_utama,
                        kode_item=item.get('kode_item', '-'),
                        nama_item=item.get('nama_item'),
                        nama_pesanan=item.get('nama_pesanan'),
                        qty=int(item.get('qty', 1)),
                        panjang=float(item.get('panjang', 1)),
                        lebar=float(item.get('lebar', 1)),
                        harga_dasar=float(item.get('harga_dasar', 0)),
                        harga_jual=float(item.get('harga_jual', 0)),
                        jasa_desain=float(item.get('jasa_desain', 0)),
                        biaya_lain=float(item.get('biaya_lain', 0)),
                        total=float(item.get('total', 0)),
                        keterangan=item.get('keterangan', '')
                    )
            
            messages.success(request, f"Order {order_utama.no_order} berhasil diperbarui!")
            return redirect('list_order')
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f"Gagal memperbarui order: {str(e)}")
            return redirect('list_order')
            
    return redirect('list_order')

def hapus_order_view(request, order_id):
    # Pastikan hanya menerima request POST demi keamanan data
    if request.method == "POST":
        # 1. Ambil data order berdasarkan ID
        order = get_object_or_404(OrderUtama, id=order_id)
        
        # 2. Ambil alasan hapus yang diisi user di modal HTML
        alasan = request.POST.get('alasan_hapus')
        
        if alasan:
            # 3. Jalankan Soft Delete (Ubah status, simpan alasan & waktu hapus)
            order.is_active = False
            order.alasan_hapus = alasan
            order.deleted_at = timezone.now()  # Mencatat waktu pembatalan
            order.save()
            
            # 4. Beri notifikasi sukses ke user
            messages.success(request, f"Order {order.no_order} berhasil dinonaktifkan.")
        else:
            messages.error(request, "Gagal menghapus! Alasan pembatalan wajib diisi.")
            
    # Kembalikan user ke halaman list stok / order semula
    return redirect('list_order')

#=====================================piutang=====================================
def piutang(request):
    # 💡 1. Tangkap status filter dari parameter GET URL, default ke 'Belum Lunas'
    status_aktif = request.GET.get('status', 'Belum Lunas')
    
    # Base queryset awal (ambil semua data piutang dengan pre-fetch relasi terkait)
    daftar_piutang_qs = PiutangPelanggan.objects.all().select_related('order', 'order__customer').order_by('-updated_at')
    
    # 💡 2. Lakukan penyaringan data berdasarkan pilihan filter status user
    if status_aktif != 'Semua':
        daftar_piutang_qs = daftar_piutang_qs.filter(status=status_aktif)
        
    # Paginator (Tetap aman membatasi 25 baris per halaman)
    paginator = Paginator(daftar_piutang_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 💡 3. Kirim status_aktif ke context agar tombol filter di HTML bisa tahu mana yang sedang menyala
    context = {
        'page_obj': page_obj,
        'status_aktif': status_aktif,
    }
    return render(request, 'inventory/piutang.html', context)
@login_required(login_url='login')
def bayar_cicilan(request, piutang_id):
    if request.method == 'POST':
        piutang_obj = get_object_or_404(PiutangPelanggan, id=piutang_id)
        nominal_input = request.POST.get('nominal_pembayaran')
        keterangan_input = request.POST.get('keterangan', '')

        try:
            nominal_pembayaran = float(nominal_input)
        except (ValueError, TypeError):
            messages.error(request, "Nominal pembayaran harus berupa angka valid!")
            return redirect('piutang')

        if nominal_pembayaran <= 0:
            messages.error(request, "Nominal pembayaran harus lebih besar dari Rp 0!")
            return redirect('piutang')

        if nominal_pembayaran > float(piutang_obj.sisa_piutang):
            messages.error(request, f"Nominal kelebihan! Sisa piutang saat ini adalah Rp {piutang_obj.sisa_piutang:,.0f}")
            return redirect('piutang')

        with transaction.atomic():
            CicilanPiutang.objects.create(
                piutang=piutang_obj,
                nominal_dicicil=nominal_pembayaran,
                keterangan=keterangan_input
            )

            piutang_obj.sisa_piutang = float(piutang_obj.sisa_piutang) - nominal_pembayaran
            
            if piutang_obj.sisa_piutang == 0:
                piutang_obj.status = 'Lunas'
            piutang_obj.save()

            order_obj = piutang_obj.order
            order_obj.sisa_bayar = float(order_obj.sisa_bayar) - nominal_pembayaran
            order_obj.save()

            messages.success(request, f"Berhasil mencatat cicilan sebesar Rp {nominal_pembayaran:,.0f} untuk {piutang_obj.order.customer.nama_customer}")

    return redirect('piutang')

#=====================================Hutang=====================================
@login_required(login_url='login')
def hutang(request):
    # ==========================================
    # LOGIKA POST (PROSES CICILAN UTANG)
    # ==========================================
    if request.method == 'POST':    
        hutang_id = request.POST.get('id_hutang')
        nominal_cicil = request.POST.get('nominal_cicil')
        
        try:
            nominal_cicil = Decimal(nominal_cicil.replace('.', '').replace(',', '.'))
            hutang_obj = Hutang.objects.get(id=hutang_id)
            arus_stok_obj = hutang_obj.arus_stok
            
            if nominal_cicil <= 0:
                messages.error(request, "Nominal pembayaran harus lebih dari 0!")
                return redirect('hutang') # ✅ Sekarang aman (ditambahkan return)
                
            elif nominal_cicil > hutang_obj.sisa_hutang:
                sisa_formatted = f"{hutang_obj.sisa_hutang:,.0f}".replace(',', '.')
                messages.error(request, f"Nominal pembayaran melebihi sisa utang (Maksimal Rp {sisa_formatted})")
                return redirect('hutang') # ✅ Sekarang aman (ditambahkan return)
                
            else:
                arus_stok_obj.pembayaran += nominal_cicil
                arus_stok_obj.save() 
                
                cicil_formatted = f"{nominal_cicil:,.0f}".replace(',', '.')
                messages.success(request, f"Berhasil membayar utang sebesar Rp {cicil_formatted}")
                return redirect('hutang')
                
        except (Hutang.DoesNotExist, ValueError, TypeError):
            messages.error(request, "Terjadi kesalahan saat memproses pembayaran utang.")
            return redirect('hutang')

    # ==========================================
    # LOGIKA GET (FILTER DATA & RENDER HALAMAN)
    # ==========================================
    status_aktif = request.GET.get('status', 'Belum Lunas') # Default: Belum Lunas
    
    # Ambil base queryset
    hutang_queryset = Hutang.objects.all().order_by('-arus_stok__tanggal')
    
    # Filter data berdasarkan status pilihan user (Lunas / Belum Lunas)
    if status_aktif != 'Semua':
        hutang_queryset = hutang_queryset.filter(status=status_aktif)
    
    daftar_hutang_custom = []
    
    # Kelompokkan item barang berdasarkan no_invoice
    for h in hutang_queryset:
        arus_utama = h.arus_stok
        items_list = []
        
        if arus_utama:
            if arus_utama.no_invoice:
                semua_item_nota = ArusStok.objects.filter(
                    jenis_arus='Pembelian',
                    no_invoice=arus_utama.no_invoice
                )
                for item in semua_item_nota:
                    items_list.append({
                        'kode_barang': item.barang.kode_barang if item.barang else '-',
                        'nama_barang': item.barang.nama_barang if item.barang else '-',
                        'qty': item.qty_arus
                    })
            else:
                items_list.append({
                    'kode_barang': arus_utama.barang.kode_barang if arus_utama.barang else '-',
                    'nama_barang': arus_utama.barang.nama_barang if arus_utama.barang else '-',
                    'qty': arus_utama.qty_arus
                })
        else:
            items_list.append({
                'kode_barang': '-',
                'nama_barang': 'Tidak diketahui',
                'qty': 0
            })

        daftar_hutang_custom.append({
            'obj': h,
            'items_json': json.dumps(items_list)
        })
    
    # Bungkus data ke dalam context
    context = {
        'daftar_hutang': daftar_hutang_custom,
        'status_aktif': status_aktif,
    }
    
    # ✅ SEKARANG DIKEMBALIKAN DENGAN BERSIH BERSAMA CONTEXT-NYA
    return render(request, 'inventory/hutang.html', context)

    
#=====================================Transaksi=====================================
def transaksi(request):
    if request.method == 'POST':
        tanggal = request.POST.get('tanggal')
        keterangan = request.POST.get('keterangan')
        jenis = request.POST.get('jenis')
        nominal = request.POST.get('nominal')
        pilihan_bulan = request.POST.get('filter_bulan_aktif', '')
        start_date_aktif = request.POST.get('filter_start_aktif', '')
        end_date_aktif = request.POST.get('filter_end_aktif', '')
        
        Transaksi.objects.create(
            tanggal=tanggal,
            keterangan=keterangan,
            jenis=jenis,
            nominal=Decimal(nominal)
        )
        
        response = redirect('transaksi')
        if start_date_aktif and end_date_aktif:
            response['Location'] += f"?bulan_terpilih={pilihan_bulan}&start_date={start_date_aktif}&end_date={end_date_aktif}"
        return response

    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    query_search = request.GET.get('search', '')

    daftar_transaksi_query = Transaksi.objects.all().order_by('tanggal', 'id')
    
    sisa_minggu_lalu = Decimal(0)
    total_pemasukan = Decimal(0)
    total_pengeluaran = Decimal(0)
    sisa_dana = Decimal(0)

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            daftar_transaksi_query = daftar_transaksi_query.filter(tanggal__range=[start_date, end_date])
            
            pemasukan_lalu = Transaksi.objects.filter(tanggal__lt=start_date, jenis='pemasukan').aggregate(total=Sum('nominal'))['total'] or Decimal(0)
            pengeluaran_lalu = Transaksi.objects.filter(tanggal__lt=start_date, jenis='pengeluaran').aggregate(total=Sum('nominal'))['total'] or Decimal(0)
            sisa_minggu_lalu = pemasukan_lalu - pengeluaran_lalu
        except ValueError:
            pass

    if query_search:
        daftar_transaksi_query = daftar_transaksi_query.filter(
            Q(keterangan__icontains=query_search) | Q(jenis__icontains=query_search)
        )

    total_pemasukan = daftar_transaksi_query.filter(jenis='pemasukan').aggregate(total=Sum('nominal'))['total'] or Decimal(0)
    total_pengeluaran = daftar_transaksi_query.filter(jenis='pengeluaran').aggregate(total=Sum('nominal'))['total'] or Decimal(0)
    sisa_dana = sisa_minggu_lalu + total_pemasukan - total_pengeluaran

    context = {
        'daftar_transaksi': daftar_transaksi_query,
        'sisa_minggu_lalu': sisa_minggu_lalu,
        'total_pemasukan': total_pemasukan,
        'total_pengeluaran': total_pengeluaran,
        'sisa_dana': sisa_dana,
    }
    return render(request, 'inventory/transaksi.html', context)


@login_required(login_url='login')
def hapus_transaksi(request, id):
    transaksi = get_object_or_404(Transaksi, id=id)
    transaksi.delete()
    return redirect('transaksi')


#=========================home=======================
@login_required(login_url='login')
def home(request):
    if request.method == 'POST':
        action = request.POST.get('action') 
        
        if action == 'delete':
            kegiatan_id = request.POST.get('kegiatan_id')
            if kegiatan_id:
                Kegiatan.objects.filter(id=kegiatan_id).delete()
                messages.success(request, "Kegiatan manual berhasil dihapus!")
            return redirect('home')
            
        elif action == 'lunas_hutang':
            hutang_id = request.POST.get('hutang_id')
            if hutang_id:
                hutang = Hutang.objects.filter(id=hutang_id).first()
                if hutang:
                    hutang.status = 'Lunas'
                    hutang.sisa_hutang = 0
                    hutang.save()
                    
                    arus = hutang.arus_stok
                    if arus:
                        total_harga_nota = arus.qty_arus * arus.harga_satuan
                        arus.pembayaran = total_harga_nota
                        arus.sisa_pembayaran = 0
                        arus.save()
                        
                    messages.success(request, "Hutang telah ditandai Lunas!")
            return redirect('home')
            
        else:
            kegiatan_nama = request.POST.get('kegiatan')
            deskripsi = request.POST.get('deskripsi')
            tanggal = request.POST.get('tanggal') 

            if kegiatan_nama and tanggal:
                Kegiatan.objects.create(
                    kegiatan=kegiatan_nama,
                    deskripsi=deskripsi,
                    tanggal=tanggal
                )
                messages.success(request, "Kegiatan baru berhasil ditambahkan!")
            else:
                messages.error(request, "Gagal menambahkan kegiatan. Data tidak lengkap.")
            
            return redirect('home') 

    daftar_hutang = Hutang.objects.all().select_related('arus_stok__suplier', 'arus_stok')
    
    daftar_kegiatan = Kegiatan.objects.all()
    events_data = {}

    # Set untuk melacak No. Invoice yang sudah dimasukkan ke kalender Home
    invoice_terproses = set()

    for h in daftar_hutang:
        arus_utama = h.arus_stok
        if not arus_utama:
            continue
            
        # 💡 KEMBALIKAN KE TENGGAT PEMBAYARAN (Agar menetap di hari jatuh tempo)
        # Kita cek tenggat_pembayaran dulu, kalau kosong baru fallback ke tanggal input
        target_tanggal = arus_utama.tenggat_pembayaran or arus_utama.tanggal
        
        if target_tanggal:
            # Pastikan diconvert ke string format murni YYYY-MM-DD
            tgl_str = target_tanggal.strftime('%Y-%m-%d')
        else:
            continue
            
        supplier_nama = arus_utama.suplier.nama_suplier if arus_utama.suplier else "Supplier"
        
        # JIKA MEMILIKI NO INVOICE (Gabungan Banyak Barang)
        if arus_utama.no_invoice:
            if arus_utama.no_invoice in invoice_terproses:
                continue
                
            invoice_terproses.add(arus_utama.no_invoice)
            
            semua_hutang_nota = Hutang.objects.filter(arus_stok__no_invoice=arus_utama.no_invoice)
            total_sisa_nota = sum(item.sisa_hutang for item in semua_hutang_nota)
            
            # Jika semua item di nota itu Lunas, maka statusnya Lunas
            status_nota = 'Lunas' if all(item.status == 'Lunas' for item in semua_hutang_nota) else 'Belum Lunas'
            keterangan_tampil = f"Inv: {arus_utama.no_invoice} | Sisa: Rp {total_sisa_nota:,.0f}".replace(',', '.')
        
        # JIKA TANPA NO INVOICE (Pembelian eceran/satuan)
        else:
            status_nota = h.status
            keterangan_tampil = f"Sisa: Rp {h.sisa_hutang:,.0f} | Nota: {arus_utama.keterangan_arus or '-'}"

        # Masukkan ke dalam dictionary data kalender event
        if tgl_str not in events_data:
            events_data[tgl_str] = []
            
        events_data[tgl_str].append({
            'id': h.id,
            'tipe': 'debt',
            'status_bayar': status_nota, 
            'judul': f"Bayar Hutang: {supplier_nama}",
            'detail': keterangan_tampil
        })

    # ==========================================
    # AMBIL DATA KEGIATAN MANUAL GENERAL
    # ==========================================
    for k in daftar_kegiatan:
        tgl_str = k.tanggal.strftime('%Y-%m-%d')
        if tgl_str not in events_data:
            events_data[tgl_str] = []
        events_data[tgl_str].append({
            'id': k.id, 
            'tipe': 'general',
            'judul': k.kegiatan,
            'detail': k.deskripsi or '-'
        })

    context = {
        'events_json': json.dumps(events_data)
    }
    return render(request, 'inventory/home.html', context)

#=========================stok opname============================
def stok_opname(request):
    if request.method == 'POST':
        barang_id = request.POST.get('barang')
        tanggal_input = request.POST.get('tanggal')
        jenis = request.POST.get('jenis')
        qty_sistem = request.POST.get('qty_sistem')
        qty_gudang = request.POST.get('qty_gudang')
        selisih = request.POST.get('selisih')
        stok_akhir = request.POST.get('stok_akhir')
        keterangan = request.POST.get('keterangan', '')

        if not barang_id:
            messages.error(request, "Gagal menyimpan! Barang harus dipilih dari daftar rekomendasi resmi.")
            return redirect('stok_opname')

        try:
            with transaction.atomic():
                barang_obj = List_Stok.objects.get(id=barang_id)

                StokOpname.objects.create(
                    tanggal=tanggal_input if tanggal_input else timezone.now(),
                    barang=barang_obj,
                    jenis=jenis,
                    qty_sistem=int(qty_sistem) if qty_sistem else 0,
                    qty_gudang=int(qty_gudang) if qty_gudang else 0,
                    selisih=int(selisih) if selisih else 0,
                    stok_akhir=int(stok_akhir) if stok_akhir else 0,
                    keterangan=keterangan
                )

                barang_obj.qty = int(stok_akhir)
                barang_obj.save()

                messages.success(request, f"Stok opname untuk {barang_obj.nama_barang} berhasil disimpan!")
        
        except List_Stok.DoesNotExist:
            messages.error(request, "Data barang tidak ditemukan di sistem.")
        except Exception as e:
            messages.error(request, f"Terjadi kegagalan sistem: {str(e)}")

        return redirect('stok_opname')

    query = request.GET.get('search', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    jenis_filter = request.GET.get('jenis', 'Semua') 
    hari_ini = timezone.now().date()
    
    opname_list = StokOpname.objects.all().select_related('barang')

    if start_date and end_date:
        opname_list = opname_list.filter(tanggal__date__range=[start_date, end_date])
    else:
        opname_list = opname_list.filter(tanggal__date=hari_ini)
        start_date = hari_ini.strftime('%Y-%m-%d')
        end_date = hari_ini.strftime('%Y-%m-%d')

    if query:
        opname_list = opname_list.filter(
            Q(barang__nama_barang__icontains=query) |
            Q(barang__kode_barang__icontains=query)
        )

    if jenis_filter and jenis_filter != 'Semua':
        opname_list = opname_list.filter(jenis=jenis_filter)

    opname_list = opname_list.order_by('-tanggal')
    semua_barang = List_Stok.objects.all().order_by('nama_barang')

    context = {
        'opname_list': opname_list,
        'semua_barang': semua_barang,
        'query': query,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'jenis_aktif': jenis_filter, 
    }
    return render(request, 'inventory/stok_opname.html', context)

def hapus_stok_opname(request, pk):
    if request.method == 'POST':
        opname = get_object_or_404(StokOpname, pk=pk)
        barang = opname.barang

        try:
            with transaction.atomic():
                if barang:
                    barang.qty = opname.qty_sistem
                    barang.save()
                    nama_barang = barang.nama_barang
                else:
                    nama_barang = "Barang Terhapus"

                opname.delete()
                messages.success(request, f"Riwayat opname untuk {nama_barang} berhasil dihapus.")
        
        except Exception as e:
            messages.error(request, f"Gagal menghapus data: {str(e)}")
            
    return redirect('stok_opname')
        

#====================faktur=======================
def faktur_lunas(request, order_id):
    order_obj = get_object_or_404(OrderUtama, id=order_id)
    
    # Cek apakah sudah lunas dan belum memiliki kode faktur
    if order_obj.sisa_bayar <= 0 and not order_obj.kode_faktur:
        tanggal_sekarang = timezone.now().date()
        order_obj.tgl_pelunasan = tanggal_sekarang
        order_obj.kode_faktur = order_obj.generate_kode_faktur(tanggal_sekarang)
        order_obj.save()
    
    # Cek apakah user mencoba akses faktur pada order yang belum lunas
    elif order_obj.sisa_bayar > 0:
        messages.error(request, "Order belum lunas!")
        return redirect('list_order')

    context = {
        'order': order_obj,
        'tgl_cetak_sekarang': timezone.now(),
        'is_faktur_lunas': True
    }
    return render(request, 'inventory/faktur_order.html', context)

#===================faktur order=====================
def faktur_order(request, order_id):
    order_obj = get_object_or_404(OrderUtama, id=order_id)
    
    context = {
        'order': order_obj,
        'tgl_cetak_sekarang': timezone.now()
    }
    return render(request, 'inventory/faktur_order.html', context)

#===========================spk==============================
def detail_spk(request, order_id):
    order_obj = get_object_or_404(OrderUtama, id=order_id)

    context = {
        'order': order_obj, 
        'tgl_cetak_sekarang': timezone.now()
    }
    return render(request, 'inventory/spk_detail.html', context)

def update_tgl_cetak(request, order_id):
    return JsonResponse({'status': 'success', 'message': 'Waktu cetak berhasil diperbarui'})