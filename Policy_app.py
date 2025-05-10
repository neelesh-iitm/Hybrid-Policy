import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- App Title and Description ---
st.set_page_config(layout="wide")
st.title("Hybrid Investment Policy Analyzer 📈")
st.markdown("""
This application analyzes and compares two investment scenarios:
1.  **Primary Insurance Policy Only**: Receives a fixed monthly survival benefit.
2.  **Hybrid Investment Policy**: The monthly survival benefit is first invested in a Systematic Investment Plan (SIP) for a period,
    and then a Systematic Withdrawal Plan (SWP) is activated from the accumulated corpus. The primary survival benefit continues throughout.

Adjust the parameters in the sidebar to see how they impact the outcomes.
""")

# --- Sidebar for User Inputs ---
st.sidebar.header("⚙️ Policy & Investment Parameters")

# Policy Parameters
st.sidebar.subheader("Policy Details")
current_age_input = st.sidebar.number_input("Current Age (Years)", min_value=20, max_value=70, value=40, step=1)
monthly_survival_benefit_input = st.sidebar.number_input("Monthly Survival Benefit (₹)", min_value=1000, max_value=100000, value=10000, step=1000)
policy_end_age_input = st.sidebar.number_input("Policy End Age (Years)", min_value=current_age_input + 20, max_value=100, value=85, step=1)

# SIP Parameters
st.sidebar.subheader("SIP Details")
sip_duration_years_input = st.sidebar.slider("SIP Duration (Years)", min_value=5, max_value=25, value=12, step=1)
sip_annual_return_rate_input = st.sidebar.slider("SIP Annual Return Rate (%)", min_value=1.0, max_value=25.0, value=15.0, step=0.5) / 100

# SWP & Corpus Parameters
st.sidebar.subheader("SWP & Corpus Details")
corpus_annual_growth_rate_input = st.sidebar.slider("SWP Corpus Annual Growth Rate (%)", min_value=1.0, max_value=25.0, value=15.0, step=0.5) / 100
swp_initial_annual_withdrawal_rate_input = st.sidebar.slider("SWP Initial Annual Withdrawal Rate from Corpus (%)", min_value=1.0, max_value=20.0, value=12.0, step=0.5) / 100
swp_annual_payout_growth_rate_input = st.sidebar.slider("SWP Annual Payout Growth Rate (%)", min_value=0.0, max_value=10.0, value=5.0, step=0.5) / 100


# --- Core Calculation Logic (Function) ---
def calculate_policy_outcomes(
    current_age, monthly_survival_benefit, policy_end_age,
    sip_duration_years, sip_annual_return_rate,
    corpus_annual_growth_rate, swp_initial_annual_withdrawal_rate, swp_annual_payout_growth_rate
):
    """
    Performs the month-by-month simulation based on the input parameters.
    Returns a pandas DataFrame with the results.
    """
    
    # Derived Parameters
    policy_duration_years = policy_end_age - current_age
    total_months = policy_duration_years * 12
    sip_duration_months = sip_duration_years * 12

    monthly_sip_return_rate = sip_annual_return_rate / 12
    monthly_corpus_growth_rate = corpus_annual_growth_rate / 12

    results_list = []

    # Initial State Variables
    primary_cumulative_income = 0.0
    hybrid_sip_corpus = 0.0
    hybrid_swp_corpus = 0.0
    hybrid_cumulative_total_income = 0.0
    scheduled_last_year_swp_monthly_payout = 0.0
    swp_year_counter = 0
    current_target_swp_monthly_payout = 0.0

    for month_index in range(total_months):
        age_at_month_start = current_age + (month_index / 12.0)
        current_policy_year = month_index // 12 + 1
        current_policy_month_in_year = month_index % 12

        # Scenario 1: Primary Insurance Only
        primary_monthly_income = monthly_survival_benefit
        primary_cumulative_income += primary_monthly_income

        # Scenario 2: Hybrid Policy
        hybrid_survival_benefit_received_this_month = monthly_survival_benefit
        current_sip_investment_this_month = 0.0
        actual_swp_payout_this_month = 0.0
        current_hybrid_swp_corpus_value_eom = 0.0 # Initialize for SIP phase

        if month_index < sip_duration_months:
            # --- SIP Phase ---
            current_sip_investment_this_month = hybrid_survival_benefit_received_this_month
            interest_on_sip = hybrid_sip_corpus * monthly_sip_return_rate
            hybrid_sip_corpus += interest_on_sip
            hybrid_sip_corpus += current_sip_investment_this_month
            
            hybrid_total_monthly_income_this_month = hybrid_survival_benefit_received_this_month
            current_hybrid_swp_corpus_value_eom = 0.0 # No SWP corpus during SIP
            actual_swp_payout_this_month = 0.0

        else:
            # --- SWP Phase ---
            current_sip_investment_this_month = 0.0 # SIP investment stops

            if month_index == sip_duration_months: # First month of SWP
                hybrid_swp_corpus = hybrid_sip_corpus # Transfer final SIP corpus
                swp_year_counter = 1
                annual_swp_amount_year1 = hybrid_swp_corpus * swp_initial_annual_withdrawal_rate
                current_target_swp_monthly_payout = annual_swp_amount_year1 / 12
                scheduled_last_year_swp_monthly_payout = current_target_swp_monthly_payout
            
            if (month_index - sip_duration_months) > 0 and (month_index - sip_duration_months) % 12 == 0:
                swp_year_counter += 1
                current_target_swp_monthly_payout = scheduled_last_year_swp_monthly_payout * (1 + swp_annual_payout_growth_rate)
                scheduled_last_year_swp_monthly_payout = current_target_swp_monthly_payout
            
            if hybrid_swp_corpus <= 0:
                actual_swp_payout_this_month = 0.0
                hybrid_swp_corpus = 0.0
            else:
                interest_on_swp_corpus = hybrid_swp_corpus * monthly_corpus_growth_rate
                corpus_after_growth = hybrid_swp_corpus + interest_on_swp_corpus
                
                if current_target_swp_monthly_payout >= corpus_after_growth:
                    actual_swp_payout_this_month = corpus_after_growth
                    hybrid_swp_corpus = 0.0
                else:
                    actual_swp_payout_this_month = current_target_swp_monthly_payout
                    hybrid_swp_corpus = corpus_after_growth - actual_swp_payout_this_month
            
            if hybrid_swp_corpus < 0: hybrid_swp_corpus = 0.0
            
            hybrid_total_monthly_income_this_month = hybrid_survival_benefit_received_this_month + actual_swp_payout_this_month
            current_hybrid_swp_corpus_value_eom = hybrid_swp_corpus

        hybrid_cumulative_total_income += hybrid_total_monthly_income_this_month

        results_list.append({
            'MonthIndex': month_index,
            'Age': age_at_month_start,
            'PolicyYear': current_policy_year,
            'MonthInPolicyYear': current_policy_month_in_year + 1,
            'Primary_MonthlyIncome': primary_monthly_income,
            'Primary_CumulativeIncome': primary_cumulative_income,
            'Hybrid_SurvivalBenefitReceived': hybrid_survival_benefit_received_this_month,
            'Hybrid_SIPInvestment': current_sip_investment_this_month,
            'Hybrid_SIPCorpus_EOM': hybrid_sip_corpus,
            'Hybrid_SWPPayout': actual_swp_payout_this_month,
            'Hybrid_SWPCorpus_EOM': current_hybrid_swp_corpus_value_eom,
            'Hybrid_TotalMonthlyIncome': hybrid_total_monthly_income_this_month,
            'Hybrid_CumulativeTotalIncome': hybrid_cumulative_total_income,
            'SWP_Year': swp_year_counter if month_index >= sip_duration_months else 0,
            'Target_SWP_Payout': current_target_swp_monthly_payout if month_index >= sip_duration_months else 0
        })
    
    return pd.DataFrame(results_list)

# --- Perform Calculations based on Inputs ---
df_results = calculate_policy_outcomes(
    current_age_input, monthly_survival_benefit_input, policy_end_age_input,
    sip_duration_years_input, sip_annual_return_rate_input,
    corpus_annual_growth_rate_input, swp_initial_annual_withdrawal_rate_input, swp_annual_payout_growth_rate_input
)

# --- Display Key Metrics Summary ---
st.header("📊 Key Metrics Summary")

final_primary_cumulative_income = df_results['Primary_CumulativeIncome'].iloc[-1] if not df_results.empty else 0
final_hybrid_cumulative_total_income = df_results['Hybrid_CumulativeTotalIncome'].iloc[-1] if not df_results.empty else 0
final_hybrid_swp_corpus = df_results['Hybrid_SWPCorpus_EOM'].iloc[-1] if not df_results.empty else 0
additional_cumulative_income_from_hybrid = final_hybrid_cumulative_total_income - final_primary_cumulative_income

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Primary Policy: Total Income", value=f"₹{final_primary_cumulative_income:,.0f}")
    st.metric(label="Primary Policy: Final Corpus", value="₹0")
with col2:
    st.metric(label="Hybrid Policy: Total Income", value=f"₹{final_hybrid_cumulative_total_income:,.0f}")
    st.metric(label="Hybrid Policy: Final Corpus", value=f"₹{final_hybrid_swp_corpus:,.0f}")
with col3:
    st.metric(label="Hybrid Advantage: Addl. Income", value=f"₹{additional_cumulative_income_from_hybrid:,.0f}",
              delta=f"{((additional_cumulative_income_from_hybrid / final_primary_cumulative_income) * 100 if final_primary_cumulative_income else 0):.2f}%")

st.markdown("---")
st.header("Visualizations")

if not df_results.empty:
    # --- Plotting Visualizations ---
    plt.style.use('seaborn-v0_8-whitegrid')

    # Plot 1: Monthly Income Comparison
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(df_results['Age'], df_results['Primary_MonthlyIncome'], label='Primary Policy Only - Monthly Income', linestyle='--')
    ax1.plot(df_results['Age'], df_results['Hybrid_TotalMonthlyIncome'], label='Hybrid Policy - Total Monthly Income', color='green', linewidth=2)
    ax1.axvline(x=current_age_input + sip_duration_years_input, color='gray', linestyle=':', linewidth=2, label=f'SWP Starts (Age {current_age_input + sip_duration_years_input})')
    ax1.set_xlabel('Age (Years)', fontsize=10)
    ax1.set_ylabel('Monthly Income (₹)', fontsize=10)
    ax1.set_title('Monthly Income Comparison', fontsize=12)
    ax1.legend(fontsize=8)
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    st.pyplot(fig1)

    # Plot 2: Cumulative Income Comparison
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.plot(df_results['Age'], df_results['Primary_CumulativeIncome'], label='Primary Policy Only - Cumulative Income', linestyle='--')
    ax2.plot(df_results['Age'], df_results['Hybrid_CumulativeTotalIncome'], label='Hybrid Policy - Cumulative Total Income', color='green', linewidth=2)
    ax2.axvline(x=current_age_input + sip_duration_years_input, color='gray', linestyle=':', linewidth=2, label=f'SWP Starts (Age {current_age_input + sip_duration_years_input})')
    ax2.set_xlabel('Age (Years)', fontsize=10)
    ax2.set_ylabel('Cumulative Income (₹)', fontsize=10)
    ax2.set_title('Cumulative Income Comparison', fontsize=12)
    ax2.ticklabel_format(style='plain', axis='y')
    ax2.legend(fontsize=8)
    ax2.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    st.pyplot(fig2)

    # Plot 3: Hybrid Policy Investment Corpus Growth
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    ax3.plot(df_results['Age'], df_results['Hybrid_SIPCorpus_EOM'], label='SIP Corpus Value', color='blue', linestyle='-.')
    swp_phase_df = df_results[df_results['MonthIndex'] >= (sip_duration_years_input * 12)]
    if not swp_phase_df.empty:
        ax3.plot(swp_phase_df['Age'], swp_phase_df['Hybrid_SWPCorpus_EOM'], label='SWP Corpus Value (During SWP Phase)', color='purple', linewidth=2)
    ax3.axvline(x=current_age_input + sip_duration_years_input, color='gray', linestyle=':', linewidth=2, label=f'SIP Ends / SWP Starts (Age {current_age_input + sip_duration_years_input})')
    ax3.set_xlabel('Age (Years)', fontsize=10)
    ax3.set_ylabel('Corpus Value (₹)', fontsize=10)
    ax3.set_title('Hybrid Policy: Investment Corpus Growth (SIP & SWP)', fontsize=12)
    ax3.ticklabel_format(style='plain', axis='y')
    ax3.legend(fontsize=8)
    ax3.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    st.pyplot(fig3)

    # Plot 4: Breakdown of Hybrid Monthly Income During SWP Phase
    fig4, ax4 = plt.subplots(figsize=(12, 6))
    swp_phase_plot_df = df_results[df_results['MonthIndex'] >= (sip_duration_years_input * 12)].copy()
    if not swp_phase_plot_df.empty:
        ax4.stackplot(swp_phase_plot_df['Age'],
                      swp_phase_plot_df['Hybrid_SurvivalBenefitReceived'],
                      swp_phase_plot_df['Hybrid_SWPPayout'],
                      labels=['Survival Benefit (Primary Policy)', 'SWP Payout (Investment Corpus)'],
                      colors=['skyblue', 'orange'],
                      alpha=0.8)
        ax4.plot(swp_phase_plot_df['Age'], swp_phase_plot_df['Hybrid_TotalMonthlyIncome'], label='Total Hybrid Monthly Income', color='black', linestyle='--', linewidth=1.5)
        ax4.set_xlabel('Age (Years - During SWP Phase)', fontsize=10)
        ax4.set_ylabel('Monthly Income Components (₹)', fontsize=10)
        ax4.set_title('Breakdown of Hybrid Policy Monthly Income (SWP Phase)', fontsize=12)
        ax4.legend(loc='upper left', fontsize=8)
        ax4.grid(True, which='both', linestyle='--', linewidth=0.5)
        plt.tight_layout()
        st.pyplot(fig4)
    else:
        st.markdown("SWP phase not reached with current parameters or data is empty for SWP plot.")
else:
    st.warning("No data to display. This might happen if the policy duration is too short or parameters are invalid.")

st.markdown("---")
st.subheader("Detailed Data Table")
st.markdown("You can inspect the month-by-month calculations below:")

# Display a portion of the DataFrame (e.g., with a checkbox to show all)
if not df_results.empty:
    # Add an option to show the full table, as it can be very long
    if st.checkbox("Show Full Detailed Data Table (can be very long)", False):
        st.dataframe(df_results.style.format("{:,.2f}", subset=pd.IndexSlice[:, [
            'Primary_MonthlyIncome', 'Primary_CumulativeIncome',
            'Hybrid_SurvivalBenefitReceived', 'Hybrid_SIPInvestment', 'Hybrid_SIPCorpus_EOM',
            'Hybrid_SWPPayout', 'Hybrid_SWPCorpus_EOM', 'Hybrid_TotalMonthlyIncome',
            'Hybrid_CumulativeTotalIncome', 'Target_SWP_Payout'
        ]]))
    else:
        st.dataframe(df_results.head(12*2).style.format("{:,.2f}", subset=pd.IndexSlice[:, [
            'Primary_MonthlyIncome', 'Primary_CumulativeIncome',
            'Hybrid_SurvivalBenefitReceived', 'Hybrid_SIPInvestment', 'Hybrid_SIPCorpus_EOM',
            'Hybrid_SWPPayout', 'Hybrid_SWPCorpus_EOM', 'Hybrid_TotalMonthlyIncome',
            'Hybrid_CumulativeTotalIncome', 'Target_SWP_Payout'
        ]]))
        st.caption("Showing first 2 years of data. Check the box above to see the full table.")

st.sidebar.markdown("---")
st.sidebar.info("This app demonstrates the potential outcomes based on the input assumptions. Actual returns may vary.")

