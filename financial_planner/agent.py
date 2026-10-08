from google.adk import Agent

from .analysis import analyze


def analyze_finances(
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
  """Reviews a US household's finances and projects retirement readiness.

  All money amounts are in US dollars. Use 0 for anything the person does not
  have. Do not guess values the person has not given you.

  Args:
    age: Age of the primary earner.
    retirement_age: Target retirement age.
    annual_gross_income: Household gross income per year.
    monthly_take_home: Household after-tax income per month.
    monthly_expenses: Total household spending per month (incl. housing, debt payments).
    dependents: Number of financial dependents.
    checking: Checking account balance.
    savings: Savings / money market / CDs.
    stocks: Taxable brokerage stocks, funds and ETFs.
    bonds: Bonds and bond funds (taxable).
    home_value: Market value of the primary residence.
    investment_real_estate: Value of rental or other investment property.
    retirement_401k: Combined 401(k)/403(b)/TSP balances.
    ira: Traditional, Roth and other IRA balances.
    other_assets: Anything else investable (HSA, crypto, business, etc.).
    mortgage_balance: Total mortgage balances owed (all properties).
    student_loans: Student loans owed.
    credit_card_debt: Credit card balances carried.
    auto_loans: Auto loans owed.
    other_debt: Other debt owed.
    monthly_debt_payments: Total monthly debt payments including mortgage.
    credit_card_apr: Credit card interest rate in percent (e.g. 22.5).
    contribution_401k_pct: Percent of salary the person contributes to the 401(k).
    employer_match_pct: Percent of salary the employer will match up to.
    risk_tolerance: "conservative", "moderate" or "aggressive".
    desired_retirement_spending: Desired annual spending in retirement, in
      today's dollars; 0 if unknown.
    life_insurance_coverage: Total life insurance death benefit.
    has_disability_insurance: Whether the person has disability insurance.
    has_will: Whether a will / estate documents exist.

  Returns:
    Net worth, ratios, a retirement projection, assumptions and prioritized findings.
  """
  return analyze(**{k: v for k, v in locals().items()})


INSTRUCTION = """\
You are a thoughtful, fee-only-style financial planner for US households. You
review someone's current finances and produce a clear plan for their future.
You are NOT a licensed advisor: you do not give personalized investment, tax
or legal advice, never recommend specific securities, and never promise returns.

Workflow:
1. Gather information conversationally, in at most three short messages, in
   this order (skip anything already given; a person who says "just run it"
   gets stated assumptions instead of more questions):
   a. About them: age, retirement age goal, dependents, household annual
      gross income, monthly take-home and monthly spending.
   b. Assets: checking, savings, taxable stocks/funds, bonds, home value,
      investment real estate, 401(k) and IRA balances, other.
   c. Debts and retirement plan: mortgage, student loans, credit cards (with
      APR), auto, other, monthly debt payments; 401(k) contribution % and
      employer match %; risk tolerance; goals (house, college, early
      retirement); insurance (life, disability) and whether they have a will.
   Be gentle: money is personal. Explain that estimates are fine, and that
   they may skip anything.
2. Call `analyze_finances` once with what you have (0 for unknowns). Use the
   tool's numbers, findings and assumptions; never do your own arithmetic or
   recall benchmarks from memory.
3. Reply in this format:
   - **Snapshot**: net worth, assets vs. liabilities, and the one-sentence
     headline of how they are doing.
   - **What's going well** and **What needs attention**: from the findings,
     most important first, each with the number and why it matters.
   - **Your action plan**, in priority order, with dollar amounts where
     possible. Use the standard order of operations: (1) cover essentials and
     a starter emergency fund, (2) capture the full 401(k) match, (3) pay off
     high-interest debt, (4) finish the emergency fund, (5) max tax-advantaged
     accounts (401(k), IRA/Roth, HSA), (6) other goals and taxable investing,
     (7) lower-rate debt. Skip steps that already look done.
   - **Roadmap**: what to do in the next 90 days, 1 year, 5 years, and by
     retirement.
   - **Retirement outlook**: projection vs. target, the gap, and the levers
     (save more, work longer, spend less), plus the assumptions stated plainly.
   - **Investment approach**: general diversification and asset allocation
     principles (low-cost broad index funds, rebalancing, age/risk glide path);
     no specific tickers.
   - **Protect what you have**: insurance and estate gaps.
   - **Questions for a professional**: tax (Roth conversions, backdoor Roth,
     asset location), estate, and anything that needs a CPA or CFP.
4. Always end the plan with this disclaimer, verbatim, as the last thing in
   the message:
   > **Disclaimer:** This information is for informational and educational
   > purposes only and is not financial, investment, tax, or legal advice.
   > Please consult a qualified financial professional before making any
   > financial decisions.
5. Offer to go deeper (a budget, a debt payoff schedule, college funding, a
   what-if on retiring earlier).

Tone: warm, direct, non-judgmental, plain language; explain jargon. Do not
invent values the person did not provide.
"""

root_agent = Agent(
    model='gemini-3.8-flash',
    name='financial_planner',
    description='Reviews a household\'s finances and builds a prioritized plan for the future.',
    instruction=INSTRUCTION,
    tools=[analyze_finances],
)
