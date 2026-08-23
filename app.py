"""
Ứng dụng Streamlit: TÍNH LÃI TIỀN GỬI TIẾT KIỆM (v3 — Ô NHẬP TIỀN THÔNG MINH)
Tác giả: Claude (chuyên gia IT tài chính giả lập)

ĐIỂM MỚI SO VỚI v2:
- Ô nhập số tiền được nâng cấp thành "ô nhập thông minh":
    + Gõ số ngắn (vd 50, 500) -> hiện các mức gợi ý theo bội số 10 (nghìn/triệu/tỷ).
    + Gõ trực tiếp "50 triệu", "1 tỷ", "1.5 tỷ", "200k"... đều hiểu được.
    + Có nút tăng nhanh +1/+10/+50 triệu và nút giảm nhanh tương ứng.
    + Tự động định dạng lại thành số VNĐ có dấu phẩy + nhãn rút gọn (vd "50 triệu").
- Toàn bộ nghiệp vụ tính lãi (rút trước hạn, tự động tái tục, 3 phương thức nhận lãi,
  bảng chi tiết, biểu đồ, so sánh 3 phương thức) giữ NGUYÊN như bản trước.

Lưu ý về giới hạn kỹ thuật: Streamlit chỉ rerun script khi một widget "chốt" giá trị
(nhấn Enter / rời khỏi ô nhập / bấm nút) — không có kiểu autocomplete "gõ tới đâu gợi ý
tới đó theo từng ký tự" như JavaScript thật sự. Gợi ý sẽ xuất hiện ngay sau khi bạn gõ
xong và nhấn Enter (hoặc click ra ngoài ô), điều này vẫn tạo cảm giác "gõ là có gợi ý"
rất nhanh trong thực tế sử dụng.
"""

import calendar
import re
from datetime import date, timedelta
from functools import partial

import streamlit as st

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# ==========================================================
# Cấu hình trang
# ==========================================================
st.set_page_config(page_title="Tính lãi tiền gửi tiết kiệm", page_icon="💰", layout="wide")
st.title("💰 TÍNH LÃI TIỀN GỬI TIẾT KIỆM")
st.caption(
    "Công cụ mô phỏng lãi tiền gửi tiết kiệm có kỳ hạn — tự động gia hạn, "
    "hỗ trợ 3 phương thức nhận lãi và tính lãi suất không kỳ hạn khi rút trước hạn."
)

KY_HAN_OPTIONS = {
    "1 tháng": 1, "2 tháng": 2, "3 tháng": 3, "6 tháng": 6,
    "9 tháng": 9, "12 tháng": 12, "13 tháng": 13,
    "18 tháng": 18, "24 tháng": 24, "36 tháng": 36,
    "Tùy chỉnh...": None,
}

PHUONG_THUC_OPTIONS = [
    "Nhận lãi cuối kỳ (gộp lãi vào gốc mỗi lần đáo hạn)",
    "Nhận lãi định kỳ hàng tháng",
    "Nhận lãi trước",
]


# ==========================================================
# Hàm tiện ích chung
# ==========================================================
def add_months(d: date, months: int) -> date:
    """Cộng thêm 'months' tháng vào ngày d, tự xử lý số ngày cuối tháng."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def fmt_vnd(so_tien: float) -> str:
    return f"{so_tien:,.0f} VNĐ"


def xay_dung_lich_ky(ngay_gui: date, ky_han_thang: int, ngay_rut: date):
    ky_hoan_thanh = []
    start = ngay_gui
    end = add_months(start, ky_han_thang)

    while ngay_rut >= end:
        so_ngay = (end - start).days
        ky_hoan_thanh.append((start, end, so_ngay))
        start = end
        end = add_months(start, ky_han_thang)

    if ngay_rut > start:
        so_ngay_le = (ngay_rut - start).days
        ky_le = (start, ngay_rut, so_ngay_le)
    else:
        ky_le = None

    return ky_hoan_thanh, ky_le


# ==========================================================
# Ô NHẬP TIỀN THÔNG MINH — parser + nhãn rút gọn + gợi ý
# ==========================================================
_SUFFIX_MULT = {
    "": 1, "d": 1, "dong": 1, "đ": 1, "đồng": 1,
    "k": 1_000, "nghin": 1_000, "nghìn": 1_000,
    "tr": 1_000_000, "trieu": 1_000_000, "triệu": 1_000_000, "m": 1_000_000,
    "ty": 1_000_000_000, "tỷ": 1_000_000_000, "b": 1_000_000_000,
}

_PARSE_RE = re.compile(r"^([\d]*\.?[\d]+)\s*([^\d\s]*)$", re.UNICODE)
_BARE_NUMBER_RE = re.compile(r"^\d*\.?\d+$")


def parse_smart_amount(text: str):
    """Hiểu các cách gõ: '500000000', '50 triệu', '1.5 tỷ', '200k'... -> float VNĐ hoặc None."""
    if not text:
        return None
    t = text.strip().lower()
    t = t.replace(",", "").replace("vnđ", "").replace("vnd", "").strip()
    m = _PARSE_RE.match(t)
    if not m:
        return None
    num_str, suffix = m.groups()
    suffix = suffix.strip()
    if suffix not in _SUFFIX_MULT:
        return None
    try:
        number = float(num_str)
    except ValueError:
        return None
    return number * _SUFFIX_MULT[suffix]


def is_bare_small_number(text: str):
    """Trả về số N nếu người dùng gõ một số trần (không hậu tố) và số đó < 1 triệu (còn mơ hồ)."""
    if not text:
        return None
    t = text.strip().replace(",", "")
    if _BARE_NUMBER_RE.match(t):
        try:
            n = float(t)
        except ValueError:
            return None
        if 0 < n < 1_000_000:
            return n
    return None


def auto_label(v: float) -> str:
    """Đổi số tiền thành nhãn rút gọn kiểu Việt Nam: 50 triệu / 1.5 tỷ / 200 nghìn..."""
    v = float(v)
    if v >= 1_000_000_000:
        x = v / 1_000_000_000
        return f"{x:g} tỷ"
    if v >= 1_000_000:
        x = v / 1_000_000
        return f"{x:g} triệu"
    if v >= 1_000:
        x = v / 1_000
        return f"{x:g} nghìn"
    return f"{v:g} đồng"


DEFAULT_AMOUNT = 100_000_000.0

if "so_tien_goc" not in st.session_state:
    st.session_state.so_tien_goc = DEFAULT_AMOUNT
if "so_tien_text" not in st.session_state:
    st.session_state.so_tien_text = f"{DEFAULT_AMOUNT:,.0f}"


def _set_amount(new_val: float):
    new_val = max(float(new_val), 0.0)
    st.session_state.so_tien_goc = new_val
    st.session_state.so_tien_text = f"{new_val:,.0f}"


def _on_change_text():
    val = parse_smart_amount(st.session_state.so_tien_text)
    if val is not None:
        _set_amount(val)
    else:
        # gõ không hợp lệ -> quay về giá trị hợp lệ gần nhất, tránh vỡ tính toán
        st.session_state.so_tien_text = f"{st.session_state.so_tien_goc:,.0f}"


def _reset_amount():
    _set_amount(DEFAULT_AMOUNT)


# ==========================================================
# GIAO DIỆN NHẬP TIỀN THÔNG MINH (nằm ngoài form để nút bấm phản hồi tức thì)
# ==========================================================
st.subheader("📋 Thông tin gửi tiết kiệm")

st.markdown("**💰 Số tiền gửi**")
c_input, c_reset = st.columns([5, 1])
with c_input:
    st.text_input(
        "Nhập số tiền (vd: 50, 500, 50 triệu, 1.5 tỷ, 200k...)",
        key="so_tien_text",
        on_change=_on_change_text,
        label_visibility="collapsed",
    )
with c_reset:
    st.button("↺ Đặt lại", on_click=_reset_amount, use_container_width=True)

st.caption(f"➡️ Số tiền đang chọn: **{fmt_vnd(st.session_state.so_tien_goc)}** "
           f"(≈ {auto_label(st.session_state.so_tien_goc)})")

# ---- Gợi ý nhanh khi gõ số ngắn/mơ hồ ----
n_goi_y = is_bare_small_number(st.session_state.so_tien_text)
if n_goi_y is not None:
    goi_y_values = [n_goi_y * 1_000, n_goi_y * 10_000, n_goi_y * 100_000, n_goi_y * 1_000_000]
    st.caption("💡 Gợi ý nhanh — bấm để chọn:")
    cols = st.columns(len(goi_y_values))
    for col, v in zip(cols, goi_y_values):
        with col:
            st.button(auto_label(v), key=f"goi_y_{v}", on_click=partial(_set_amount, v), use_container_width=True)

# ---- Nút tăng / giảm nhanh ----
def _adjust_amount(delta: float):
    """Đọc giá trị MỚI NHẤT từ session_state ngay tại thời điểm bấm nút, tránh lệch giá trị."""
    _set_amount(st.session_state.so_tien_goc + delta)


st.caption("⚡ Điều chỉnh nhanh:")
b1, b2, b3, b4, b5, b6 = st.columns(6)
buoc_dieu_chinh = [
    (b1, "➕ 1 triệu", 1_000_000),
    (b2, "➕ 10 triệu", 10_000_000),
    (b3, "➕ 50 triệu", 50_000_000),
    (b4, "➖ 1 triệu", -1_000_000),
    (b5, "➖ 10 triệu", -10_000_000),
    (b6, "➖ 50 triệu", -50_000_000),
]
for col, nhan, delta in buoc_dieu_chinh:
    with col:
        st.button(nhan, key=f"delta_{delta}", on_click=partial(_adjust_amount, delta), use_container_width=True)


# ==========================================================
# Form các thông tin còn lại — giữ nguyên như bản trước
# (so_tien_goc lấy từ ô nhập thông minh phía trên qua session_state)
# ==========================================================
with st.form("form_tinh_lai"):
    so_tien_goc = st.session_state.so_tien_goc
    st.markdown(f"*(Số tiền gửi đang dùng để tính: **{fmt_vnd(so_tien_goc)}**)*")

    c1, c2 = st.columns(2)
    with c1:
        lai_suat_ky_han = st.number_input(
            "Lãi suất CÓ kỳ hạn (%/năm)", min_value=0.0, value=5.5, step=0.1
        )
        lai_suat_khong_ky_han = st.number_input(
            "Lãi suất KHÔNG kỳ hạn (%/năm)", min_value=0.0, value=0.2, step=0.1
        )

    with c2:
        ngay_gui = st.date_input("Ngày gửi tiền", value=date.today())
        ngay_rut = st.date_input("Ngày rút tiền (dự kiến / thực tế)", value=date.today() + timedelta(days=180))

        ky_han_label = st.selectbox("Kỳ hạn gửi tiền", list(KY_HAN_OPTIONS.keys()), index=2)
        if KY_HAN_OPTIONS[ky_han_label] is None:
            ky_han_thang = st.number_input("Nhập số tháng kỳ hạn tùy chỉnh", min_value=1, value=1, step=1)
        else:
            ky_han_thang = KY_HAN_OPTIONS[ky_han_label]

    phuong_thuc = st.radio("Phương thức nhận lãi", PHUONG_THUC_OPTIONS, index=0)

    submitted = st.form_submit_button("🧮 TÍNH TOÁN", use_container_width=True)


# ==========================================================
# Xử lý tính toán — giữ nguyên toàn bộ logic của bản trước
# ==========================================================
if submitted:
    if ngay_rut <= ngay_gui:
        st.error("⚠️ Ngày rút tiền phải lớn hơn ngày gửi tiền.")
    else:
        ky_hoan_thanh, ky_le = xay_dung_lich_ky(ngay_gui, ky_han_thang, ngay_rut)

        i_ky_han = lai_suat_ky_han / 100
        i_khong_ky_han = lai_suat_khong_ky_han / 100
        so_ky_da_gia_han = max(len(ky_hoan_thanh) - 1, 0)

        rows = []  # để hiển thị bảng chi tiết

        # ---------- Trường hợp rút trước cả kỳ hạn đầu tiên ----------
        if not ky_hoan_thanh and ky_le is not None:
            start, end, so_ngay = ky_le
            lai = so_tien_goc * i_khong_ky_han / 365 * so_ngay
            tong_nhan = so_tien_goc + lai
            rows.append({
                "Kỳ": "Lẻ (rút trước hạn kỳ 1)",
                "Từ ngày": start.strftime("%d/%m/%Y"),
                "Đến ngày": end.strftime("%d/%m/%Y"),
                "Số ngày": so_ngay,
                "Lãi suất áp dụng": f"{lai_suat_khong_ky_han:.2f}%/năm (không kỳ hạn)",
                "Tiền lãi kỳ": fmt_vnd(lai),
            })
            trang_thai = "🔴 Rút trước hạn — toàn bộ hưởng lãi suất KHÔNG kỳ hạn"
            tong_lai = lai

        else:
            # ---------- Các kỳ đã hoàn thành ----------
            if phuong_thuc == PHUONG_THUC_OPTIONS[0]:
                # Nhận lãi cuối kỳ -> gộp lãi vào gốc (lãi kép qua các kỳ)
                p = so_tien_goc
                for (start, end, so_ngay) in ky_hoan_thanh:
                    lai_ky = p * i_ky_han / 365 * so_ngay
                    rows.append({
                        "Kỳ": "Hoàn thành (đáo hạn)",
                        "Từ ngày": start.strftime("%d/%m/%Y"),
                        "Đến ngày": end.strftime("%d/%m/%Y"),
                        "Số ngày": so_ngay,
                        "Lãi suất áp dụng": f"{lai_suat_ky_han:.2f}%/năm (có kỳ hạn)",
                        "Tiền lãi kỳ": fmt_vnd(lai_ky),
                    })
                    p += lai_ky  # nhập lãi vào gốc

                if ky_le is not None:
                    start, end, so_ngay = ky_le
                    lai_le = p * i_khong_ky_han / 365 * so_ngay
                    rows.append({
                        "Kỳ": "Lẻ (rút trước hạn kỳ hiện tại)",
                        "Từ ngày": start.strftime("%d/%m/%Y"),
                        "Đến ngày": end.strftime("%d/%m/%Y"),
                        "Số ngày": so_ngay,
                        "Lãi suất áp dụng": f"{lai_suat_khong_ky_han:.2f}%/năm (không kỳ hạn)",
                        "Tiền lãi kỳ": fmt_vnd(lai_le),
                    })
                    p += lai_le
                    trang_thai = "🟡 Rút trước hạn của kỳ hiện tại (các kỳ trước đã tính đủ lãi có kỳ hạn)"
                else:
                    trang_thai = "🟢 Rút đúng vào ngày đáo hạn — toàn bộ hưởng lãi suất CÓ kỳ hạn"

                tong_nhan = p
                tong_lai = p - so_tien_goc

            else:
                # Nhận lãi định kỳ hàng tháng HOẶC nhận lãi trước -> gốc giữ nguyên, không lãi kép
                nhan_truoc = (phuong_thuc == PHUONG_THUC_OPTIONS[2])
                tong_lai = 0.0
                for (start, end, so_ngay) in ky_hoan_thanh:
                    lai_ky = so_tien_goc * i_ky_han / 365 * so_ngay
                    nhan_dinh = "Tạm ứng đầu kỳ" if nhan_truoc else "Trả hàng tháng trong kỳ"
                    rows.append({
                        "Kỳ": "Hoàn thành (đáo hạn)",
                        "Từ ngày": start.strftime("%d/%m/%Y"),
                        "Đến ngày": end.strftime("%d/%m/%Y"),
                        "Số ngày": so_ngay,
                        "Lãi suất áp dụng": f"{lai_suat_ky_han:.2f}%/năm (có kỳ hạn) — {nhan_dinh}",
                        "Tiền lãi kỳ": fmt_vnd(lai_ky),
                    })
                    tong_lai += lai_ky

                if ky_le is not None:
                    start, end, so_ngay = ky_le
                    lai_le = so_tien_goc * i_khong_ky_han / 365 * so_ngay
                    ghi_chu = (
                        "Thu hồi phần lãi tạm ứng dư, chỉ còn hưởng lãi không kỳ hạn"
                        if nhan_truoc else
                        "Bù thêm lãi không kỳ hạn cho số ngày lẻ"
                    )
                    rows.append({
                        "Kỳ": "Lẻ (rút trước hạn kỳ hiện tại)",
                        "Từ ngày": start.strftime("%d/%m/%Y"),
                        "Đến ngày": end.strftime("%d/%m/%Y"),
                        "Số ngày": so_ngay,
                        "Lãi suất áp dụng": f"{lai_suat_khong_ky_han:.2f}%/năm (không kỳ hạn) — {ghi_chu}",
                        "Tiền lãi kỳ": fmt_vnd(lai_le),
                    })
                    tong_lai += lai_le
                    trang_thai = "🟡 Rút trước hạn của kỳ hiện tại (các kỳ trước đã tính đủ lãi có kỳ hạn)"
                else:
                    trang_thai = "🟢 Rút đúng vào ngày đáo hạn — toàn bộ hưởng lãi suất CÓ kỳ hạn"

                tong_nhan = so_tien_goc + tong_lai

        # ---------- Hiển thị kết quả ----------
        st.success("Đã tính toán xong!")
        st.markdown(f"**Trạng thái:** {trang_thai}")
        if so_ky_da_gia_han > 0:
            st.info(f"ℹ️ Sổ tiết kiệm đã được ngân hàng **tự động gia hạn {so_ky_da_gia_han} lần** "
                    f"(mỗi lần đúng bằng kỳ hạn {ky_han_thang} tháng đã đăng ký) vì khách hàng không tất toán đúng hạn ban đầu.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Số tiền gốc ban đầu", fmt_vnd(so_tien_goc))
        col2.metric("Tổng tiền lãi", fmt_vnd(tong_lai))
        col3.metric("Tổng số tiền nhận được", fmt_vnd(tong_nhan))

        st.write(f"**Tổng số ngày gửi thực tế:** {(ngay_rut - ngay_gui).days} ngày "
                 f"(từ {ngay_gui.strftime('%d/%m/%Y')} đến {ngay_rut.strftime('%d/%m/%Y')})")

        st.write("---")
        st.subheader("📊 Chi tiết từng kỳ tính lãi")
        if HAS_PANDAS:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Tải bảng chi tiết (CSV)",
                df.to_csv(index=False).encode("utf-8-sig"),
                file_name="chi_tiet_lai_tiet_kiem.csv",
                mime="text/csv",
            )
        else:
            for r in rows:
                st.write(r)

        # ---------- Biểu đồ minh họa tăng trưởng số dư ----------
        if HAS_PANDAS and rows:
            st.write("---")
            st.subheader("📈 Minh họa tăng trưởng số tiền qua từng kỳ")
            so_du = so_tien_goc
            nhan = ["Ban đầu"]
            gia_tri = [so_du]
            for r in rows:
                lai_ky_val = float(r["Tiền lãi kỳ"].replace(" VNĐ", "").replace(",", ""))
                if phuong_thuc == PHUONG_THUC_OPTIONS[0]:
                    so_du += lai_ky_val
                else:
                    so_du = so_tien_goc + sum(
                        float(x["Tiền lãi kỳ"].replace(" VNĐ", "").replace(",", ""))
                        for x in rows[: rows.index(r) + 1]
                    )
                nhan.append(r["Đến ngày"])
                gia_tri.append(so_du)
            chart_df = pd.DataFrame({"Số dư ước tính (VNĐ)": gia_tri}, index=nhan)
            st.line_chart(chart_df)

        # ---------- So sánh nhanh 3 phương thức (nếu rút đúng/sau hạn) ----------
        st.write("---")
        st.subheader("⚖️ So sánh nhanh 3 phương thức nhận lãi (cùng điều kiện gửi)")
        st.caption(
            "So sánh tổng số tiền nhận được cuối cùng nếu áp dụng cùng ngày gửi / ngày rút / kỳ hạn, "
            "chỉ khác phương thức nhận lãi. Chênh lệch (nếu có) chủ yếu đến từ hiệu ứng lãi kép "
            "khi sổ được tự động gia hạn nhiều lần ở phương thức “nhận lãi cuối kỳ”."
        )

        def tinh_tong_nhan(pt):
            if not ky_hoan_thanh and ky_le is not None:
                _, _, so_ngay = ky_le
                return so_tien_goc + so_tien_goc * i_khong_ky_han / 365 * so_ngay
            if pt == PHUONG_THUC_OPTIONS[0]:
                p = so_tien_goc
                for (_, _, so_ngay) in ky_hoan_thanh:
                    p += p * i_ky_han / 365 * so_ngay
                if ky_le is not None:
                    _, _, so_ngay = ky_le
                    p += p * i_khong_ky_han / 365 * so_ngay
                return p
            else:
                tong = so_tien_goc
                for (_, _, so_ngay) in ky_hoan_thanh:
                    tong += so_tien_goc * i_ky_han / 365 * so_ngay
                if ky_le is not None:
                    _, _, so_ngay = ky_le
                    tong += so_tien_goc * i_khong_ky_han / 365 * so_ngay
                return tong

        cA, cB, cC = st.columns(3)
        for col, pt in zip((cA, cB, cC), PHUONG_THUC_OPTIONS):
            with col:
                tong_pt = tinh_tong_nhan(pt)
                is_current = "👉 " if pt == phuong_thuc else ""
                st.metric(f"{is_current}{pt}", fmt_vnd(tong_pt))

st.write("---")
st.caption(
    "⚠️ Đây là công cụ mô phỏng mang tính minh họa, dùng công thức lãi đơn/lãi kép theo ngày thực tế (365 ngày/năm). "
    "Số liệu thực tế có thể khác tùy quy định và biểu lãi suất của từng ngân hàng."
)
