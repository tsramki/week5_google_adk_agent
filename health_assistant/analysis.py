"""Deterministic lab interpretation against standard adult reference ranges.

Units are US conventional: lipids and glucose in mg/dL, Lp(a) in mg/dL,
ApoB in mg/dL, HbA1c in %, TSH in mIU/L, RBC in million/uL, WBC and PLT in
thousand/uL, Hgb in g/dL, ALT/AST in U/L, eGFR in mL/min/1.73m2.
"""

from typing import Optional

# Status levels, ordered by severity for sorting/display.
NORMAL = 'normal'
BORDERLINE = 'borderline'
HIGH = 'high'
LOW = 'low'
VERY_HIGH = 'very high'
SEVERITY = {NORMAL: 0, BORDERLINE: 1, LOW: 2, HIGH: 2, VERY_HIGH: 3}

# key -> (display name, unit)
MARKERS = {
    'total_cholesterol': ('Total cholesterol', 'mg/dL'),
    'ldl': ('LDL', 'mg/dL'),
    'hdl': ('HDL', 'mg/dL'),
    'triglycerides': ('Triglycerides', 'mg/dL'),
    'vldl': ('VLDL', 'mg/dL'),
    'apob': ('ApoB', 'mg/dL'),
    'lpa': ('Lipoprotein(a)', 'mg/dL'),
    'hba1c': ('HbA1c', '%'),
    'fbg': ('Fasting glucose', 'mg/dL'),
    'rbc': ('RBC', 'M/uL'),
    'wbc': ('WBC', 'K/uL'),
    'hgb': ('Hemoglobin', 'g/dL'),
    'plt': ('Platelets', 'K/uL'),
    'alt': ('ALT', 'U/L'),
    'ast': ('AST', 'U/L'),
    'egfr': ('eGFR', 'mL/min/1.73m2'),
    'tsh': ('TSH', 'mIU/L'),
}


def _bands(value, bands, reference):
  """bands: ascending (upper_exclusive, status, label); last bound may be None."""
  for upper, status, label in bands:
    if upper is None or value < upper:
      return status, label, reference
  raise AssertionError('unreachable')


def _range(value, low, high, reference, low_label='Below range',
           high_label='Above range'):
  if value < low:
    return LOW, low_label, reference
  if value > high:
    return HIGH, high_label, reference
  return NORMAL, 'Within range', reference


def _classify(key: str, v: float, sex: Optional[str]):
  female = sex == 'female'
  male = sex == 'male'
  if key == 'total_cholesterol':
    return _bands(v, [(200, NORMAL, 'Desirable'), (240, BORDERLINE, 'Borderline high'),
                      (None, HIGH, 'High')], '<200')
  if key == 'ldl':
    return _bands(v, [(100, NORMAL, 'Optimal'), (130, NORMAL, 'Near optimal'),
                      (160, BORDERLINE, 'Borderline high'), (190, HIGH, 'High'),
                      (None, VERY_HIGH, 'Very high')], '<100 (lower if high risk)')
  if key == 'hdl':
    floor = 50 if female else 40
    ref = f'>={floor}' if sex else '>=40 (men) / >=50 (women)'
    if v < floor:
      return LOW, 'Low (less protective)', ref
    return (NORMAL, 'Protective', ref) if v >= 60 else (NORMAL, 'Acceptable', ref)
  if key == 'triglycerides':
    return _bands(v, [(150, NORMAL, 'Normal'), (200, BORDERLINE, 'Borderline high'),
                      (500, HIGH, 'High'), (None, VERY_HIGH, 'Very high')], '<150')
  if key == 'vldl':
    return _range(v, 2, 30, '2-30', high_label='Elevated')
  if key == 'apob':
    return _bands(v, [(90, NORMAL, 'Desirable'), (130, BORDERLINE, 'Borderline high'),
                      (None, HIGH, 'High')], '<90 (<80 if high risk)')
  if key == 'lpa':
    return _bands(v, [(30, NORMAL, 'Normal'), (50, BORDERLINE, 'Borderline'),
                      (None, HIGH, 'Elevated (inherited risk factor)')], '<30 (~<75 nmol/L)')
  if key == 'hba1c':
    return _bands(v, [(5.7, NORMAL, 'Normal'), (6.5, BORDERLINE, 'Prediabetes range'),
                      (None, HIGH, 'Diabetes range')], '<5.7')
  if key == 'fbg':
    if v < 70:
      return LOW, 'Low', '70-99'
    return _bands(v, [(100, NORMAL, 'Normal'), (126, BORDERLINE, 'Prediabetes range'),
                      (None, HIGH, 'Diabetes range')], '70-99')
  if key == 'rbc':
    lo, hi = (4.1, 5.1) if female else (4.5, 5.9) if male else (4.1, 5.9)
    return _range(v, lo, hi, f'{lo}-{hi}')
  if key == 'wbc':
    return _range(v, 4.0, 11.0, '4.0-11.0')
  if key == 'hgb':
    lo, hi = (12.0, 15.5) if female else (13.5, 17.5) if male else (12.0, 17.5)
    return _range(v, lo, hi, f'{lo}-{hi}', low_label='Low (possible anemia)')
  if key == 'plt':
    return _range(v, 150, 450, '150-450')
  if key in ('alt', 'ast'):
    hi = 35 if female else 40
    return _range(v, 0, hi, f'<={hi}', high_label='Elevated (liver or muscle)')
  if key == 'egfr':
    return _bands(v, [(15, VERY_HIGH, 'Kidney failure range (G5)'),
                      (30, HIGH, 'Severely decreased (G4)'),
                      (45, HIGH, 'Moderately to severely decreased (G3b)'),
                      (60, BORDERLINE, 'Mildly to moderately decreased (G3a)'),
                      (90, NORMAL, 'Mildly decreased (G2)'),
                      (None, NORMAL, 'Normal')], '>=90')
  if key == 'tsh':
    return _range(v, 0.4, 4.0, '0.4-4.0', low_label='Low (possible overactive thyroid)',
                  high_label='High (possible underactive thyroid)')
  raise KeyError(key)


def calc_bmi(weight_kg: float, height_cm: float) -> dict:
  bmi = weight_kg / (height_cm / 100) ** 2
  if bmi < 18.5:
    cat = 'Underweight'
  elif bmi < 25:
    cat = 'Healthy weight'
  elif bmi < 30:
    cat = 'Overweight'
  else:
    cat = 'Obesity'
  return {'bmi': round(bmi, 1), 'category': cat}


def analyze(
    labs: dict[str, float],
    sex: Optional[str] = None,
    weight_kg: Optional[float] = None,
    height_cm: Optional[float] = None,
) -> dict:
  """Classify each supplied lab and compute BMI and derived ratios."""
  sex = sex.strip().lower() if sex else None
  findings = []
  unknown = []
  for key, raw in labs.items():
    k = key.strip().lower()
    if raw is None:
      continue
    if k not in MARKERS:
      unknown.append(key)
      continue
    name, unit = MARKERS[k]
    status, label, ref = _classify(k, float(raw), sex)
    findings.append({'key': k, 'marker': name, 'value': float(raw), 'unit': unit,
                     'status': status, 'interpretation': label,
                     'reference': f'{ref} {unit}'})
  result: dict = {'findings': findings}
  if unknown:
    result['ignored_unknown_markers'] = unknown
  if weight_kg and height_cm:
    result['bmi'] = calc_bmi(weight_kg, height_cm)
  by_key = {f['key']: f['value'] for f in findings}
  derived = {}
  if 'total_cholesterol' in by_key and 'hdl' in by_key and by_key['hdl'] > 0:
    derived['total_chol_to_hdl_ratio'] = round(by_key['total_cholesterol'] / by_key['hdl'], 1)
  if 'total_cholesterol' in by_key and 'hdl' in by_key:
    derived['non_hdl_cholesterol'] = round(by_key['total_cholesterol'] - by_key['hdl'], 0)
  if 'triglycerides' in by_key and 'hdl' in by_key and by_key['hdl'] > 0:
    derived['triglyceride_to_hdl_ratio'] = round(by_key['triglycerides'] / by_key['hdl'], 1)
  if 'ast' in by_key and 'alt' in by_key and by_key['alt'] > 0:
    derived['ast_to_alt_ratio'] = round(by_key['ast'] / by_key['alt'], 2)
  if derived:
    result['derived'] = derived
  result['counts'] = {
      s: sum(1 for f in findings if f['status'] == s)
      for s in (NORMAL, BORDERLINE, LOW, HIGH, VERY_HIGH)
  }
  return result
