"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""
# --- The page ---------------------------------------------------------------------
#
# No scaffolding. Every function this page needs already exists in the payroll
# package, and every widget it needs you used in Assignments 03 and 04 — plus two
# new ones, st.date_input and st.bar_chart. README Step 8 has the exact widgets,
# keys and labels; the tests in tests/test_pipeline.py -k app check them.
#
# The shape, in words:
#
#   title and a sentence of instructions
#   roster   <- load_employees()                           (fixed; not uploaded)
#   uploads  <- st.file_uploader, key="exports", accept_multiple_files=True
#               (an empty list until files are chosen)
#   if there are uploads:
#       history <- build_history([load_export(u) for u in uploads], roster)
#       st.warning naming any employeeid with no department (not on the roster);
#           the reports below use only the rows that matched
#       st.selectbox, key="department": "All" plus each department
#       st.date_input, key="dates": a (start, end) range, defaulting to the first
#           and last pay_date — compare against pay_date.dt.date to filter
#       the selection as a subheader
#       four st.metric cards in st.columns(4): Weeks, Employees, Total hours,
#           Total gross pay — counts are .nunique(), totals are .sum()
#       st.bar_chart of pay_by_month(selected), with month as the x axis
#       st.dataframe of summarize_employees(selected)
#       st.dataframe of hours_grid(selected), then of missed_weeks(that grid)
#       st.download_button, key="download": pay_by_month(...).to_csv(index=False)
#
# What the page does NOT do: cleaning, grouping, pivoting. If you find yourself
# writing a groupby or a pivot_table here, that logic belongs in the package.



import streamlit as st

from payroll import (
    load_employees,
    load_export,
    build_history,
    summarize_employees,
    hours_grid,
    missed_weeks,
    pay_by_month,
)

st.title("Salt City Coffee — Quarterly Payroll Report")

st.write(
    "Upload the weekly payroll exports for the period you want to review "
    "— old spreadsheet weeks and new app weeks can be mixed. "
    "The roster is loaded automatically."
)

# Load employee roster
roster = load_employees()

# Upload weekly payroll exports
uploads = st.file_uploader(
    "Upload weekly payroll exports (CSV)",
    type=["csv"],
    accept_multiple_files=True,
    key="exports"
)

if uploads:

    # Build payroll history
    history = build_history(
        [load_export(u) for u in uploads],
        roster
    )

    # Warn about employees not found on roster
    unmatched = history[history["department"].isna()]

    if not unmatched.empty:
        missing_ids = unmatched["employeeid"].unique()
        st.warning(
            f"Employees not found on roster: {', '.join(missing_ids)}"
        )

    # Keep only matched employees
    history = history[history["department"].notna()].copy()
    history = history.dropna(subset=["pay_date"])

    if not history.empty:

        # Department filter
        departments = ["All"] + sorted(history["department"].unique())

        department = st.selectbox(
            "Department",
            departments,
            key="department"
        )

        # Pay date filter
        start_date = history["pay_date"].min().date()
        end_date = history["pay_date"].max().date()

        dates = st.date_input(
            "Pay dates",
            value=(start_date, end_date),
            key="dates"
        )

        # Filter history
        selected = history.copy()

        if department != "All":
            selected = selected[
                selected["department"] == department
            ]

        if len(dates) == 2:
            start, end = dates

            selected = selected[
                (selected["pay_date"].dt.date >= start)
                & (selected["pay_date"].dt.date <= end)
            ]

            st.subheader(f"{department} · {start} to {end}")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Weeks",
                selected["week_ending"].nunique()
            )

        with col2:
            st.metric(
                "Employees",
                selected["employee_id"].nunique()
            )

        with col3:
            st.metric(
                "Total hours",
                f"{selected['hours_worked'].sum():,.2f}"
            )

        with col4:
            st.metric(
                "Total gross pay",
                f"${selected['gross_pay'].sum():,.2f}"
            )

        # Gross pay by month
        st.subheader("Gross pay by month")

        monthly = pay_by_month(selected)

        if not monthly.empty:
            st.bar_chart(monthly, x="month", stack=True)

        # Employee summary
        st.subheader("Employees")
        st.dataframe(
            summarize_employees(selected),
            hide_index=True
        )

        # Hours by week
        st.subheader("Hours by week")
        st.caption("0 means the employee was not paid that week.")

        grid = hours_grid(selected)

        st.dataframe(
            grid,
            hide_index=True
        )

        # Missed weeks
        st.subheader("Missed weeks")

        st.dataframe(
            missed_weeks(grid),
            hide_index=True
        )

        # Download monthly payroll report
        st.download_button(
            "Download pay by month for the accountant (CSV)",
            data=monthly.to_csv(index=False),
            file_name="pay_by_month.csv",
            mime="text/csv",
            key="download"
        )
