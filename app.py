import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd

# ============================================================
# CẤU HÌNH TRANG
# ============================================================

st.set_page_config(
    page_title="Tính tiền gửi tiết kiệm",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title { font-size: 34px; font-weight: 800; color: #0F4C81; margin-bottom: 5px; }
    .sub-title { color: #666666; font-size: 16px; margin-bottom: 25px; }
    .result-box { padding: 20px; border-radius: 12px; background-color: #F5F9FF;
                  border: 1px solid #D9E8F7; margin-bottom: 15px; }
    .warning-box { padding: 15px; border-radius: 10px; background-color: #FFF8E1; border: 1px solid #FFE082; }
    .success-box { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border: 1px solid #A5D6A7; }
    div[data-testid="stMetricValue"] { font-size: 24px; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HÀM ĐỊNH DẠNG
# ============================================================

def format_money(value: float) -> str:
    return f"{round(value):,.0f} VNĐ"


def format_million(value: float) -> str:
    return f"{value:,.2f} triệu đồng"


# ============================================================
# HẰNG SỐ KỲ HẠN
# ============================================================

TERM_OPTIONS = {
    "Không kỳ hạn": 0,
    "1 tháng": 1, "2 tháng": 2, "3 tháng": 3,
    "6 tháng": 6, "9 tháng": 9, "12 tháng": 12,
    "18 tháng": 18, "24 tháng": 24, "36 tháng": 36
}


# ============================================================
# HÀM LÕI (đã gộp, khử trùng lặp so với bản trước)
# ============================================================

def get_maturity_date(start_date, term_months):
    """Ngày đáo hạn. Không kỳ hạn -> None."""
    if term_months == 0:
        return None
    return start_date + relativedelta(months=term_months)


def get_days(start_date, end_date):
    """Số ngày tính lãi: từ ngày gửi đến TRƯỚC 1 ngày đáo hạn/rút."""
    return (end_date - start_date).days


def simple_interest(principal, annual_rate_percent, days):
    """Lãi đơn: Gốc x Lãi suất năm x Số ngày / 365."""
    if days <= 0:
        return 0.0
    return principal * (annual_rate_percent / 100) * days / 365


def monthly_breakdown(principal, annual_rate_percent, start_date, end_date):
    """
    Chia [start_date, end_date) thành các đoạn theo từng tháng để tính lãi.
    Trả về (tổng lãi, danh sách kỳ). Mỗi kỳ có cờ full_month cho biết
    kỳ đó đã tròn 1 tháng hay là đoạn lẻ cuối cùng (chưa đến kỳ trả lãi).
    """
    rows = []
    total_interest = 0.0
    current = start_date

    while current < end_date:
        next_month = current + relativedelta(months=1)
        period_end = min(next_month, end_date)
        days = get_days(current, period_end)
        interest = simple_interest(principal, annual_rate_percent, days)
        total_interest += interest

        rows.append({
            "Kỳ": len(rows) + 1,
            "Từ ngày": current.strftime("%d/%m/%Y"),
            "Đến trước ngày": period_end.strftime("%d/%m/%Y"),
            "Số ngày": days,
            "Tiền lãi": interest,
            "full_month": period_end == next_month
        })
        current = period_end

    return total_interest, rows


def renewal_periods(principal, term_rate, non_term_rate, start_date, withdrawal_date, term_months):
    """
    Tự động tái tục theo đúng kỳ hạn ban đầu cho tới ngày rút.

    TỐI ƯU so với bản gốc: nếu kỳ CUỐI CÙNG bị rút giữa chừng (chưa
    tới ngày đáo hạn của kỳ tái tục đó) thì đoạn đó phải hưởng lãi
    suất KHÔNG kỳ hạn (đúng theo quy tắc "rút trước hạn -> lãi suất
    không kỳ hạn"), thay vì tính nhầm theo lãi suất có kỳ hạn như
    bản trước.
    """
    periods = []
    current_start = start_date

    while current_start < withdrawal_date:
        maturity = current_start + relativedelta(months=term_months)
        period_end = min(maturity, withdrawal_date)
        is_full_period = period_end == maturity

        applied_rate = term_rate if is_full_period else non_term_rate
        days = get_days(current_start, period_end)
        interest = simple_interest(principal, applied_rate, days)

        periods.append({
            "Kỳ": len(periods) + 1,
            "Ngày bắt đầu": current_start,
            "Ngày kết thúc": period_end,
            "Số ngày": days,
            "Lãi suất áp dụng": applied_rate,
            "Tiền lãi": interest,
            "Đủ kỳ hạn": is_full_period
        })
        current_start = period_end

    return periods


# ============================================================
# HEADER
# ============================================================

st.markdown('<div class="main-title">🏦 HỆ THỐNG TÍNH TIỀN GỬI TIẾT KIỆM</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Mô phỏng tiền gốc, tiền lãi, đáo hạn, rút trước hạn '
    'và tự động tái tục</div>',
    unsafe_allow_html=True
)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Cấu hình hệ thống")
    st.selectbox("Cơ sở tính lãi", [365], index=0, help="Phiên bản này dùng 365 ngày/năm.")
    st.divider()
    st.info(
        """
        **Quy tắc tính:**

        • Lãi theo số ngày thực tế.

        • Không tính ngày đáo hạn/ngày rút tiền.

        • Rút trước hạn (kể cả rút giữa một kỳ tái tục) → toàn bộ
          thời gian của kỳ đó dùng lãi suất **không kỳ hạn**.

        • Đến hạn không rút → tự động tái tục đúng kỳ hạn ban đầu.
        """
    )

# ============================================================
# NHẬP THÔNG TIN
# ============================================================

st.subheader("1️⃣ Thông tin tiền gửi")

col1, col2, col3 = st.columns(3)

QUICK_AMOUNTS = [50, 100, 200, 500, 1000, 2000]  # triệu đồng

if "principal_million" not in st.session_state:
    st.session_state.principal_million = 500.0

with col1:
    principal_million = st.number_input(
        "💰 Số tiền khách hàng gửi (triệu đồng)",
        min_value=0.01, step=10.0, format="%.2f",
        key="principal_million"
    )

    st.caption("Chọn nhanh:")
    quick_cols = st.columns(len(QUICK_AMOUNTS))
    for i, amt in enumerate(QUICK_AMOUNTS):
        label = f"{amt} tr" if amt < 1000 else f"{amt // 1000} tỷ"
        if quick_cols[i].button(label, use_container_width=True, key=f"quick_{amt}"):
            st.session_state.principal_million = float(amt)
            st.rerun()

    term_text = st.selectbox("📅 Kỳ hạn gửi tiền", list(TERM_OPTIONS.keys()), index=3)
    term_months = TERM_OPTIONS[term_text]

with col2:
    term_rate = st.number_input(
        "📈 Lãi suất có kỳ hạn (%/năm)",
        min_value=0.0, max_value=100.0, value=5.0, step=0.01, format="%.2f"
    )
    non_term_rate = st.number_input(
        "📉 Lãi suất không kỳ hạn (%/năm)",
        min_value=0.0, max_value=100.0, value=0.2, step=0.01, format="%.2f"
    )

with col3:
    start_date = st.date_input("📌 Ngày gửi tiền", value=date.today())
    withdrawal_date = st.date_input(
        "🏧 Ngày rút tiền",
        value=date.today() + relativedelta(months=3)
    )

# Xem trước ngày đáo hạn / trạng thái (cập nhật ngay khi đổi input)
if term_months > 0:
    preview_maturity = get_maturity_date(start_date, term_months)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Ngày gửi", start_date.strftime("%d/%m/%Y"))
    with c2:
        st.metric("Ngày đáo hạn (lần đầu)", preview_maturity.strftime("%d/%m/%Y"))
    with c3:
        if withdrawal_date < preview_maturity:
            st.error("⚠️ RÚT TRƯỚC HẠN")
        elif withdrawal_date == preview_maturity:
            st.success("✅ RÚT ĐÚNG NGÀY ĐÁO HẠN")
        else:
            st.warning("🔄 Rút sau đáo hạn → có tái tục")

# ============================================================
# PHƯƠNG THỨC NHẬN LÃI
# ============================================================

st.subheader("2️⃣ Phương thức nhận tiền lãi")
interest_method = st.radio(
    "Chọn cách nhận tiền lãi (áp dụng khi gửi đủ kỳ hạn):",
    ["💵 Nhận lãi trước", "📆 Nhận lãi hàng tháng", "🏁 Nhận lãi cuối kỳ"],
    horizontal=True
)

st.divider()
calculate_button = st.button("🧮 TÍNH TOÁN", type="primary", use_container_width=True)

# ============================================================
# XỬ LÝ TÍNH TOÁN
# ============================================================

if calculate_button:

    if principal_million <= 0:
        st.error("Số tiền gửi phải lớn hơn 0.")
        st.stop()

    if withdrawal_date <= start_date:
        st.error("Ngày rút tiền phải lớn hơn ngày gửi tiền.")
        st.stop()

    principal = principal_million * 1_000_000

    # --------------------------------------------------------
    # KHÔNG KỲ HẠN
    # --------------------------------------------------------
    if term_months == 0:
        st.warning("Tiền gửi không kỳ hạn → áp dụng lãi suất không kỳ hạn cho toàn bộ thời gian.")

        days = get_days(start_date, withdrawal_date)
        interest = simple_interest(principal, non_term_rate, days)
        total_receive = principal + interest

        st.subheader("📊 KẾT QUẢ")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tiền gốc", format_million(principal / 1_000_000))
        c2.metric("Số ngày gửi", f"{days} ngày")
        c3.metric("Tiền lãi", format_million(interest / 1_000_000))
        c4.metric("Tổng nhận", format_million(total_receive / 1_000_000))

        st.success(f"Khách hàng nhận được tổng cộng **{format_money(total_receive)}**.")

        report_df = pd.DataFrame([{
            "Loại tiền gửi": "Không kỳ hạn",
            "Ngày gửi": start_date.strftime("%d/%m/%Y"),
            "Ngày rút": withdrawal_date.strftime("%d/%m/%Y"),
            "Số ngày": days,
            "Lãi suất áp dụng (%/năm)": non_term_rate,
            "Tiền gốc (VNĐ)": round(principal),
            "Tiền lãi (VNĐ)": round(interest),
            "Tổng nhận (VNĐ)": round(total_receive)
        }])
        st.download_button(
            "⬇️ Tải kết quả (CSV)",
            report_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="ket_qua_tiet_kiem.csv",
            mime="text/csv"
        )
        st.stop()

    # --------------------------------------------------------
    # CÓ KỲ HẠN
    # --------------------------------------------------------
    maturity_date = get_maturity_date(start_date, term_months)
    early_withdrawal = withdrawal_date < maturity_date
    exact_maturity = withdrawal_date == maturity_date

    # ---------------- RÚT TRƯỚC HẠN (kỳ đầu tiên) ----------------
    if early_withdrawal:
        days = get_days(start_date, withdrawal_date)
        interest = simple_interest(principal, non_term_rate, days)
        total_receive = principal + interest

        st.error("⚠️ KHÁCH HÀNG RÚT TRƯỚC HẠN")
        st.warning(
            f"Toàn bộ **{days} ngày** gửi được tính lại theo lãi suất "
            f"không kỳ hạn **{non_term_rate:.2f}%/năm**, không phụ thuộc "
            f"phương thức nhận lãi đã chọn ban đầu."
        )

        st.subheader("📊 KẾT QUẢ RÚT TRƯỚC HẠN")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tiền gốc", format_million(principal / 1_000_000))
        c2.metric("Số ngày gửi", f"{days} ngày")
        c3.metric("Tiền lãi", format_million(interest / 1_000_000))
        c4.metric("TỔNG NHẬN", format_million(total_receive / 1_000_000))

        st.markdown(
            f"""
            <div class="result-box">

            ### 💰 Tổng số tiền khách hàng nhận được

            **{format_money(total_receive)}**

            - Tiền gốc: **{format_money(principal)}**
            - Tiền lãi: **{format_money(interest)}**
            - Lãi suất áp dụng: **{non_term_rate:.2f}%/năm**
            - Số ngày thực gửi: **{days} ngày**

            </div>
            """,
            unsafe_allow_html=True
        )

        st.subheader("🧮 Chi tiết công thức")
        st.latex(r"Lãi = Tiền\ gốc \times \frac{Lãi\ suất}{100} \times \frac{Số\ ngày}{365}")
        st.write(f"Lãi = {principal:,.0f} × {non_term_rate:.2f}% × {days} / 365 = **{format_money(interest)}**")

        report_df = pd.DataFrame([{
            "Trạng thái": "Rút trước hạn",
            "Ngày gửi": start_date.strftime("%d/%m/%Y"),
            "Ngày rút": withdrawal_date.strftime("%d/%m/%Y"),
            "Số ngày": days,
            "Lãi suất áp dụng (%/năm)": non_term_rate,
            "Tiền gốc (VNĐ)": round(principal),
            "Tiền lãi (VNĐ)": round(interest),
            "Tổng nhận (VNĐ)": round(total_receive)
        }])
        st.download_button(
            "⬇️ Tải kết quả (CSV)",
            report_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="ket_qua_rut_truoc_han.csv",
            mime="text/csv"
        )

    # ---------------- RÚT ĐÚNG HẠN ----------------
    elif exact_maturity:
        days = get_days(start_date, maturity_date)
        st.success("🏁 Khách hàng gửi đúng kỳ hạn.")

        if interest_method == "💵 Nhận lãi trước":
            interest = simple_interest(principal, term_rate, days)
            total_cash_received = principal + interest

            st.subheader("📊 KẾT QUẢ")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tiền gốc", format_million(principal / 1_000_000))
            c2.metric("Tiền lãi", format_million(interest / 1_000_000))
            c3.metric("Nhận lúc gửi", format_million(interest / 1_000_000))
            c4.metric("Tổng tiền nhận", format_million(total_cash_received / 1_000_000))

            st.info(
                f"""
                **Phương thức nhận lãi trước**

                Khách hàng nhận trước tiền lãi: **{format_money(interest)}**

                Khi đáo hạn khách hàng nhận lại tiền gốc: **{format_money(principal)}**

                Tổng dòng tiền khách hàng nhận: **{format_money(total_cash_received)}**
                """
            )

            summary_rows = [{
                "Mốc": "Ngày gửi (nhận lãi trước)",
                "Số tiền (VNĐ)": round(interest)
            }, {
                "Mốc": "Ngày đáo hạn (nhận gốc)",
                "Số tiền (VNĐ)": round(principal)
            }]

        elif interest_method == "📆 Nhận lãi hàng tháng":
            total_interest, rows = monthly_breakdown(principal, term_rate, start_date, maturity_date)
            total_cash_received = principal + total_interest

            st.subheader("📊 KẾT QUẢ NHẬN LÃI HÀNG THÁNG")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tiền gốc", format_million(principal / 1_000_000))
            c2.metric("Tổng tiền lãi", format_million(total_interest / 1_000_000))
            c3.metric("Số kỳ nhận lãi", f"{len(rows)} kỳ")
            c4.metric("Tổng dòng tiền nhận", format_million(total_cash_received / 1_000_000))

            display_df = pd.DataFrame(rows).drop(columns=["full_month"])
            display_df["Tiền lãi"] = display_df["Tiền lãi"].map(format_money)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            summary_rows = [{
                "Mốc": f"Kỳ {r['Kỳ']} ({r['Từ ngày']} - {r['Đến trước ngày']})",
                "Số tiền (VNĐ)": round(r["Tiền lãi"])
            } for r in rows]
            summary_rows.append({"Mốc": "Ngày đáo hạn (nhận gốc)", "Số tiền (VNĐ)": round(principal)})

        else:  # Nhận lãi cuối kỳ
            interest = simple_interest(principal, term_rate, days)
            total_cash_received = principal + interest

            st.subheader("📊 KẾT QUẢ NHẬN LÃI CUỐI KỲ")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tiền gốc", format_million(principal / 1_000_000))
            c2.metric("Số ngày", f"{days} ngày")
            c3.metric("Tiền lãi", format_million(interest / 1_000_000))
            c4.metric("TỔNG NHẬN", format_million(total_cash_received / 1_000_000))

            st.markdown(
                f"""
                <div class="success-box">

                ### 💰 Tổng tiền khách hàng nhận

                **{format_money(total_cash_received)}**

                - Gốc: **{format_money(principal)}**
                - Lãi: **{format_money(interest)}**
                - Lãi suất: **{term_rate:.2f}%/năm**
                - Số ngày: **{days} ngày**

                </div>
                """,
                unsafe_allow_html=True
            )

            summary_rows = [{
                "Mốc": "Ngày đáo hạn (nhận gốc + lãi)",
                "Số tiền (VNĐ)": round(total_cash_received)
            }]

        report_df = pd.DataFrame(summary_rows)
        st.download_button(
            "⬇️ Tải kết quả (CSV)",
            report_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="ket_qua_dao_han.csv",
            mime="text/csv"
        )

    # ---------------- RÚT SAU ĐÁO HẠN → TÁI TỤC ----------------
    else:
        st.warning("🔄 Khách hàng không rút tại ngày đáo hạn. Khoản tiền gửi được tự động tái tục.")

        periods = renewal_periods(principal, term_rate, non_term_rate,
                                   start_date, withdrawal_date, term_months)
        total_interest = sum(p["Tiền lãi"] for p in periods)
        total_cash_received = principal + total_interest
        last_period_full = periods[-1]["Đủ kỳ hạn"] if periods else True

        st.subheader("🔄 LỊCH SỬ TÁI TỤC")
        if not last_period_full:
            st.info(
                "ℹ️ Kỳ cuối cùng khách hàng rút **giữa chừng** (chưa tới ngày tái tục kế "
                "tiếp) nên đoạn này được tính theo **lãi suất không kỳ hạn**."
            )

        period_display = [{
            "Kỳ": p["Kỳ"],
            "Ngày bắt đầu": p["Ngày bắt đầu"].strftime("%d/%m/%Y"),
            "Ngày kết thúc": p["Ngày kết thúc"].strftime("%d/%m/%Y"),
            "Số ngày": p["Số ngày"],
            "Lãi suất áp dụng": f"{p['Lãi suất áp dụng']:.2f}%",
            "Tiền lãi": format_money(p["Tiền lãi"]),
            "Trạng thái": "Đủ kỳ hạn (tái tục)" if p["Đủ kỳ hạn"] else "Rút giữa kỳ (không kỳ hạn)"
        } for p in periods]

        st.dataframe(pd.DataFrame(period_display), use_container_width=True, hide_index=True)

        st.subheader("📊 TỔNG KẾT KHOẢN TIỀN GỬI")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tiền gốc", format_million(principal / 1_000_000))
        c2.metric("Số lần tái tục", f"{max(len(periods) - 1, 0)} lần")
        c3.metric("Tổng tiền lãi", format_million(total_interest / 1_000_000))
        c4.metric("TỔNG NHẬN", format_million(total_cash_received / 1_000_000))

        st.success(
            f"""
            💰 Khi khách hàng rút ngày **{withdrawal_date.strftime('%d/%m/%Y')}**,
            tổng số tiền nhận được là:

            ### {format_money(total_cash_received)}

            Trong đó: **Tiền gốc:** {format_money(principal)} —
            **Tổng tiền lãi:** {format_money(total_interest)}
            """
        )

        report_df = pd.DataFrame(period_display)
        st.download_button(
            "⬇️ Tải lịch sử tái tục (CSV)",
            report_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="lich_su_tai_tuc.csv",
            mime="text/csv"
        )

# ============================================================
# HƯỚNG DẪN & CÔNG THỨC
# ============================================================

st.divider()

with st.expander("📖 Hướng dẫn sử dụng"):
    st.markdown("""
    **1. Số tiền gửi** — nhập theo triệu đồng, ví dụ `500` = 500.000.000 VNĐ.

    **2. Lãi suất** — nhập lãi suất có kỳ hạn và không kỳ hạn (%/năm).

    **3. Kỳ hạn** — chọn từ Không kỳ hạn đến 36 tháng.

    **4. Phương thức nhận lãi** (áp dụng khi gửi đủ kỳ hạn):
    - *Nhận lãi trước*: nhận lãi ngay khi gửi, đáo hạn nhận lại gốc.
    - *Nhận lãi hàng tháng*: lãi được trả theo từng tháng.
    - *Nhận lãi cuối kỳ*: nhận cả gốc và lãi khi đáo hạn.

    **5. Rút trước hạn** — nếu `Ngày rút < Ngày đáo hạn (gần nhất)`, toàn bộ
    thời gian của kỳ đó được tính lại theo lãi suất **không kỳ hạn**, dù
    trước đó chọn phương thức nào.

    **6. Tự động tái tục** — nếu `Ngày rút > Ngày đáo hạn`, hệ thống chia
    thành nhiều kỳ bằng đúng kỳ hạn ban đầu. Nếu kỳ cuối cùng bị rút giữa
    chừng (chưa đủ một kỳ tái tục), đoạn đó cũng được tính theo lãi suất
    không kỳ hạn — đây là điểm đã được sửa/tối ưu so với bản tính thông thường.
    """)

with st.expander("🧮 Công thức tính lãi"):
    st.markdown("""
    **Tiền lãi = Tiền gốc × Lãi suất năm × Số ngày / 365**

    **Tổng tiền nhận = Tiền gốc + Tiền lãi**

    - Rút trước hạn (hoặc rút giữa một kỳ tái tục) → dùng lãi suất không kỳ hạn.
    - Đến hạn không rút → tự động tái tục đúng kỳ hạn ban đầu.
    """)

st.divider()
st.caption("🏦 Hệ thống mô phỏng tính tiền gửi tiết kiệm | Streamlit | Cơ sở tính lãi 365 ngày/năm")
