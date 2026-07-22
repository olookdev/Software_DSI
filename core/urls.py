from django.contrib import admin
from django.urls import path
from inventory.views import (
    login_view,
    logout_view,
    list_stok,
    data_customer,
    data_suplier,
    daftar_harga,
    piutang,
    edit_suplier,
    edit_customer,
    edit_stok,
    hapus_harga,
    hapus_harga_jual,
    edit_harga_jual,
    daftar_harga_jual,
    tambah_jenis,
    hapus_stok,
    edit_harga_stok,
    tambah_arus_stok,
    log_arus_stok,
    edit_arus_stok,
    hapus_arus_stok,
    hapus_customer,
    hapus_suplier,
    list_order,
    cari_customer,
    tambah_order,
    kode_order,
    cari_produk,
    get_order_items,
    edit_order,
    bayar_cicilan,
    ambil_harga_satuan,
    transaksi,
    hapus_transaksi,
    hutang,
    home,
    stok_opname,
    hapus_stok_opname,
    update_tgl_cetak,
    detail_spk,
    faktur_order,
    faktur_lunas,
    pengiriman,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth
    path("", login_view, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    # home
    path("home/", home, name="home"),
    # Utama
    path("daftar_harga/", daftar_harga, name="daftar_harga"),
    # Harga Stok
    path("daftar-harga/edit-stok/", edit_harga_stok, name="edit_harga_stok"),
    path("daftar-harga/hapus/<int:id>/", hapus_harga, name="hapus_harga"),
    # Harga Jual
    path("harga-jual/", daftar_harga_jual, name="daftar_harga_jual"),
    path("harga-jual/edit/", edit_harga_jual, name="edit_harga_jual"),
    path("harga-jual/hapus/<int:id>/", hapus_harga_jual, name="hapus_harga_jual"),
    # Stok
    path("stok/", list_stok, name="list_stok"),
    path("stok/edit/", edit_stok, name="edit_stok"),
    path("stok/tambah-jenis/", tambah_jenis, name="tambah_jenis"),
    path("stok/hapus/<int:id>/", hapus_stok, name="hapus_stok"),
    # Arus Stok
    path("stok/arus/", log_arus_stok, name="log_arus_stok"),
    path("stok/arus/tambah/", tambah_arus_stok, name="tambah_arus_stok"),
    path("stok/arus/edit/<int:pk>/", edit_arus_stok, name="edit_arus_stok"),
    path("stok/arus/hapus/<int:pk>/", hapus_arus_stok, name="hapus_arus_stok"),
    path("stok/ambil-harga/", ambil_harga_satuan, name="ambil_harga_satuan"),
    # Stok opname
    path("stok/stok_opname", stok_opname, name="stok_opname"),
    path("stok/hapus_opname/<int:pk>/", hapus_stok_opname, name="hapus_stok_opname"),
    # Customer
    path("customer/", data_customer, name="data_customer"),
    path("customer/edit/", edit_customer, name="edit_customer"),
    path("customer/hapus/<int:pk>/", hapus_customer, name="hapus_customer"),
    # Suplier
    path("suplier/", data_suplier, name="data_suplier"),
    path("suplier/edit/", edit_suplier, name="edit_suplier"),
    path("suplier/hapus/<int:pk>/", hapus_suplier, name="hapus_suplier"),
    # hutang
    path("hutang/", hutang, name="hutang"),
    # order
    path("order/", list_order, name="list_order"),
    path("order/tambah/", tambah_order, name="tambah_order"),
    path("api/cari-customer/", cari_customer, name="cari_customer"),
    path("api/get-next-order-number/", kode_order, name="api_get_next_order_number"),
    path("api/cari-produk/", cari_produk, name="api_cari_produk"),
    path(
        "api/get-order-items/<int:order_id>/", get_order_items, name="get_order_items"
    ),
    path("order/edit/<int:order_id>/", edit_order, name="edit_order_utama"),
    path("order/edit/<int:order_id>/", edit_order, name="edit_order"),
    # piutang
    path("piutang/", piutang, name="piutang"),
    path("piutang/bayar/<int:piutang_id>/", bayar_cicilan, name="bayar_cicilan"),
    # transaksi
    path("transaksi", transaksi, name="transaksi"),
    path("transaksi/hapus/<int:id>/", hapus_transaksi, name="hapus_transaksi"),
    # faktur order
    path("order/faktur-order/<int:order_id>/", faktur_order, name="faktur_order"),
    path(
        "order/update-tgl-cetak/<int:order_id>/",
        update_tgl_cetak,
        name="update_tgl_cetak",
    ),
    # Faktur
    path("order/faktur/<int:order_id>/", faktur_lunas, name="faktur_lunas"),
    # spk
    path("order/spk/<int:order_id>/", detail_spk, name="detail_spk"),
    # pengiriman
    path("order/pengiriman/<int:order_id>", pengiriman, name="pengiriman"),
]
