"""Deterministic personal-finance review (US households, USD).

All rules of thumb live here so the LLM never has to do the arithmetic or
recall benchmarks from memory. Figures are general guidelines, not advice.
"""

# Contribution limits for 2026. Review each January.
LIMIT_401K = 24_500
LIMIT_401K_CATCHUP_50 = 8_000
LIMIT_IRA = 7_500
LIMIT_IRA_CATCHUP_50 = 1_100

REAL_RETURN = {'conservative': 0.03, 'moderate': 0.05, 'aggressive': 0.06}
SS_SHARE_OF_NEED = 0.25  # share of retirement spending assumed to come from Social Security
SAFE_WITHDRAWAL = 0.04
# Fidelity-style multiples of annual income by age (interpolated).
SAVINGS_MULTIPLES = [(30, 1), (35, 2), (40, 3), (45, 4), (50, 6), (55, 7), (60, 8), (67, 10)]

GOOD, WATCH, ACTION = 'good', 'watch', 'action'
SEVERITY = {GOOD: 0, WATCH: 1, ACTION: 2}


def _multiple_for_age(age: int) -> float:
  if age < 30:
    return max(0.0, (age - 22) / 8)
  if age >= 67:
    return 10.0
  for (a0, m0), (a1, m1) in zip(SAVINGS_MULTIPLES, SAVINGS_MULTIPLES[1:]):
    if a0 <= age <= a1:
      return m0 + (m1 - m0) * (age - a0) / (a1 - a0)
  return 10.0


def _fv(balance: float, annual_contrib: float, rate: float, years: int) -> float:
  if years <= 0:
    return balance
  growth = (1 + rate) ** years
  return balance * growth + annual_contrib * ((growth - 1) / rate)


def _monthly_needed(gap: float, rate: float, years: int) -> float:
  """Extra monthly saving that closes `gap` by retirement (annual compounding)."""
  if gap <= 0 or years <= 0:
    return 0.0
  annual = gap * rate / ((1 + rate) ** years - 1)
  return annual / 12


def analyze(
    age: int,
    retirement_age: int,
    annual_gross_income: float,
    monthly_take_home: float = 0.0,
    monthly_expenses: float = 0.0,
    dependents: int = 0,
    checking: float = 0.0,
    savings: float = 0.0,
    stocks: float = 0.0,
    bonds: float = 0.0,
    home_value: float = 0.0,
    investment_real_estate: float = 0.0,
    retirement_401k: float = 0.0,
    ira: float = 0.0,
    other_assets: float = 0.0,
    mortgage_balance: float = 0.0,
    student_loans: float = 0.0,
    credit_card_debt: float = 0.0,
    auto_loans: float = 0.0,
    other_debt: float = 0.0,
    monthly_debt_payments: float = 0.0,
    credit_card_apr: float = 0.0,
    contribution_401k_pct: float = 0.0,
    employer_match_pct: float = 0.0,
    risk_tolerance: str = 'moderate',
    desired_retirement_spending: float = 0.0,
    life_insurance_coverage: float = 0.0,
    has_disability_insurance: bool = False,
    has_will: bool = False,
) -> dict:
  """Compute net worth, ratios, a retirement projection and prioritized findings."""
  risk = risk_tolerance.strip().lower() if risk_tolerance else 'moderate'
  rate = REAL_RETURN.get(risk, REAL_RETURN['moderate'])
  income = max(annual_gross_income, 0.0)
  findings: list[dict] = []

  def add(area, status, headline, detail):
    findings.append({'area': area, 'status': status, 'headline': headline, 'detail': detail})

  # ---- balance sheet
  cash = checking + savings
  investable = stocks + bonds + other_assets
  retirement = retirement_401k + ira
  assets = cash + investable + retirement + home_value + investment_real_estate
  liabilities = mortgage_balance + student_loans + credit_card_debt + auto_loans + other_debt
  net_worth = assets - liabilities
  liquid = cash + stocks + bonds

  allocation_base = cash + stocks + bonds + other_assets + retirement + investment_real_estate
  allocation = {}
  if allocation_base > 0:
    allocation = {
        'Cash': cash, 'Stocks': stocks, 'Bonds': bonds,
        'Retirement accounts': retirement, 'Investment real estate': investment_real_estate,
        'Other': other_assets,
    }
    allocation = {k: round(v / allocation_base * 100, 1) for k, v in allocation.items() if v}

  # ---- emergency fund
  em_months = None
  if monthly_expenses > 0:
    em_months = cash / monthly_expenses
    target = 6 if dependents > 0 else 3
    if em_months >= target:
      add('Emergency fund', GOOD, f'{em_months:.1f} months of expenses in cash',
          f'Meets the {target}-6 month guideline.')
    elif em_months >= 3:
      add('Emergency fund', WATCH, f'{em_months:.1f} months of expenses in cash',
          f'Decent, but with dependents or a single income aim for 6 months '
          f'(about ${monthly_expenses * 6:,.0f}).' if dependents else
          'Adequate; consider building toward 6 months.')
    else:
      add('Emergency fund', ACTION, f'Only {em_months:.1f} months of expenses in cash',
          f'Build to at least 3 months (about ${monthly_expenses * 3 - cash:,.0f} more).')

  # ---- debt
  gross_monthly = income / 12
  dti = monthly_debt_payments / gross_monthly if gross_monthly > 0 else None
  if dti is not None and monthly_debt_payments > 0:
    if dti <= 0.36:
      add('Debt load', GOOD, f'Debt-to-income {dti:.0%}', 'At or below the 36% guideline.')
    elif dti <= 0.43:
      add('Debt load', WATCH, f'Debt-to-income {dti:.0%}',
          'Above 36%; lenders start to see this as stretched. Avoid new debt.')
    else:
      add('Debt load', ACTION, f'Debt-to-income {dti:.0%}',
          'Above 43%, a high burden. Prioritize paydown and review the budget.')
  if credit_card_debt > 0:
    apr_txt = f' at ~{credit_card_apr:g}% APR' if credit_card_apr else ''
    add('Debt load', ACTION, f'${credit_card_debt:,.0f} credit card debt{apr_txt}',
        'Typically the highest-return use of spare cash is paying this off, '
        'ahead of extra investing (after any 401(k) match).')
  if student_loans > 0 and credit_card_debt == 0:
    add('Debt load', WATCH, f'${student_loans:,.0f} student loans',
        'Compare rates to expected investment returns; check forgiveness or refinance options.')

  # ---- cash flow
  savings_rate = None
  if monthly_take_home > 0 and monthly_expenses > 0:
    surplus = monthly_take_home - monthly_expenses
    savings_rate = surplus / monthly_take_home
    if savings_rate >= 0.20:
      add('Cash flow', GOOD, f'Saving ~{savings_rate:.0%} of take-home (${surplus:,.0f}/mo)',
          'At or above the common 20% target.')
    elif savings_rate >= 0.10:
      add('Cash flow', WATCH, f'Saving ~{savings_rate:.0%} of take-home (${surplus:,.0f}/mo)',
          'Reasonable; 15-20% is a common target.')
    elif surplus >= 0:
      add('Cash flow', ACTION, f'Saving only ~{savings_rate:.0%} of take-home (${surplus:,.0f}/mo)',
          'Look for spending to trim or income to grow.')
    else:
      add('Cash flow', ACTION, f'Spending exceeds take-home by ${-surplus:,.0f}/mo',
          'This is the first thing to fix; the gap is being funded by savings or debt.')

  # ---- retirement plan
  match_gap = max(0.0, employer_match_pct - contribution_401k_pct)
  if employer_match_pct > 0:
    if contribution_401k_pct >= employer_match_pct:
      add('401(k)', GOOD, f'Capturing the full {employer_match_pct:g}% employer match',
          'You contribute at least the matched amount.')
    else:
      lost = match_gap / 100 * income
      add('401(k)', ACTION, f'Missing ~${lost:,.0f}/yr of employer match',
          f'Contributing {contribution_401k_pct:g}% vs. the {employer_match_pct:g}% that earns a match. '
          'This is usually the best guaranteed return available.')
  annual_limit = LIMIT_401K + (LIMIT_401K_CATCHUP_50 if age >= 50 else 0)
  own_contrib = contribution_401k_pct / 100 * income
  match_contrib = min(contribution_401k_pct, employer_match_pct) / 100 * income
  if own_contrib > 0 and own_contrib < annual_limit * 0.5 and savings_rate is not None and savings_rate > 0.15:
    add('401(k)', WATCH, f'Contributing ${own_contrib:,.0f}/yr of a ${annual_limit:,} limit',
        'There may be room to contribute more, including IRA / Roth options.')

  years = max(retirement_age - age, 0)
  multiple = _multiple_for_age(age)
  saved_multiple = retirement / income if income > 0 else None
  if saved_multiple is not None and age >= 25:
    if saved_multiple >= multiple:
      add('Retirement', GOOD, f'{saved_multiple:.1f}x income saved (benchmark ~{multiple:.1f}x at {age})',
          'On or ahead of typical age-based benchmarks.')
    elif saved_multiple >= multiple * 0.6:
      add('Retirement', WATCH, f'{saved_multiple:.1f}x income saved (benchmark ~{multiple:.1f}x at {age})',
          'Somewhat behind; higher contributions can close this.')
    else:
      add('Retirement', ACTION, f'{saved_multiple:.1f}x income saved (benchmark ~{multiple:.1f}x at {age})',
          'Well behind typical benchmarks; raise savings and consider working a little longer.')

  # ---- retirement projection (inflation-adjusted dollars)
  need = desired_retirement_spending if desired_retirement_spending > 0 else 0.7 * income
  portfolio_need = need * (1 - SS_SHARE_OF_NEED)
  target_nest_egg = portfolio_need / SAFE_WITHDRAWAL
  retire_balance = retirement + stocks + bonds + other_assets
  annual_contrib = own_contrib + match_contrib
  projected = _fv(retire_balance, annual_contrib, rate, years)
  gap = target_nest_egg - projected
  projection = {
      'years_to_retirement': years,
      'assumed_real_return': rate,
      'annual_retirement_contributions': round(annual_contrib),
      'starting_investable_balance': round(retire_balance),
      'projected_balance_todays_dollars': round(projected),
      'annual_spending_goal': round(need),
      'portfolio_funded_spending': round(portfolio_need),
      'target_nest_egg': round(target_nest_egg),
      'shortfall': round(max(gap, 0)),
      'extra_monthly_saving_to_close_gap': round(_monthly_needed(gap, rate, years)),
      'on_track_pct': round(min(projected / target_nest_egg * 100, 999), 0) if target_nest_egg else None,
  }
  if income > 0 and years > 0:
    if gap <= 0:
      add('Retirement', GOOD, f'Projected ${projected:,.0f} vs. ${target_nest_egg:,.0f} target',
          f'On track to retire at {retirement_age} under the assumptions.')
    else:
      add('Retirement', ACTION if projected < 0.75 * target_nest_egg else WATCH,
          f'Projected ${projected:,.0f} vs. ${target_nest_egg:,.0f} target',
          f'Closing the gap would take about ${projection["extra_monthly_saving_to_close_gap"]:,.0f} '
          f'more per month, or a later retirement / lower spending goal.')

  # ---- allocation vs. age/risk
  if allocation_base > 0 and (stocks + bonds + retirement) > 0:
    guide = {'conservative': 90, 'moderate': 110, 'aggressive': 120}.get(risk, 110)
    equity_guide = max(20, min(95, guide - age))
    cash_pct = cash / allocation_base * 100
    if cash_pct > 25 and cash > 6 * (monthly_expenses or 0) + 20_000:
      add('Allocation', WATCH, f'{cash_pct:.0f}% of assets in cash',
          'Beyond the emergency fund, large cash balances lose to inflation over time.')
    re_pct = investment_real_estate / allocation_base * 100
    if re_pct > 40:
      add('Allocation', WATCH, f'{re_pct:.0f}% in investment real estate',
          'Concentrated and illiquid; consider diversification.')
    allocation_guide = f'~{equity_guide}% stocks for a {risk} investor aged {age} (rule of thumb)'
  else:
    allocation_guide = None

  # ---- protection
  if dependents > 0 or income > 0:
    want = 10 * income
    if dependents > 0:
      if life_insurance_coverage >= want:
        add('Protection', GOOD, f'Life insurance ${life_insurance_coverage:,.0f}', 'Meets the ~10x income guideline.')
      else:
        add('Protection', ACTION, f'Life insurance ${life_insurance_coverage:,.0f} vs. ~${want:,.0f} guideline',
            'With dependents, term life of about 10x income is a common starting point.')
    if not has_disability_insurance:
      add('Protection', WATCH, 'No disability insurance reported',
          'Your ability to earn is your largest asset; check employer coverage.')
  if not has_will:
    add('Protection', WATCH if dependents == 0 else ACTION, 'No will / estate documents reported',
        'Will, beneficiary designations, power of attorney and healthcare directive.'
        + (' Essential with dependents (guardianship).' if dependents else ''))

  findings.sort(key=lambda f: -SEVERITY[f['status']])
  return {
      'net_worth': round(net_worth),
      'total_assets': round(assets),
      'total_liabilities': round(liabilities),
      'liquid_assets': round(liquid),
      'cash': round(cash),
      'emergency_fund_months': round(em_months, 1) if em_months is not None else None,
      'debt_to_income': round(dti, 3) if dti is not None else None,
      'savings_rate': round(savings_rate, 3) if savings_rate is not None else None,
      'retirement_multiple_of_income': round(saved_multiple, 1) if saved_multiple is not None else None,
      'allocation_pct': allocation,
      'allocation_guideline': allocation_guide,
      'projection': projection,
      'limits_2026': {'401k': annual_limit, 'ira': LIMIT_IRA + (LIMIT_IRA_CATCHUP_50 if age >= 50 else 0)},
      'findings': findings,
      'assumptions': [
          f'Real (inflation-adjusted) return {rate:.0%} for a {risk} investor',
          f'Retirement spending goal {"as entered" if desired_retirement_spending else "70% of gross income"}; '
          f'Social Security assumed to cover {SS_SHARE_OF_NEED:.0%} of it',
          f'Sustainable withdrawal rate {SAFE_WITHDRAWAL:.0%}',
          'Primary home equity is excluded from the retirement projection',
      ],
  }
