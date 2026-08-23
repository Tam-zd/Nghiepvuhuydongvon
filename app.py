import streamlit as st
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import math


# ============================================================
# CẤU HÌNH TRANG
# ============================================================

st.set_page_config(
    page_title="Tính tiền gửi tiết kiệm",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CSS GIAO DIỆN
# ============================================================

st.markdown("""
<style>

    .main-title {
        font-size: 34px;
        font-weight: 800;
        color: #0F4C81;
        margin-bottom: 5px;
    }

    .sub-title {
        color: #666666;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .result-box {
        padding: 20px;
        border-radius: 12px;
        background-color: #F5F9FF;
        border: 1px solid #D9E8F7;
        margin-bottom: 15px;
    }

    .warning-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #FFF8E1;
        border: 1px solid #FFE082;
    }

    .success-box {
        padding: 15px;
        border-radius: 10px;
        background-color: #E8F5E9;
        border: 1px solid #A5D6A7;
    }

    div[data-testid="stMetricValue"] {
        font-size: 25px;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# HÀM ĐỊNH DẠNG
# ============================================================

def format_money(value):
    """Định dạng tiền Việt Nam."""
    return f"{value:,.0f} VNĐ"


def format_million(value):
    """Định dạng tiền theo triệu đồng."""
    return f"{value:,.2f} triệu đồng"


def format_percent(value):
    return f"{value:.2f}%"


# ============================================================
# HÀM TÍNH KỲ HẠN
# ============================================================

TERM_OPTIONS = {
    "Không kỳ hạn": 0,
    "1 tháng": 1,
    "2 tháng": 2,
    "3 tháng": 3,
    "6 tháng": 6,
    "9 tháng": 9,
    "12 tháng": 12,
    "18 tháng": 18,
    "24 tháng": 24,
    "36 tháng": 36
}


def get_maturity_date(start_date, term_months):
    """
    Tính ngày đáo hạn.

    Ví dụ:
    Gửi 01/01 kỳ hạn 3 tháng
    -> đáo hạn 01/04.
    """

    if term_months == 0:
        return None

    return start_date + relativedelta(months=term_months)


def get_days(start_date, end_date):
    """
    Số ngày tính lãi.

    Theo yêu cầu:
    bắt đầu từ ngày gửi
    đến trước 1 ngày ngày rút/đáo hạn.

    Ví dụ:
    01/01 -> 01/04
    = 90 ngày, không tính ngày 01/04.
    """

    return (end_date - start_date).days


# ============================================================
# HÀM TÍNH LÃI
# ============================================================

def calculate_interest(principal, annual_rate, days):
    """
    Lãi đơn theo số ngày.

    Lãi = Gốc × Lãi suất năm × Số ngày / 365
    """

    if days <= 0:
        return 0

    return principal * (annual_rate / 100) * days / 365


# ============================================================
# TÍNH LÃI THEO TỪNG THÁNG
# ============================================================

def calculate_monthly_interest(
    principal,
    annual_rate,
    start_date,
    end_date
):
    """
    Chia thời gian thành từng tháng để tính lãi hàng tháng.

    Tiền lãi mỗi tháng được tính trên số ngày thực tế của tháng đó.
    """

    rows = []

    current_date = start_date
    total_interest = 0

    while current_date < end_date:

        next_month = current_date + relativedelta(months=1)

        # Không vượt quá ngày kết thúc
        period_end = min(next_month, end_date)

        days = get_days(current_date, period_end)

        interest = calculate_interest(
            principal,
            annual_rate,
            days
        )

        total_interest += interest

        rows.append({
            "Kỳ": len(rows) + 1,
            "Từ ngày": current_date.strftime("%d/%m/%Y"),
            "Đến trước ngày": period_end.strftime("%d/%m/%Y"),
            "Số ngày": days,
            "Tiền lãi": interest
        })

        current_date = period_end

    return total_interest, rows


# ============================================================
# TÍNH LẠI SUẤT TRƯỚC HẠN
# ============================================================

def calculate_early_withdrawal(
    principal,
    non_term_rate,
    start_date,
    withdrawal_date
):

    days = get_days(
        start_date,
        withdrawal_date
    )

    interest = calculate_interest(
        principal,
        non_term_rate,
        days
    )

    total = principal + interest

    return {
        "days": days,
        "interest": interest,
        "total": total
    }


# ============================================================
# TÍNH TÁI TỤC
# ============================================================

def calculate_renewal_periods(
    principal,
    annual_rate,
    start_date,
    withdrawal_date,
    term_months
):
    """
    Nếu khách hàng không rút khi đến hạn:
    ngân hàng tự động gia hạn đúng kỳ hạn.

    Ví dụ:
    gửi 01/01/2026 kỳ hạn 3 tháng
    rút 10/10/2026

    Các kỳ:
    01/01 -> 01/04
    01/04 -> 01/07
    01/07 -> 01/10
    01/10 -> 10/10
    """

    periods = []

    current_start = start_date

    while current_start < withdrawal_date:

        maturity = current_start + relativedelta(
            months=term_months
        )

        period_end = min(
            maturity,
            withdrawal_date
        )

        days = get_days(
            current_start,
            period_end
        )

        interest = calculate_interest(
            principal,
            annual_rate,
            days
        )

        periods.append({
            "Kỳ": len(periods) + 1,
            "Ngày bắt đầu": current_start,
            "Ngày kết thúc": period_end,
            "Số ngày": days,
            "Tiền gốc": principal,
            "Lãi suất": annual_rate,
            "Tiền lãi": interest,
            "Đáo hạn": period_end == maturity
        })

        current_start = period_end

    return periods


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🏦 HỆ THỐNG TÍNH TIỀN GỬI TIẾT KIỆM</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    'Mô phỏng tiền gốc, tiền lãi, đáo hạn, rút trước hạn và tự động tái tục'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Cấu hình hệ thống")

    basis_days = st.selectbox(
        "Cơ sở tính lãi",
        [365],
        index=0,
        help="Phiên bản này sử dụng 365 ngày/năm."
    )

    st.divider()

    st.info(
        """
        **Quy tắc tính:**

        • Lãi theo ngày thực tế.

        • Không tính ngày đáo hạn/rút tiền.

        • Rút trước hạn → dùng lãi suất không kỳ hạn.

        • Đến hạn không rút → tự động tái tục.

        • Kỳ hạn tái tục = kỳ hạn ban đầu.
        """
    )


# ============================================================
# NHẬP THÔNG TIN
# ============================================================

st.subheader("1️⃣ Thông tin tiền gửi")

col1, col2, col3 = st.columns(3)

with col1:

    principal_million = st.number_input(
        "💰 Số tiền khách hàng gửi (triệu đồng)",
        min_value=0.01,
        value=500.0,
        step=10.0,
        format="%.2f"
    )

    term_text = st.selectbox(
        "📅 Kỳ hạn gửi tiền",
        list(TERM_OPTIONS.keys()),
        index=3
    )

    term_months = TERM_OPTIONS[term_text]


with col2:

    term_rate = st.number_input(
        "📈 Lãi suất có kỳ hạn (%/năm)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.01,
        format="%.2f"
    )

    non_term_rate = st.number_input(
        "📉 Lãi suất không kỳ hạn (%/năm)",
        min_value=0.0,
        max_value=100.0,
        value=0.2,
        step=0.01,
        format="%.2f"
    )


with col3:

    start_date = st.date_input(
        "📌 Ngày gửi tiền",
        value=date.today()
    )

    withdrawal_date = st.date_input(
        "🏧 Ngày rút tiền",
        value=date.today() + relativedelta(months=3)
    )


# ============================================================
# HIỂN THỊ NGÀY ĐÁO HẠN
# ============================================================

if term_months > 0:

    maturity_date = get_maturity_date(
        start_date,
        term_months
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Ngày gửi",
            start_date.strftime("%d/%m/%Y")
        )

    with c2:
        st.metric(
            "Ngày đáo hạn",
            maturity_date.strftime("%d/%m/%Y")
        )

    with c3:

        if withdrawal_date < maturity_date:

            st.error("⚠️ KHÁCH HÀNG RÚT TRƯỚC HẠN")

        elif withdrawal_date == maturity_date:

            st.success("✅ KHÁCH HÀNG RÚT ĐÚNG NGÀY ĐÁO HẠN")

        else:

            st.warning(
                "🔄 Khách hàng rút sau ngày đáo hạn → có tái tục"
            )


# ============================================================
# PHƯƠNG THỨC NHẬN LÃI
# ============================================================

st.subheader("2️⃣ Phương thức nhận tiền lãi")

interest_method = st.radio(
    "Chọn cách nhận tiền lãi:",
    [
        "💵 Nhận lãi trước",
        "📆 Nhận lãi hàng tháng",
        "🏁 Nhận lãi cuối kỳ"
    ],
    horizontal=True
)


# ============================================================
# NÚT TÍNH TOÁN
# ============================================================

st.divider()

calculate_button = st.button(
    "🧮 TÍNH TOÁN",
    type="primary",
    use_container_width=True
)


# ============================================================
# XỬ LÝ TÍNH TOÁN
# ============================================================

if calculate_button:

    # --------------------------------------------------------
    # KIỂM TRA DỮ LIỆU
    # --------------------------------------------------------

    if principal_million <= 0:

        st.error("Số tiền gửi phải lớn hơn 0.")

        st.stop()

    if withdrawal_date <= start_date:

        st.error(
            "Ngày rút tiền phải lớn hơn ngày gửi tiền."
        )

        st.stop()

    if term_months == 0:

        st.warning(
            "Bạn đang chọn tiền gửi không kỳ hạn. "
            "Hệ thống sẽ sử dụng lãi suất không kỳ hạn."
        )

    # Chuyển triệu đồng -> VNĐ
    principal = principal_million * 1_000_000

    # --------------------------------------------------------
    # TRƯỜNG HỢP KHÔNG KỲ HẠN
    # --------------------------------------------------------

    if term_months == 0:

        actual_rate = non_term_rate

        days = get_days(
            start_date,
            withdrawal_date
        )

        interest = calculate_interest(
            principal,
            actual_rate,
            days
        )

        total_receive = principal + interest

        st.subheader("📊 KẾT QUẢ")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Tiền gốc",
                format_million(principal / 1_000_000)
            )

        with col2:
            st.metric(
                "Số ngày gửi",
                f"{days} ngày"
            )

        with col3:
            st.metric(
                "Tiền lãi",
                format_million(interest / 1_000_000)
            )

        with col4:
            st.metric(
                "Tổng nhận",
                format_million(total_receive / 1_000_000)
            )

        st.success(
            f"Khách hàng nhận được tổng cộng "
            f"**{format_money(total_receive)}**."
        )

        st.stop()

    # --------------------------------------------------------
    # XÁC ĐỊNH TRẠNG THÁI
    # --------------------------------------------------------

    maturity_date = get_maturity_date(
        start_date,
        term_months
    )

    early_withdrawal = withdrawal_date < maturity_date
    exact_maturity = withdrawal_date == maturity_date
    after_maturity = withdrawal_date > maturity_date

    # --------------------------------------------------------
    # RÚT TRƯỚC HẠN
    # --------------------------------------------------------

    if early_withdrawal:

        result = calculate_early_withdrawal(
            principal,
            non_term_rate,
            start_date,
            withdrawal_date
        )

        days = result["days"]
        interest = result["interest"]
        total_receive = result["total"]

        st.error(
            "⚠️ KHÁCH HÀNG RÚT TRƯỚC HẠN"
        )

        st.warning(
            f"Theo quy tắc hệ thống, toàn bộ thời gian gửi "
            f"được tính theo lãi suất không kỳ hạn "
            f"**{non_term_rate:.2f}%/năm**."
        )

        # -----------------------------------------------
        # KẾT QUẢ
        # -----------------------------------------------

        st.subheader("📊 KẾT QUẢ RÚT TRƯỚC HẠN")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Tiền gốc",
                format_million(principal / 1_000_000)
            )

        with col2:
            st.metric(
                "Số ngày gửi",
                f"{days} ngày"
            )

        with col3:
            st.metric(
                "Tiền lãi",
                format_million(interest / 1_000_000)
            )

        with col4:
            st.metric(
                "TỔNG NHẬN",
                format_million(total_receive / 1_000_000)
            )

        st.markdown(
            f"""
            <div class="result-box">

            ### 💰 Tổng số tiền khách hàng nhận được

            **{format_money(total_receive)}**

            Trong đó:

            - Tiền gốc: **{format_money(principal)}**
            - Tiền lãi: **{format_money(interest)}**
            - Lãi suất áp dụng: **{non_term_rate:.2f}%/năm**
            - Số ngày thực gửi: **{days} ngày**

            </div>
            """,
            unsafe_allow_html=True
        )

        # -----------------------------------------------
        # CÔNG THỨC
        # -----------------------------------------------

        st.subheader("🧮 Chi tiết công thức")

        st.latex(
            r"""
            Lãi =
            Tiền\ gốc
            \times
            \frac{Lãi\ suất}{100}
            \times
            \frac{Số\ ngày}{365}
            """
        )

        st.write(
            f"""
            **Lãi = {principal:,.0f} × "
            f"{non_term_rate:.2f}% × {days} / 365"
            """
        )

    # --------------------------------------------------------
    # RÚT ĐÚNG HẠN
    # --------------------------------------------------------

    elif exact_maturity:

        days = get_days(
            start_date,
            maturity_date
        )

        # -----------------------------------------------
        # LÃI TRƯỚC
        # -----------------------------------------------

        if interest_method == "💵 Nhận lãi trước":

            interest = calculate_interest(
                principal,
                term_rate,
                days
            )

            # Lãi đã được nhận từ đầu.
            # Khi đáo hạn nhận lại gốc.
            amount_at_maturity = principal

            total_cash_received = principal + interest

            st.success(
                "🏁 Khách hàng gửi đúng kỳ hạn."
            )

            st.subheader("📊 KẾT QUẢ")

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "Tiền gốc",
                    format_million(principal / 1_000_000)
                )

            with c2:
                st.metric(
                    "Tiền lãi",
                    format_million(interest / 1_000_000)
                )

            with c3:
                st.metric(
                    "Nhận lúc gửi",
                    format_million(interest / 1_000_000)
                )

            with c4:
                st.metric(
                    "Tổng tiền nhận",
                    format_million(
                        total_cash_received / 1_000_000
                    )
                )

            st.info(
                f"""
                **Phương thức nhận lãi trước**

                Khách hàng nhận trước tiền lãi:

                **{format_money(interest)}**

                Khi đáo hạn khách hàng nhận lại tiền gốc:

                **{format_money(principal)}**

                Tổng dòng tiền khách hàng nhận:

                **{format_money(total_cash_received)}**
                """
            )

        # -----------------------------------------------
        # LÃI HÀNG THÁNG
        # -----------------------------------------------

        elif interest_method == "📆 Nhận lãi hàng tháng":

            total_interest, monthly_rows = calculate_monthly_interest(
                principal,
                term_rate,
                start_date,
                maturity_date
            )

            total_cash_received = (
                principal + total_interest
            )

            st.success(
                "🏁 Khách hàng gửi đúng kỳ hạn."
            )

            st.subheader(
                "📊 KẾT QUẢ NHẬN LÃI HÀNG THÁNG"
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "Tiền gốc",
                    format_million(principal / 1_000_000)
                )

            with c2:
                st.metric(
                    "Tổng tiền lãi",
                    format_million(
                        total_interest / 1_000_000
                    )
                )

            with c3:
                st.metric(
                    "Số kỳ nhận lãi",
                    f"{len(monthly_rows)} kỳ"
                )

            with c4:
                st.metric(
                    "Tổng dòng tiền nhận",
                    format_million(
                        total_cash_received / 1_000_000
                    )
                )

            st.dataframe(
                pd.DataFrame(monthly_rows).assign(
                    **{
                        "Tiền lãi": lambda df:
                        df["Tiền lãi"].map(
                            lambda x: format_money(x)
                        )
                    }
                ),
                use_container_width=True,
                hide_index=True
            )

        # -----------------------------------------------
        # LÃI CUỐI KỲ
        # -----------------------------------------------

        else:

            interest = calculate_interest(
                principal,
                term_rate,
                days
            )

            total_cash_received = (
                principal + interest
            )

            st.success(
                "🏁 Khách hàng gửi đúng kỳ hạn."
            )

            st.subheader(
                "📊 KẾT QUẢ NHẬN LÃI CUỐI KỲ"
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "Tiền gốc",
                    format_million(principal / 1_000_000)
                )

            with c2:
                st.metric(
                    "Số ngày",
                    f"{days} ngày"
                )

            with c3:
                st.metric(
                    "Tiền lãi",
                    format_million(
                        interest / 1_000_000
                    )
                )

            with c4:
                st.metric(
                    "TỔNG NHẬN",
                    format_million(
                        total_cash_received / 1_000_000
                    )
                )

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

    # --------------------------------------------------------
    # RÚT SAU NGÀY ĐÁO HẠN → TÁI TỤC
    # --------------------------------------------------------

    else:

        st.warning(
            "🔄 Khách hàng không rút tại ngày đáo hạn. "
            "Khoản tiền gửi được tự động gia hạn."
        )

        periods = calculate_renewal_periods(
            principal,
            term_rate,
            start_date,
            withdrawal_date,
            term_months
        )

        # Tổng lãi
        total_interest = sum(
            x["Tiền lãi"]
            for x in periods
        )

        total_cash_received = (
            principal + total_interest
        )

        st.subheader(
            "🔄 LỊCH SỬ TÁI TỤC"
        )

        period_display = []

        for p in periods:

            period_display.append({
                "Kỳ": p["Kỳ"],
                "Ngày bắt đầu":
                    p["Ngày bắt đầu"].strftime("%d/%m/%Y"),
                "Ngày kết thúc":
                    p["Ngày kết thúc"].strftime("%d/%m/%Y"),
                "Số ngày": p["Số ngày"],
                "Lãi suất":
                    f"{p['Lãi suất']:.2f}%",
                "Tiền lãi":
                    format_money(p["Tiền lãi"]),
                "Trạng thái":
                    "Đáo hạn" if p["Đáo hạn"]
                    else "Rút tiền"
            })

        st.dataframe(
            pd.DataFrame(period_display),
            use_container_width=True,
            hide_index=True
        )

        # -----------------------------------------------
        # KẾT QUẢ
        # -----------------------------------------------

        st.subheader(
            "📊 TỔNG KẾT KHOẢN TIỀN GỬI"
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Tiền gốc",
                format_million(
                    principal / 1_000_000
                )
            )

        with c2:
            st.metric(
                "Số lần tái tục",
                f"{max(len(periods) - 1, 0)} lần"
            )

        with c3:
            st.metric(
                "Tổng tiền lãi",
                format_million(
                    total_interest / 1_000_000
                )
            )

        with c4:
            st.metric(
                "TỔNG NHẬN",
                format_million(
                    total_cash_received / 1_000_000
                )
            )

        st.success(
            f"""
            💰 Khi khách hàng rút ngày
            **{withdrawal_date.strftime('%d/%m/%Y')}**,

            tổng số tiền nhận được là:

            ### {format_money(total_cash_received)}

            Trong đó:

            **Tiền gốc:** {format_money(principal)}

            **Tổng tiền lãi:** {format_money(total_interest)}
            """
        )


# ============================================================
# PHẦN HƯỚNG DẪN
# ============================================================

st.divider()

with st.expander("📖 Hướng dẫn sử dụng"):

    st.markdown("""
    ### 1. Nhập số tiền gửi

    Ví dụ:

    `500` = 500 triệu đồng.

    ### 2. Nhập lãi suất

    Ví dụ:

    - Lãi suất có kỳ hạn: `5%/năm`
    - Lãi suất không kỳ hạn: `0.2%/năm`

    ### 3. Chọn kỳ hạn

    Có thể chọn:

    - 1 tháng
    - 2 tháng
    - 3 tháng
    - 6 tháng
    - 9 tháng
    - 12 tháng
    - 18 tháng
    - 24 tháng
    - 36 tháng

    ### 4. Chọn phương thức nhận lãi

    **Nhận lãi trước:**

    Khách hàng nhận tiền lãi ngay khi gửi.
    Khi đáo hạn nhận lại tiền gốc.

    **Nhận lãi hàng tháng:**

    Tiền lãi được chia và trả theo từng tháng.

    **Nhận lãi cuối kỳ:**

    Đến ngày đáo hạn khách hàng nhận cả gốc và lãi.

    ### 5. Rút trước hạn

    Nếu:

    `Ngày rút < Ngày đáo hạn`

    thì toàn bộ thời gian gửi được tính theo
    lãi suất không kỳ hạn.

    ### 6. Tự động tái tục

    Nếu:

    `Ngày rút > Ngày đáo hạn`

    hệ thống tự động chia khoản tiền gửi thành
    nhiều kỳ bằng đúng kỳ hạn ban đầu.

    Ví dụ:

    Gửi:

    `01/01/2026`

    Kỳ hạn:

    `3 tháng`

    Nếu rút:

    `15/10/2026`

    hệ thống tính:

    `01/01 → 01/04`

    `01/04 → 01/07`

    `01/07 → 01/10`

    `01/10 → 15/10`
    """)


# ============================================================
# THÔNG TIN CÔNG THỨC
# ============================================================

with st.expander("🧮 Công thức tính lãi"):

    st.markdown(
        """
        ### Công thức lãi theo ngày

        Lãi tiền gửi:

        **Tiền lãi = Tiền gốc × Lãi suất năm × Số ngày / 365**

        Trong đó:

        - Tiền gốc: số tiền khách hàng gửi.
        - Lãi suất: tính theo %/năm.
        - Số ngày: số ngày thực tế gửi.
        - Cơ sở tính: 365 ngày/năm.

        ### Tổng tiền nhận

        **Tổng tiền nhận = Tiền gốc + Tiền lãi**

        Đối với rút trước hạn:

        **Lãi suất áp dụng = Lãi suất không kỳ hạn**

        Đối với tiền gửi đến hạn nhưng không rút:

        **Tự động tái tục theo đúng kỳ hạn ban đầu.**
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🏦 Hệ thống mô phỏng tính tiền gửi tiết kiệm | "
    "Streamlit | Cơ sở tính lãi 365 ngày/năm"
)
