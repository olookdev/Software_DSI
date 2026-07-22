from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Max, Sum
from django.http import JsonResponse
from django.conf import settings
from .models import (
    Suplier,
    Customer,
    List_Stok,
    JenisBarang,
    HargaStok,
    HargaJual,
    HargaJualBahan,
    ArusStok,
    OrderUtama,
    OrderDetail,
    PiutangPelanggan,
    CicilanPiutang,
    Transaksi,
    Hutang,
    Kegiatan,
    StokOpname,
    Pengiriman,
    PengirimanDetail,
)
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import json
from decimal import Decimal
from datetime import datetime


def login_view(request):

    # default user
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(username="admin", password="030504", email=None)

    if request.method == "POST":
        u = request.POST.get("username")
        p = request.POST.get("password")

        user = authenticate(request, username=u, password=p)

        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Username atau Password salah!")

    return render(request, "inventory/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# ========================Stok========================
@login_required(login_url="login")
def list_stok(request):
    if request.method == "POST":
        v_nama = request.POST.get("nama_barang")
        v_satuan = request.POST.get("satuan")
        v_ukuran = request.POST.get("ukuran")
        v_keterangan = request.POST.get("keterangan")
        v_jenis_id = request.POST.get("jenis")

        if not v_nama or not v_jenis_id:
            messages.error(request, "Gagal! Nama dan Jenis Barang wajib diisi.")
            return redirect("list_stok")

        obj_jenis = JenisBarang.objects.get(id=v_jenis_id)
        nama_jenis = obj_jenis.nama.upper()
        prefix = nama_jenis[0]

        bentrok = (
            JenisBarang.objects.filter(nama__istartswith=prefix)
            .exclude(id=v_jenis_id)
            .exists()
        )
        if bentrok:
            prefix = nama_jenis[:2]

        nomor = 1
        while True:
            v_kode = f"{prefix}-{str(nomor).zfill(3)}"
            if not List_Stok.objects.filter(kode_barang=v_kode).exists():
                break
            nomor += 1

        List_Stok.objects.create(
            kode_barang=v_kode,
            nama_barang=v_nama,
            jenis_id=v_jenis_id,
            satuan=v_satuan,
            ukuran=v_ukuran,
            keterangan=v_keterangan,
            qty=0,
        )
        messages.success(
            request, f"Barang {v_nama} berhasil ditambahkan dengan kode {v_kode}!"
        )
        return redirect("list_stok")

    tab_aktif = request.GET.get("tab", "list")
    context = {
        "tab_aktif": tab_aktif,
        "semua_jenis": JenisBarang.objects.all(),
    }

    if tab_aktif == "list":
        query = request.GET.get("search")

        if query:
            stok = (
                List_Stok.objects.filter(
                    Q(nama_barang__icontains=query)
                    | Q(kode_barang__icontains=query)
                    | Q(jenis__nama__icontains=query)
                )
                .select_related("jenis")
                .order_by("id")
            )
        else:
            stok = List_Stok.objects.all().select_related("jenis").order_by("id")

        for s in stok:
            if s.nama_barang:
                s.nama_barang = (
                    s.nama_barang.replace("\r", "")
                    .replace("\n", " ")
                    .replace("'", "\\'")
                )
            if s.keterangan:
                s.keterangan = (
                    s.keterangan.replace("\r", "")
                    .replace("\n", " ")
                    .replace("'", "\\'")
                )
            if s.ukuran:
                s.ukuran = (
                    s.ukuran.replace("\r", "").replace("\n", " ").replace("'", "\\'")
                )

        total_qty_data = stok.aggregate(Sum("qty"))["qty__sum"]
        total_stok = int(total_qty_data) if total_qty_data else 0
        barang_terbanyak = stok.order_by("-qty").first()

        if barang_terbanyak and barang_terbanyak.qty > 0:
            pemakaian_info = f"{barang_terbanyak.nama_barang}"
        else:
            pemakaian_info = "-"

        context.update(
            {
                "stok_barang": stok,
                "query": query,
                "total_seluruh_stok": total_stok,
                "pemakaian_terbanyak": pemakaian_info,
            }
        )

    elif tab_aktif == "arus":
        arus_stok_list = (
            ArusStok.objects.all().select_related("barang").order_by("-tanggal")
        )
        semua_barang = List_Stok.objects.all().order_by("nama_barang")
        semua_suplier = []
        try:
            semua_suplier = Suplier.objects.all().order_by("nama_suplier")
        except Exception:
            pass
        context.update(
            {
                "arus_stok_list": arus_stok_list,
                "semua_barang": semua_barang,
                "semua_suplier": semua_suplier,
            }
        )

    elif tab_aktif == "opname":
        context.update(
            {
                "data_opname_list": [],
            }
        )

    return render(request, "inventory/list_stok.html", context)


def edit_stok(request):
    if request.method == "POST":
        v_id = request.POST.get("id_barang")
        v_nama = request.POST.get("nama_barang")
        v_satuan = request.POST.get("satuan")
        v_ukuran = request.POST.get("ukuran")
        v_keterangan = request.POST.get("keterangan")
        v_jenis_id = request.POST.get("jenis")

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

        return redirect("list_stok")


def tambah_jenis(request):
    if request.method == "POST":
        nama_jenis = request.POST.get("nama_jenis")
        if nama_jenis:
            jenis_baru, created = JenisBarang.objects.get_or_create(nama=nama_jenis)
            if created:
                return JsonResponse(
                    {"status": "success", "id": jenis_baru.id, "nama": jenis_baru.nama}
                )
            else:
                return JsonResponse({"status": "error", "message": "Jenis sudah ada"})
    return JsonResponse({"status": "error", "message": "Invalid request"})


def hapus_stok(request, id):
    barang = get_object_or_404(List_Stok, id=id)
    barang.delete()
    return redirect("list_stok")


# ======================Customer======================
def data_customer(request):
    if request.method == "POST":
        v_nama = request.POST.get("nama_customer")
        v_alamat = request.POST.get("alamat")
        v_telp = request.POST.get("telepon")
        v_email = request.POST.get("email")

        jumlah_data = Customer.objects.count() + 1
        v_kode = f"C-{str(jumlah_data).zfill(3)}"

        Customer.objects.create(
            kode_customer=v_kode,
            nama_customer=v_nama,
            alamat=v_alamat,
            telepon=v_telp,
            email=v_email,
        )

        return redirect("data_customer")

    tgl_mulai = request.GET.get("start_date")
    tgl_akhir = request.GET.get("end_date")
    query = request.GET.get("search")

    semua_customer = Customer.objects.all()

    if tgl_mulai and tgl_akhir:
        semua_customer = semua_customer.filter(
            created_at__date__range=[tgl_mulai, tgl_akhir]
        )

    if query:
        semua_customer = semua_customer.filter(
            Q(nama_customer__icontains=query) | Q(kode_customer__icontains=query)
        )

    max_nominal = semua_customer.aggregate(Max("total_transaksi"))[
        "total_transaksi__max"
    ]

    if max_nominal and max_nominal > 0:
        top_cust = semua_customer.filter(total_transaksi=max_nominal).first()
        penjualan_terbanyak = f"{top_cust.nama_customer} (Rp {max_nominal})"
    else:
        penjualan_terbanyak = "Tidak ada data"

    return render(
        request,
        "inventory/data_customer.html",
        {
            "customer": semua_customer.order_by("id"),
            "query": query,
            "start_date": tgl_mulai,
            "end_date": tgl_akhir,
            "customer_terbanyak": penjualan_terbanyak,
        },
    )


def edit_customer(request):
    if request.method == "POST":
        v_id = request.POST.get("id_customer")
        v_nama = request.POST.get("nama_customer")
        v_alamat = request.POST.get("alamat")
        v_telp = request.POST.get("telepon")
        v_email = request.POST.get("email")

        customer = Customer.objects.get(id=v_id)
        customer.nama_customer = v_nama
        customer.alamat = v_alamat
        customer.telepon = v_telp
        customer.email = v_email
        customer.save()

        return redirect("data_customer")


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

    return redirect("data_customer")


# ======================suplier======================
def data_suplier(request):
    if request.method == "POST":
        v_nama = request.POST.get("nama_suplier")
        v_alamat = request.POST.get("alamat")
        v_telp = request.POST.get("telepon")
        v_email = request.POST.get("email")

        jumlah_data = Suplier.objects.count() + 1
        v_kode = f"S-{str(jumlah_data).zfill(3)}"

        Suplier.objects.create(
            kode_suplier=v_kode,
            nama_suplier=v_nama,
            alamat=v_alamat,
            telepon=v_telp,
            email=v_email,
        )

        return redirect("data_suplier")
    query = request.GET.get("search")

    if query:
        semua_suplier = Suplier.objects.filter(
            Q(nama_suplier__icontains=query) | Q(kode_suplier__icontains=query)
        ).order_by("id")
    else:
        semua_suplier = Suplier.objects.all().order_by("id")

    return render(
        request,
        "inventory/data_suplier.html",
        {"supliers": semua_suplier, "query": query},
    )


def edit_suplier(request):
    if request.method == "POST":
        v_id = request.POST.get("id_suplier")
        v_nama = request.POST.get("nama_suplier")
        v_alamat = request.POST.get("alamat")
        v_telp = request.POST.get("telepon")
        v_email = request.POST.get("email")

        suplier = Suplier.objects.get(id=v_id)
        suplier.nama_suplier = v_nama
        suplier.alamat = v_alamat
        suplier.telepon = v_telp
        suplier.email = v_email
        suplier.save()

        return redirect("data_suplier")


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

    return redirect("data_suplier")


# ========================HargaStok==========================
def daftar_harga(request):
    if request.method == "POST":
        barang_id = request.POST.get("barang")
        suplier_id = request.POST.get("suplier")
        harga = request.POST.get("harga_satuan")

        HargaStok.objects.create(
            barang_id=barang_id, suplier_id=suplier_id, harga_satuan=harga
        )
        return redirect("daftar_harga")
    query = request.GET.get("search", "")

    data_harga_stok = HargaStok.objects.all().select_related("barang", "suplier")

    if query:
        data_harga_stok = data_harga_stok.filter(
            Q(barang__nama_barang__icontains=query)
            | Q(barang__kode_barang__icontains=query)
        )

    data_harga_stok = data_harga_stok.order_by("-id")
    termahal_obj = (
        HargaStok.objects.all()
        .select_related("barang")
        .order_by("-harga_satuan")
        .first()
    )
    termurah_obj = (
        HargaStok.objects.all()
        .select_related("barang")
        .order_by("harga_satuan")
        .first()
    )
    stok_termahal = f"{termahal_obj.barang.nama_barang}" if termahal_obj else "-"
    stok_termurah = f"{termurah_obj.barang.nama_barang}" if termurah_obj else "-"
    pilihan_barang = (
        List_Stok.objects.all().select_related("jenis").order_by("nama_barang")
    )
    barang_data = []

    for barang in pilihan_barang:
        id_angka_barang = int(barang.id)
        stok_termahal_item = (
            HargaStok.objects.filter(barang_id=id_angka_barang)
            .order_by("-harga_satuan")
            .first()
        )

        if stok_termahal_item:
            harga_termahal = stok_termahal_item.harga_satuan
            id_stok = stok_termahal_item.id
        else:
            harga_termahal = 0
            id_stok = None

        barang_data.append(
            {
                "id": barang.id,
                "kode_barang": barang.kode_barang,
                "nama_barang": barang.nama_barang,
                "keterangan": barang.keterangan or "-",
                "harga": float(harga_termahal) if harga_termahal else 0,
                "id_stok": id_stok,
            }
        )

    context = {
        "harga_list": data_harga_stok,
        "barang_data": barang_data,
        "semua_suplier": Suplier.objects.all(),
        "semua_barang": pilihan_barang,
        "harga_jual_list": HargaJual.objects.prefetch_related(
            "list_bahan__barang", "list_bahan__harga_stok_terpilih"
        )
        .all()
        .order_by("id"),
        "stok_termahal": stok_termahal,
        "stok_termurah": stok_termurah,
        "query": query,
    }
    return render(request, "inventory/daftar_harga.html", context)


def edit_harga_stok(request):
    if request.method == "POST":
        id_harga = request.POST.get("id_harga")
        id_barang = request.POST.get("barang")
        id_suplier = request.POST.get("suplier")
        harga_satuan = request.POST.get("harga_satuan")
        harga_stok = get_object_or_404(HargaStok, id=id_harga)
        harga_stok.barang_id = id_barang
        harga_stok.suplier_id = id_suplier
        harga_stok.harga_satuan = harga_satuan
        harga_stok.save()
        return redirect("daftar_harga")


def hapus_harga(request, id):
    harga_entry = HargaStok.objects.get(id=id)
    harga_entry.delete()
    return redirect("daftar_harga")


# =====================harga jual=====================
def daftar_harga_jual(request):
    if request.method == "POST":
        if "nama_produk" in request.POST:
            v_nama_produk = request.POST.get("nama_produk")
            v_tenaga = float(request.POST.get("biaya_tenaga") or 0)
            v_listrik = float(request.POST.get("biaya_listrik") or 0)
            v_keterangan = request.POST.get("keterangan_produk")
            v_jual = float(request.POST.get("harga_jual_akhir") or 0)
            id_bahan_terpilih = request.POST.getlist("bahan_terpilih")

            if v_nama_produk and id_bahan_terpilih:
                produk_baru = HargaJual.objects.create(
                    nama_produk=v_nama_produk,
                    biaya_tenaga_kerja=v_tenaga,
                    biaya_listrik=v_listrik,
                    keterangan_produk=v_keterangan,
                    harga_jual_akhir=v_jual,
                )

                for barang_id in id_bahan_terpilih:
                    if barang_id:
                        stok_termahal = (
                            HargaStok.objects.filter(barang_id=barang_id)
                            .order_by("-harga_satuan")
                            .first()
                        )
                        if stok_termahal:
                            HargaJualBahan.objects.create(
                                harga_jual=produk_baru,
                                barang_id=barang_id,
                                harga_stok_terpilih=stok_termahal,
                            )
            return redirect("/daftar_harga/#harga-jual")

        else:
            barang_id = request.POST.get("barang")
            suplier_id = request.POST.get("suplier")
            harga = request.POST.get("harga_satuan")
            HargaStok.objects.create(
                barang_id=barang_id, suplier_id=suplier_id, harga_satuan=harga
            )
            return redirect("daftar_harga")

    query_jual = request.GET.get("search_jual", "")

    try:
        harga_jual_query = HargaJual.objects.prefetch_related(
            "list_bahan__barang", "list_bahan__harga_stok_terpilih"
        ).all()
    except Exception:
        harga_jual_query = HargaJual.objects.all()

    if query_jual:
        harga_jual_query = harga_jual_query.filter(
            Q(nama_produk__icontains=query_jual) | Q(kode_produk__icontains=query_jual)
        )

    harga_jual_list = harga_jual_query.order_by("id")
    jual_termahal_obj = HargaJual.objects.all().order_by("-harga_jual_akhir").first()
    jual_termurah_obj = HargaJual.objects.all().order_by("harga_jual_akhir").first()

    if jual_termahal_obj and jual_termahal_obj.nama_produk:
        produk_termahal = f"{jual_termahal_obj.nama_produk} (Rp {int(jual_termahal_obj.harga_jual_akhir):,})"
    else:
        produk_termahal = "-"

    if jual_termurah_obj and jual_termurah_obj.nama_produk:
        produk_termurah = f"{jual_termurah_obj.nama_produk} (Rp {int(jual_termurah_obj.harga_jual_akhir):,})"
    else:
        produk_termurah = "-"

    data_harga_stok = (
        HargaStok.objects.all().select_related("barang", "suplier").order_by("-id")
    )
    pilihan_barang = (
        List_Stok.objects.all().select_related("jenis").order_by("nama_barang")
    )
    barang_data = []

    for barang in pilihan_barang:
        id_angka_barang = int(barang.id)
        stok_termahal_item = (
            HargaStok.objects.filter(barang_id=id_angka_barang)
            .order_by("-harga_satuan")
            .first()
        )
        harga_termahal = stok_termahal_item.harga_satuan if stok_termahal_item else 0
        id_stok = stok_termahal_item.id if stok_termahal_item else None

        barang_data.append(
            {
                "id": barang.id,
                "kode_barang": barang.kode_barang,
                "nama_barang": barang.nama_barang,
                "keterangan": barang.keterangan or "-",
                "harga": float(harga_termahal) if harga_termahal else 0,
                "id_stok": id_stok,
            }
        )

    context = {
        "harga_list": data_harga_stok,
        "barang_data": barang_data,
        "semua_suplier": Suplier.objects.all(),
        "semua_barang": pilihan_barang,
        "harga_jual_list": harga_jual_list,
        "produk_termahal": produk_termahal,
        "produk_termurah": produk_termurah,
        "query_jual": query_jual,
    }
    return render(request, "inventory/daftar_harga.html", context)


def edit_harga_jual(request):
    if request.method == "POST":
        id_jual = request.POST.get("id_harga_jual")
        v_nama_produk = request.POST.get("nama_produk")
        v_tenaga = float(request.POST.get("biaya_tenaga") or 0)
        v_listrik = float(request.POST.get("biaya_listrik") or 0)
        v_keterangan = request.POST.get("keterangan_produk")
        v_jual = float(request.POST.get("harga_jual_akhir") or 0)
        id_bahan_terpilih = request.POST.getlist("bahan_terpilih")

        try:
            produk = HargaJual.objects.get(id=id_jual)
            produk.nama_produk = v_nama_produk
            produk.biaya_tenaga_kerja = v_tenaga
            produk.biaya_listrik = v_listrik
            produk.keterangan_produk = v_keterangan
            produk.harga_jual_akhir = v_jual
            produk.save()

            HargaJualBahan.objects.filter(harga_jual=produk).delete()

            for barang_id in id_bahan_terpilih:
                if barang_id:
                    stok_termahal = (
                        HargaStok.objects.filter(barang_id=barang_id)
                        .order_by("-harga_satuan")
                        .first()
                    )
                    if stok_termahal:
                        HargaJualBahan.objects.create(
                            harga_jual=produk,
                            barang_id=barang_id,
                            harga_stok_terpilih=stok_termahal,
                        )
        except HargaJual.DoesNotExist:
            pass

        return redirect("/daftar_harga/#harga-jual")
    return redirect("/daftar_harga/#harga-jual")


def hapus_harga_jual(request, id):
    hj = HargaJual.objects.get(id=id)
    hj.delete()
    return redirect("/daftar_harga/#harga-jual")


# ======================== ARUS STOK ========================
def log_arus_stok(request):
    query = request.GET.get("search", "")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    status_filter = request.GET.get("status", "Semua")
    hari_ini = timezone.now().date()
    arus_stok_list = ArusStok.objects.all().select_related("barang", "suplier")

    if start_date and end_date:
        arus_stok_list = arus_stok_list.filter(
            tanggal__date__range=[start_date, end_date]
        )
    else:
        arus_stok_list = arus_stok_list.filter(tanggal__date=hari_ini)
        start_date = hari_ini.strftime("%Y-%m-%d")
        end_date = hari_ini.strftime("%Y-%m-%d")

    if query:
        arus_stok_list = arus_stok_list.filter(
            Q(barang__nama_barang__icontains=query)
            | Q(barang__kode_barang__icontains=query)
        )

    total_masuk_data = arus_stok_list.filter(jenis_arus__iexact="Pembelian").aggregate(
        Sum("qty_arus")
    )["qty_arus__sum"]
    total_masuk = int(total_masuk_data) if total_masuk_data else 0
    total_keluar_data = arus_stok_list.filter(jenis_arus__iexact="Pemakaian").aggregate(
        Sum("qty_arus")
    )["qty_arus__sum"]
    total_keluar = int(total_keluar_data) if total_keluar_data else 0

    if status_filter and status_filter != "Semua":
        if status_filter == "masuk":
            arus_stok_list = arus_stok_list.filter(jenis_arus__iexact="Pembelian")
        elif status_filter == "keluar":
            arus_stok_list = arus_stok_list.filter(jenis_arus__iexact="Pemakaian")

    arus_stok_list = arus_stok_list.order_by("-tanggal")
    semua_barang = List_Stok.objects.all().order_by("nama_barang")
    semua_suplier = Suplier.objects.all().order_by("nama_suplier")

    context = {
        "arus_stok_list": arus_stok_list,
        "semua_barang": semua_barang,
        "semua_suplier": semua_suplier,
        "query": query,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "status_aktif": status_filter,
        "card_masuk": total_masuk,
        "card_keluar": total_keluar,
    }
    return render(request, "inventory/arus_stok.html", context)


def tambah_arus_stok(request):
    if request.method == "POST":
        v_jenis_arus = request.POST.get("jenis_arus")
        v_barang_id = request.POST.get("barang")
        v_qty = request.POST.get("qty_arus")
        v_keterangan = request.POST.get("keterangan_arus")
        v_suplier_id = request.POST.get("suplier")
        v_harga = request.POST.get("harga_satuan")
        v_pembayaran = request.POST.get("pembayaran")
        v_tenggat = request.POST.get("tenggat_pembayaran")

        if not v_jenis_arus or not v_barang_id or not v_qty:
            messages.error(request, "Gagal! Data barang dan kuantitas wajib diisi.")
            return redirect("log_arus_stok")

        try:
            with transaction.atomic():
                barang = List_Stok.objects.get(id=v_barang_id)
                qty_arus = float(v_qty)
                suplier_obj = None
                harga_satuan = 0
                pembayaran = 0
                tenggat_pembayaran = None

                if v_jenis_arus == "Pemakaian":
                    if float(barang.qty) < qty_arus:
                        raise ValueError(
                            f"Stok '{barang.nama_barang}' tidak mencukupi. Stok saat ini hanya {barang.qty} pcs, sedangkan Anda menginput {qty_arus} pcs."
                        )

                    barang.qty = float(barang.qty) - qty_arus

                elif v_jenis_arus == "Pembelian":
                    harga_satuan = float(v_harga or 0)
                    pembayaran = float(v_pembayaran or 0)
                    if v_tenggat:
                        tenggat_pembayaran = v_tenggat

                    if v_suplier_id:
                        suplier_obj = Suplier.objects.get(id=v_suplier_id)

                    barang.qty = float(barang.qty) + qty_arus

                barang.save()

                ArusStok.objects.create(
                    barang=barang,
                    jenis_arus=v_jenis_arus,
                    qty_arus=qty_arus,
                    keterangan_arus=v_keterangan,
                    suplier=suplier_obj,
                    harga_satuan=harga_satuan,
                    pembayaran=pembayaran,
                    tenggat_pembayaran=tenggat_pembayaran,
                )

                messages.success(
                    request,
                    f"Berhasil mencatat {v_jenis_arus} untuk barang: {barang.nama_barang}.",
                )

        except List_Stok.DoesNotExist:
            messages.error(request, "Gagal! Data barang tidak ditemukan di sistem.")
        except Suplier.DoesNotExist:
            messages.error(request, "Gagal! Data Supplier tidak valid.")
        except ValueError as e:
            messages.error(request, f"Gagal! {str(e)}")
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan sistem: {str(e)}")

    return redirect("log_arus_stok")


def edit_arus_stok(request, pk):
    if request.method == "POST":
        try:
            arus = ArusStok.objects.get(id=pk)
            v_keterangan = request.POST.get("keterangan_arus")
            v_suplier_id = request.POST.get("suplier")
            v_harga = request.POST.get("harga_satuan")

            v_pembayaran = request.POST.get("pembayaran")
            v_tenggat = request.POST.get("tenggat_pembayaran")

            arus.keterangan_arus = v_keterangan

            if arus.jenis_arus == "Pembelian":
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

    return redirect("log_arus_stok")


def hapus_arus_stok(request, pk):
    try:
        with transaction.atomic():
            arus = ArusStok.objects.get(id=pk)
            barang = arus.barang
            qty_arus = float(arus.qty_arus)

            if arus.jenis_arus == "Pembelian":
                if float(barang.qty) < qty_arus:
                    messages.error(
                        request,
                        f"Gagal menghapus! Stok '{barang.nama_barang}' saat ini ({barang.qty}) tidak mencukupi jika dikurangi {qty_arus} dari pembatalan pembelian ini.",
                    )
                    return redirect("log_arus_stok")
                barang.qty = float(barang.qty) - qty_arus
            else:
                barang.qty = float(barang.qty) + qty_arus

            barang.save()
            arus.delete()

            messages.success(
                request,
                "Berhasil menghapus riwayat arus stok dan menyesuaikan ulang master stok barang.",
            )

    except ArusStok.DoesNotExist:
        messages.error(request, "Gagal! Data riwayat arus stok tidak ditemukan.")
    except Exception as e:
        messages.error(request, f"Terjadi kesalahan sistem: {str(e)}")

    return redirect("log_arus_stok")


def ambil_harga_satuan(request):
    barang_id = request.GET.get("barang_id")
    suplier_id = request.GET.get("suplier_id")

    if barang_id and suplier_id:
        try:
            harga_obj = HargaStok.objects.get(
                barang_id=barang_id, suplier_id=suplier_id
            )
            return JsonResponse(
                {"status": "success", "harga_satuan": float(harga_obj.harga_satuan)}
            )
        except HargaStok.DoesNotExist:
            return JsonResponse({"status": "not_found", "harga_satuan": 0})

    return JsonResponse(
        {"status": "error", "message": "Parameter tidak lengkap"}, status=400
    )


# ================================================Order================================================
def titik_uang(nilai_string):
    if not nilai_string or nilai_string == "":
        return 0.0
    clean_string = str(nilai_string).replace(".", "").replace(",", ".")
    try:
        return float(clean_string)
    except ValueError:
        return 0.0


def list_order(request):
    query = request.GET.get("search")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    status_filter = request.GET.get("status", "Semua")
    hari_ini = timezone.now().date()
    semua_order = OrderUtama.objects.all()

    if start_date and end_date:
        semua_order = semua_order.filter(tgl_order__date__range=[start_date, end_date])
    else:
        semua_order = semua_order.filter(tgl_order__date=hari_ini)
        start_date = hari_ini.strftime("%Y-%m-%d")
        end_date = hari_ini.strftime("%Y-%m-%d")
    if query:
        semua_order = semua_order.filter(
            Q(no_order__icontains=query)
            | Q(nama_order__icontains=query)
            | Q(customer__nama_customer__icontains=query)
        )

    total_orderan = semua_order.count()
    total_status_order = semua_order.filter(status__iexact="order").count()
    total_status_proses = semua_order.filter(status__iexact="proses").count()
    total_status_selesai = semua_order.filter(status__iexact="selesai").count()

    if status_filter and status_filter != "Semua":
        semua_order = semua_order.filter(status__iexact=status_filter)

    semua_order = semua_order.order_by("-id")

    return render(
        request,
        "inventory/list_order.html",
        {
            "orders": semua_order,
            "query": query,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "status_aktif": status_filter,
            "card_total": total_orderan,
            "card_order": total_status_order,
            "card_proses": total_status_proses,
            "card_selesai": total_status_selesai,
        },
    )


def tambah_order(request):
    if request.method == "POST":
        customer_id = request.POST.get("customer_id")
        v_nama_order = request.POST.get("nama_order")
        v_keterangan = request.POST.get("keterangan", "")
        v_no_order = request.POST.get("no_order")
        v_status = request.POST.get("status", "order")

        v_tgl_order = request.POST.get("tgl_order")
        if not v_tgl_order:
            v_tgl_order = timezone.now()

        v_total_harga = titik_uang(request.POST.get("total_harga", 0))
        v_uang_muka = titik_uang(request.POST.get("uang_muka", 0))
        v_sisa_bayar = titik_uang(request.POST.get("sisa_bayar", 0))

        items_json = request.POST.get("items_json")

        if not customer_id:
            messages.error(request, "Customer wajib dipilih!")
            return redirect("list_order")

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
                tgl_order=v_tgl_order,
            )

            if items_json:
                daftar_item = json.loads(items_json)
                for item in daftar_item:
                    OrderDetail.objects.create(
                        order_utama=order_utama,
                        nama_pesanan=item.get("nama_pesanan"),
                        nama_item=item.get("nama_item"),
                        kode_item=item.get("kode_item"),
                        qty=int(item.get("qty", 1)),
                        panjang=float(item.get("panjang", 1.0)),
                        lebar=float(item.get("lebar", 1.0)),
                        harga_dasar=float(item.get("harga_dasar", 0)),
                        harga_jual=float(item.get("harga_jual", 0)),
                        jasa_desain=float(item.get("jasa_desain", 0)),
                        biaya_lain=float(item.get("biaya_lain", 0)),
                        total=float(item.get("total", 0)),
                        keterangan=item.get("keterangan", ""),
                    )
                messages.success(
                    request,
                    f"Order {v_no_order} berhasil disimpan dengan seluruh itemnya!",
                )
            else:
                messages.warning(
                    request, f"Order {v_no_order} disimpan tanpa ada item pesanan."
                )

        except Exception as e:
            import traceback

            traceback.print_exc()

            messages.error(request, f"Terjadi kesalahan saat menyimpan data: {str(e)}")

        return redirect("list_order")
    return redirect("list_order")


def cari_customer(request):
    term = request.GET.get("q", "")
    customers = Customer.objects.filter(nama_customer__icontains=term)[:10]
    results = []
    for c in customers:
        results.append(
            {
                "id": c.id,
                "nama": c.nama_customer,
                "kode": (
                    c.kode_customer if hasattr(c, "kode_customer") else f"CUST-{c.id}"
                ),
                "alamat": c.alamat if c.alamat else "-",
                "telepon": c.telepon if c.telepon else "-",
            }
        )
    return JsonResponse({"results": results}, safe=False)


def kode_order(request):
    sekarang = timezone.now()
    tahun_bulan = sekarang.strftime("%Y%m")
    prefix = f"ORD-{tahun_bulan}-"
    order_terakhir = (
        OrderUtama.objects.filter(no_order__startswith=prefix)
        .order_by("-no_order")
        .first()
    )
    if order_terakhir:
        nomor_terakhir_str = order_terakhir.no_order.split("-")[-1]
        nomor_baru = int(nomor_terakhir_str) + 1
    else:
        nomor_baru = 1
    next_no_order = f"{prefix}{str(nomor_baru).zfill(3)}"
    return JsonResponse({"next_no_order": next_no_order})


def cari_produk(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        produk_queryset = HargaJual.objects.filter(nama_produk__icontains=query)[:10]
        for produk in produk_queryset:
            results.append(
                {
                    "id": produk.id,
                    "nama_produk": produk.nama_produk,
                    "harga_jual": (
                        int(produk.harga_jual_akhir) if produk.harga_jual_akhir else 0
                    ),
                    "kode_barang": produk.kode_produk if produk.kode_produk else "PRD",
                }
            )
    return JsonResponse({"results": results})


def get_order_items(request, order_id):
    order_utama = get_object_or_404(OrderUtama, id=order_id)
    items_queryset = OrderDetail.objects.filter(order_utama=order_utama).order_by(
        "kode_item"
    )

    daftar_item = []
    for item in items_queryset:
        daftar_item.append(
            {
                "kode_item": item.kode_item if item.kode_item else "-",
                "nama_item": item.nama_item,
                "nama_pesanan": item.nama_pesanan,
                "qty": item.qty,
                "panjang": float(item.panjang),
                "lebar": float(item.lebar),
                "harga_dasar": float(item.harga_dasar),
                "harga_jual": float(item.harga_jual),
                "jasa_desain": float(item.jasa_desain),
                "biaya_lain": float(item.biaya_lain),
                "total": float(item.total),
                "keterangan": item.keterangan if item.keterangan else "",
            }
        )

    return JsonResponse({"items": daftar_item})


def edit_order(request, order_id):
    if request.method == "POST":
        order_utama = get_object_or_404(OrderUtama, id=order_id)

        try:
            customer_id = request.POST.get("id_customer_hidden")
            nama_order = request.POST.get("nama_order_utama")
            status = request.POST.get("status")
            keterangan = request.POST.get("keterangan_utama")  #
            total_harga = float(
                request.POST.get("total_harga_all", "0")
                .replace(".", "")
                .replace(",", ".")
            )
            uang_muka = float(
                request.POST.get("uang_muka", "0").replace(".", "").replace(",", ".")
            )

            items_json_data = request.POST.get("items_json")
            total_kalkulasi_json = 0.0

            if items_json_data:
                items_list = json.loads(items_json_data)
                for item in items_list:
                    total_kalkulasi_json += float(item.get("total", 0))

            if total_harga == 0 and total_kalkulasi_json > 0:
                total_harga = total_kalkulasi_json

            sisa_bayar = total_harga - uang_muka

            if customer_id:
                order_utama.customer = get_object_or_404(Customer, id=customer_id)

            if nama_order:
                order_utama.nama_order = nama_order

            order_utama.status = status
            order_utama.total_harga = total_harga
            order_utama.uang_muka = uang_muka
            order_utama.sisa_bayar = sisa_bayar
            if keterangan:
                order_utama.keterangan = keterangan

            order_utama.save()

            if items_json_data:
                OrderDetail.objects.filter(order_utama=order_utama).delete()
                for item in items_list:
                    OrderDetail.objects.create(
                        order_utama=order_utama,
                        kode_item=item.get("kode_item", "-"),
                        nama_item=item.get("nama_item"),
                        nama_pesanan=item.get("nama_pesanan"),
                        qty=int(item.get("qty", 1)),
                        panjang=float(item.get("panjang", 1)),
                        lebar=float(item.get("lebar", 1)),
                        harga_dasar=float(item.get("harga_dasar", 0)),
                        harga_jual=float(item.get("harga_jual", 0)),
                        jasa_desain=float(item.get("jasa_desain", 0)),
                        biaya_lain=float(item.get("biaya_lain", 0)),
                        total=float(item.get("total", 0)),
                        keterangan=item.get("keterangan", ""),
                    )

            messages.success(
                request, f"Order {order_utama.no_order} berhasil diperbarui!"
            )
            return redirect("/order/")

        except Exception as e:
            messages.error(request, f"Gagal memperbarui order: {str(e)}")
            return redirect("/order/")

    return redirect("/order/")


# =====================================piutang=====================================
@login_required(login_url="login")
def piutang(request):
    daftar_piutang = (
        PiutangPelanggan.objects.filter(status="Belum Lunas")
        .select_related("order", "order__customer")
        .order_by("-updated_at")
    )

    context = {
        "daftar_piutang": daftar_piutang,
    }
    return render(request, "inventory/piutang.html", context)


@login_required(login_url="login")
def bayar_cicilan(request, piutang_id):
    if request.method == "POST":
        piutang_obj = get_object_or_404(PiutangPelanggan, id=piutang_id)
        nominal_input = request.POST.get("nominal_pembayaran")
        keterangan_input = request.POST.get("keterangan", "")

        try:
            nominal_pembayaran = float(nominal_input)
        except (ValueError, TypeError):
            messages.error(request, "Nominal pembayaran harus berupa angka valid!")
            return redirect("piutang")

        if nominal_pembayaran <= 0:
            messages.error(request, "Nominal pembayaran harus lebih besar dari Rp 0!")
            return redirect("piutang")

        if nominal_pembayaran > float(piutang_obj.sisa_piutang):
            messages.error(
                request,
                f"Nominal kelebihan! Sisa piutang saat ini adalah Rp {piutang_obj.sisa_piutang:,.0f}",
            )
            return redirect("piutang")

        with transaction.atomic():
            CicilanPiutang.objects.create(
                piutang=piutang_obj,
                nominal_dicicil=nominal_pembayaran,
                keterangan=keterangan_input,
            )

            piutang_obj.sisa_piutang = (
                float(piutang_obj.sisa_piutang) - nominal_pembayaran
            )

            if piutang_obj.sisa_piutang == 0:
                piutang_obj.status = "Lunas"
            piutang_obj.save()

            order_obj = piutang_obj.order
            order_obj.sisa_bayar = float(order_obj.sisa_bayar) - nominal_pembayaran
            order_obj.save()

            messages.success(
                request,
                f"Berhasil mencatat cicilan sebesar Rp {nominal_pembayaran:,.0f} untuk {piutang_obj.order.customer.nama_customer}",
            )

    return redirect("piutang")


# =====================================Hutang=====================================
@login_required(login_url="login")
def hutang(request):
    if request.method == "POST":
        hutang_id = request.POST.get("id_hutang")
        nominal_cicil = request.POST.get("nominal_cicil")

        try:
            nominal_cicil = Decimal(nominal_cicil.replace(".", "").replace(",", "."))
            hutang_obj = Hutang.objects.get(id=hutang_id)
            arus_stok_obj = hutang_obj.arus_stok

            if nominal_cicil <= 0:
                messages.error(request, "Nominal pembayaran harus lebih dari 0!")
            elif nominal_cicil > hutang_obj.sisa_hutang:
                sisa_formatted = f"{hutang_obj.sisa_hutang:,.0f}".replace(",", ".")
                messages.error(
                    request,
                    f"Nominal pembayaran melebihi sisa utang (Maksimal Rp {sisa_formatted})",
                )
            else:
                arus_stok_obj.pembayaran += nominal_cicil
                arus_stok_obj.save()

                cicil_formatted = f"{nominal_cicil:,.0f}".replace(",", ".")
                messages.success(
                    request, f"Berhasil membayar utang sebesar Rp {cicil_formatted}"
                )
                return redirect("hutang")

        except (Hutang.DoesNotExist, ValueError, TypeError):
            messages.error(
                request, "Terjadi kesalahan saat memproses pembayaran utang."
            )
            return redirect("hutang")

    daftar_hutang = Hutang.objects.filter(status="Belum Lunas").order_by(
        "-arus_stok__tanggal"
    )

    context = {
        "daftar_hutang": daftar_hutang,
    }
    return render(request, "inventory/hutang.html", context)


# =====================================Transaksi=====================================
def transaksi(request):
    if request.method == "POST":
        tanggal = request.POST.get("tanggal")
        keterangan = request.POST.get("keterangan")
        jenis = request.POST.get("jenis")
        nominal = request.POST.get("nominal")
        pilihan_bulan = request.POST.get("filter_bulan_aktif", "")
        start_date_aktif = request.POST.get("filter_start_aktif", "")
        end_date_aktif = request.POST.get("filter_end_aktif", "")

        Transaksi.objects.create(
            tanggal=tanggal,
            keterangan=keterangan,
            jenis=jenis,
            nominal=Decimal(nominal),
        )

        response = redirect("transaksi")
        if start_date_aktif and end_date_aktif:
            response[
                "Location"
            ] += f"?bulan_terpilih={pilihan_bulan}&start_date={start_date_aktif}&end_date={end_date_aktif}"
        return response

    start_date_str = request.GET.get("start_date", "")
    end_date_str = request.GET.get("end_date", "")
    query_search = request.GET.get("search", "")

    daftar_transaksi_query = Transaksi.objects.all().order_by("tanggal", "id")

    sisa_minggu_lalu = Decimal(0)
    total_pemasukan = Decimal(0)
    total_pengeluaran = Decimal(0)
    sisa_dana = Decimal(0)

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            daftar_transaksi_query = daftar_transaksi_query.filter(
                tanggal__range=[start_date, end_date]
            )

            pemasukan_lalu = Transaksi.objects.filter(
                tanggal__lt=start_date, jenis="pemasukan"
            ).aggregate(total=Sum("nominal"))["total"] or Decimal(0)
            pengeluaran_lalu = Transaksi.objects.filter(
                tanggal__lt=start_date, jenis="pengeluaran"
            ).aggregate(total=Sum("nominal"))["total"] or Decimal(0)
            sisa_minggu_lalu = pemasukan_lalu - pengeluaran_lalu
        except ValueError:
            pass

    if query_search:
        daftar_transaksi_query = daftar_transaksi_query.filter(
            Q(keterangan__icontains=query_search) | Q(jenis__icontains=query_search)
        )

    total_pemasukan = daftar_transaksi_query.filter(jenis="pemasukan").aggregate(
        total=Sum("nominal")
    )["total"] or Decimal(0)
    total_pengeluaran = daftar_transaksi_query.filter(jenis="pengeluaran").aggregate(
        total=Sum("nominal")
    )["total"] or Decimal(0)
    sisa_dana = sisa_minggu_lalu + total_pemasukan - total_pengeluaran

    context = {
        "daftar_transaksi": daftar_transaksi_query,
        "sisa_minggu_lalu": sisa_minggu_lalu,
        "total_pemasukan": total_pemasukan,
        "total_pengeluaran": total_pengeluaran,
        "sisa_dana": sisa_dana,
    }
    return render(request, "inventory/transaksi.html", context)


@login_required(login_url="login")
def hapus_transaksi(request, id):
    transaksi = get_object_or_404(Transaksi, id=id)
    transaksi.delete()
    return redirect("transaksi")


# =========================home=======================
@login_required(login_url="login")
def home(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            kegiatan_id = request.POST.get("kegiatan_id")
            if kegiatan_id:
                Kegiatan.objects.filter(id=kegiatan_id).delete()
                messages.success(request, "Kegiatan manual berhasil dihapus!")
            return redirect("home")

        else:
            kegiatan_nama = request.POST.get("kegiatan")
            deskripsi = request.POST.get("deskripsi")
            tanggal = request.POST.get("tanggal")

            if kegiatan_nama and tanggal:
                Kegiatan.objects.create(
                    kegiatan=kegiatan_nama, deskripsi=deskripsi, tanggal=tanggal
                )
                messages.success(request, "Kegiatan baru berhasil ditambahkan!")
            else:
                messages.error(
                    request, "Gagal menambahkan kegiatan. Data tidak lengkap."
                )

            return redirect("home")

    daftar_hutang = Hutang.objects.filter(
        status="Belum Lunas", arus_stok__tenggat_pembayaran__isnull=False
    )

    daftar_kegiatan = Kegiatan.objects.all()
    events_data = {}

    for h in daftar_hutang:
        tgl_str = h.arus_stok.tenggat_pembayaran.strftime("%Y-%m-%d")
        if tgl_str not in events_data:
            events_data[tgl_str] = []

        supplier_nama = (
            h.arus_stok.suplier.nama_suplier if h.arus_stok.suplier else "Supplier"
        )
        events_data[tgl_str].append(
            {
                "tipe": "debt",
                "judul": f"Bayar Hutang: {supplier_nama}",
                "detail": f"Sisa Hutang: Rp {h.sisa_hutang:,.0f}".replace(",", "."),
            }
        )

    for k in daftar_kegiatan:
        tgl_str = k.tanggal.strftime("%Y-%m-%d")
        if tgl_str not in events_data:
            events_data[tgl_str] = []
        events_data[tgl_str].append(
            {
                "id": k.id,
                "tipe": "general",
                "judul": k.kegiatan,
                "detail": k.deskripsi or "-",
            }
        )

    context = {"events_json": json.dumps(events_data)}
    return render(request, "inventory/home.html", context)


# =========================stok opname============================
def stok_opname(request):
    if request.method == "POST":
        barang_id = request.POST.get("barang")
        tanggal_input = request.POST.get("tanggal")
        jenis = request.POST.get("jenis")
        qty_sistem = request.POST.get("qty_sistem")
        qty_gudang = request.POST.get("qty_gudang")
        selisih = request.POST.get("selisih")
        stok_akhir = request.POST.get("stok_akhir")
        keterangan = request.POST.get("keterangan", "")

        if not barang_id:
            messages.error(
                request,
                "Gagal menyimpan! Barang harus dipilih dari daftar rekomendasi resmi.",
            )
            return redirect("stok_opname")

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
                    keterangan=keterangan,
                )

                barang_obj.qty = int(stok_akhir)
                barang_obj.save()

                messages.success(
                    request,
                    f"Stok opname untuk {barang_obj.nama_barang} berhasil disimpan!",
                )

        except List_Stok.DoesNotExist:
            messages.error(request, "Data barang tidak ditemukan di sistem.")
        except Exception as e:
            messages.error(request, f"Terjadi kegagalan sistem: {str(e)}")

        return redirect("stok_opname")

    query = request.GET.get("search", "")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    jenis_filter = request.GET.get("jenis", "Semua")
    hari_ini = timezone.now().date()

    opname_list = StokOpname.objects.all().select_related("barang")

    if start_date and end_date:
        opname_list = opname_list.filter(tanggal__date__range=[start_date, end_date])
    else:
        opname_list = opname_list.filter(tanggal__date=hari_ini)
        start_date = hari_ini.strftime("%Y-%m-%d")
        end_date = hari_ini.strftime("%Y-%m-%d")

    if query:
        opname_list = opname_list.filter(
            Q(barang__nama_barang__icontains=query)
            | Q(barang__kode_barang__icontains=query)
        )

    if jenis_filter and jenis_filter != "Semua":
        opname_list = opname_list.filter(jenis=jenis_filter)

    opname_list = opname_list.order_by("-tanggal")
    semua_barang = List_Stok.objects.all().order_by("nama_barang")

    context = {
        "opname_list": opname_list,
        "semua_barang": semua_barang,
        "query": query,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "jenis_aktif": jenis_filter,
    }
    return render(request, "inventory/stok_opname.html", context)


def hapus_stok_opname(request, pk):
    if request.method == "POST":
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
                messages.success(
                    request, f"Riwayat opname untuk {nama_barang} berhasil dihapus."
                )

        except Exception as e:
            messages.error(request, f"Gagal menghapus data: {str(e)}")

    return redirect("stok_opname")


# ====================faktur=======================
def faktur_lunas(request, order_id):
    # 1. Ambil data order utama
    order_obj = get_object_or_404(OrderUtama, id=order_id)

    # 2. VALIDASI: Jika sisa bayar masih lebih besar dari 0, blokir akses
    if order_obj.sisa_bayar > 0:
        messages.error(
            request,
            f"Gagal membuka Faktur! Order {order_obj.no_order} belum lunas. "
            f"Sisa kekurangan masih Rp {int(order_obj.sisa_bayar):,}".replace(",", "."),
        )
        return redirect("list_order")  # Kembalikan ke halaman list order

    # 3. Jika lolos validasi (Sisa Bayar == 0), tampilkan template faktur yang sama
    context = {
        "order": order_obj,
        "tgl_cetak_sekarang": timezone.now(),
        "is_faktur_lunas": True,  # Penanda di HTML jika sewaktu-waktu butuh membedakan judul nota
    }
    return render(request, "inventory/faktur_order.html", context)


# ===================faktur order=====================
def faktur_order(request, order_id):
    order_obj = get_object_or_404(OrderUtama, id=order_id)

    context = {"order": order_obj, "tgl_cetak_sekarang": timezone.now()}
    return render(request, "inventory/faktur_order.html", context)


# ===========================spk==============================
def detail_spk(request, order_id):
    order_obj = get_object_or_404(OrderUtama, id=order_id)

    context = {"order": order_obj, "tgl_cetak_sekarang": timezone.now()}
    return render(request, "inventory/spk_detail.html", context)


def update_tgl_cetak(request, order_id):
    return JsonResponse(
        {"status": "success", "message": "Waktu cetak berhasil diperbarui"}
    )


# =========================pengiriman=======================
@login_required(login_url="login")
def pengiriman(request, order_id):
    order = get_object_or_404(
        OrderUtama.objects.prefetch_related("items", "customer"),
        id=order_id,
    )

    if request.method == "POST":
        payload_raw = request.POST.get("payload_split_order")
        if not payload_raw:
            messages.error(request, "Tidak ada data pengiriman untuk disimpan.")
            return redirect("pengiriman", order_id=order_id)

        try:
            daftar_pengiriman = json.loads(payload_raw)
        except json.JSONDecodeError:
            messages.error(request, "Data pengiriman tidak valid.")
            return redirect("pengiriman", order_id=order_id)

        if not daftar_pengiriman:
            messages.error(request, "Tidak ada data pengiriman untuk disimpan.")
            return redirect("pengiriman", order_id=order_id)

        sisa_qty = order.sisa_qty_per_item()

        total_diminta = {}
        for kirim in daftar_pengiriman:
            if not kirim.get("alamat") or not kirim.get("penerima"):
                messages.error(
                    request, "Alamat dan Penerima wajib diisi di setiap pengiriman."
                )
                return redirect("pengiriman", order_id=order_id)
            for item in kirim.get("items", []):
                oid = item.get("order_detail_id")
                qty = int(item.get("qty", 0))
                if not oid or qty <= 0:
                    messages.error(
                        request, "Item dan qty pada setiap baris wajib valid."
                    )
                    return redirect("pengiriman", order_id=order_id)
                oid = int(oid)
                total_diminta[oid] = total_diminta.get(oid, 0) + qty

        # VALIDASI UTAMA: tidak boleh melebihi sisa qty aktual di database
        for oid, qty_diminta in total_diminta.items():
            tersedia = sisa_qty.get(oid, 0)
            if qty_diminta > tersedia:
                nama_item_obj = get_object_or_404(OrderDetail, id=oid)
                messages.error(
                    request,
                    f"Gagal! Qty untuk item '{nama_item_obj.nama_item}' yang diminta ({qty_diminta}) "
                    f"melebihi sisa yang bisa dikirim ({tersedia}).",
                )
                return redirect("pengiriman", order_id=order_id)

        try:
            with transaction.atomic():
                for kirim in daftar_pengiriman:
                    pengiriman_obj = Pengiriman.objects.create(
                        order=order,
                        alamat=kirim.get("alamat"),
                        penerima=kirim.get("penerima"),
                        no_hp=kirim.get("no_hp", ""),
                    )
                    for item in kirim.get("items", []):
                        order_detail_obj = get_object_or_404(
                            OrderDetail, id=int(item.get("order_detail_id"))
                        )
                        PengirimanDetail.objects.create(
                            pengiriman=pengiriman_obj,
                            order_detail=order_detail_obj,
                            qty_kirim=int(item.get("qty", 1)),
                        )
            messages.success(
                request,
                f"{len(daftar_pengiriman)} pengiriman untuk order {order.no_order} berhasil disimpan!",
            )
        except Exception as e:
            messages.error(
                request, f"Terjadi kesalahan saat menyimpan pengiriman: {str(e)}"
            )

        return redirect("pengiriman", order_id=order_id)

    items = order.items.all().order_by("kode_item")
    sisa_qty_map = order.sisa_qty_per_item()

    for item in items:
        item.sisa_qty = sisa_qty_map.get(item.id, item.qty)

    context = {
        "order": order,
        "items": items,
        "sisa_qty_json": json.dumps(sisa_qty_map),
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, "inventory/pengiriman.html", context)
