#!/usr/bin/env python3
"""
Generate deterministic, entirely synthetic BC PharmaCare SA demo records.

Each patient is assigned a fictional policy from demo_criteria_cache.json.
60% qualify for SA coverage, 40% do not (realistic documentation gaps).
The output is replaced on each run; no existing or real records are read.
"""

import json
import random
import os
import argparse
from datetime import date, timedelta
from collections import defaultdict

random.seed(42)

PUBLIC_VISIT_FIELDS = (
    "date",
    "reason",
    "symptoms",
    "diagnosis",
    "prescribed",
    "doctor_notes",
)

# ── Name pools (BC-realistic) ─────────────────────────────────────────

FIRST_M = [
    "James","Robert","Michael","David","John","William","Richard","Joseph","Thomas","Charles",
    "Daniel","Matthew","Anthony","Donald","Mark","Paul","Steven","Andrew","Kenneth","Joshua",
    "Kevin","Brian","George","Timothy","Ronald","Edward","Jason","Jeffrey","Ryan","Jacob",
    "Gary","Nicholas","Eric","Jonathan","Stephen","Larry","Justin","Scott","Brandon","Benjamin",
    "Samuel","Raymond","Gregory","Frank","Alexander","Patrick","Jack","Dennis","Jerry","Tyler",
    "Aaron","Henry","Jose","Adam","Nathan","Zachary","Walter","Harold","Kyle","Carl",
]

FIRST_F = [
    "Mary","Patricia","Jennifer","Linda","Barbara","Elizabeth","Susan","Jessica","Sarah","Karen",
    "Lisa","Nancy","Betty","Margaret","Sandra","Ashley","Dorothy","Kimberly","Emily","Donna",
    "Michelle","Carol","Amanda","Melissa","Deborah","Stephanie","Rebecca","Sharon","Laura","Cynthia",
    "Kathleen","Amy","Angela","Shirley","Anna","Brenda","Pamela","Emma","Nicole","Helen",
    "Samantha","Katherine","Christine","Debra","Rachel","Carolyn","Janet","Catherine","Maria","Heather",
    "Diane","Julie","Joyce","Victoria","Kelly","Christina","Lauren","Joan","Evelyn","Olivia",
]

LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Wilson","Anderson",
    "Taylor","Thomas","Jackson","White","Harris","Martin","Thompson","Young","Walker","Hall",
    "Allen","Wright","Scott","Green","Baker","Adams","Nelson","Carter","Mitchell","Perez",
    "Roberts","Turner","Phillips","Campbell","Parker","Evans","Edwards","Collins","Stewart","Morris",
    "Murphy","Cook","Rogers","Morgan","Peterson","Cooper","Reed","Bailey","Bell","Rivera",
    "Wong","Patel","Singh","Kumar","Chen","Lee","Kim","Nguyen","Johal","Dhaliwal",
    "MacDonald","Fraser","Campbell","Robertson","Murray","Ross","McKenzie","MacLeod","Grant","Reid",
]

BC_CITIES = (
    ["Vancouver"] * 20 + ["Surrey"] * 12 + ["Burnaby"] * 10 + ["Richmond"] * 8 +
    ["Kelowna"] * 7 + ["Abbotsford"] * 6 + ["Coquitlam"] * 6 + ["Langley"] * 5 +
    ["Victoria"] * 8 + ["Nanaimo"] * 4 + ["Kamloops"] * 4 + ["Prince George"] * 3 +
    ["Chilliwack"] * 3 + ["Maple Ridge"] * 3 + ["New Westminster"] * 3 +
    ["North Vancouver"] * 4 + ["West Vancouver"] * 2 + ["Penticton"] * 2 +
    ["Vernon"] * 2 + ["Courtenay"] * 2
)

def rand_name(gender):
    first = random.choice(FIRST_M if gender == "M" else FIRST_F)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"

def rand_date(start_year=2023, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def visit_date_seq(n_visits, start_year=2023):
    """Generate n ascending visit dates."""
    d = rand_date(start_year, start_year)
    dates = []
    for _ in range(n_visits):
        dates.append(str(d))
        d += timedelta(days=random.randint(45, 180))
    return dates


# ── Drug categorizer ──────────────────────────────────────────────────

def categorize(drug_name: str, criteria: list) -> str:
    n = drug_name.lower()
    ct = " ".join(criteria).lower()

    if any(x in n for x in ["ferric carboxymaltose","ferumoxytol","iron deficiency","iron sucrose","iron isomaltoside"]):
        return "iron_deficiency"
    if any(x in ct for x in ["lvef","left ventricular ejection fraction","nyha","heart failure decompensation","nt-probnp"]):
        return "heart_failure"
    if any(x in n for x in ["aclidinium","umeclidinium","tiotropium","olodaterol","formoterol","roflumilast","indacaterol"]) or \
       any(x in ct for x in ["fev1/fvc","copd","chronic obstructive","lama molecule"]):
        return "copd"
    if any(x in n for x in ["dupilumab","abrocitinib","tralokinumab","upadacitinib for atopic","lebrikizumab"]) or \
       any(x in ct for x in ["easi score","atopic dermatitis","viga-ad","eczema area"]):
        return "atopic_dermatitis"
    if any(x in n for x in ["secukinumab","ixekizumab","guselkumab","risankizumab","bimekizumab","ustekinumab for plaque"]) or \
       any(x in ct for x in ["plaque psoriasis","pasi score","dlqi","psoriasis area"]):
        return "psoriasis"
    if any(x in ct for x in ["rheumatoid arthritis","das28","dmard","methotrexate failure","tender joint","swollen joint"]):
        return "rheumatoid_arthritis"
    if any(x in ct for x in ["crohn","ulcerative colitis","inflammatory bowel","harvey bradshaw","mayo score","calprotectin"]):
        return "inflammatory_bowel"
    if any(x in ct for x in ["multiple sclerosis","relapsing-remitting","edss","annualized relapse rate","mri lesion"]):
        return "multiple_sclerosis"
    if any(x in ct for x in ["pulmonary arterial hypertension","6-minute walk","who functional class","mean pulmonary"]):
        return "pulmonary_hypertension"
    if any(x in ct for x in ["migraine","acq-5 score is","episodic migraine","chronic migraine","cgrp"]):
        if "asthma" not in n and "allergic" not in n:
            return "migraine"
    if any(x in ct for x in ["osteoporosis","bone mineral density","t-score","vertebral fracture","dexa"]):
        return "osteoporosis"
    if any(x in ct for x in ["hepatitis b","hepatitis c","hbv dna","hcv rna","fibrosis","cirrhosis","genotype"]):
        return "hepatitis"
    if any(x in ct for x in ["asthma","ige","eosinophil","acq-5","inhaled corticosteroid","fev1 reversibility"]):
        return "asthma"
    if any(x in ct for x in ["schizophrenia","psychosis","antipsychotic","clozapine","depot injection","positive symptoms"]):
        return "psychiatric"
    if any(x in ct for x in ["insomnia","benzodiazepine","hypnotic","sleep"]):
        return "insomnia"
    if any(x in ct for x in ["narcolepsy","excessive daytime sleepiness","cataplexy"]):
        return "narcolepsy"
    if any(x in ct for x in ["febrile neutropenia","absolute neutrophil count","chemotherapy","g-csf"]):
        return "oncology_support"
    if any(x in ct for x in ["nausea","vomiting","antiemetic","chemotherapy-induced"]):
        return "antiemetic"
    if any(x in n for x in ["statin","simvastatin","pravastatin","lovastatin","rosuvastatin","atorvastatin"]):
        return "dyslipidemia"
    return "simple"


# ── Visit builders ────────────────────────────────────────────────────

def _visit(date_str, reason, symptoms, diagnosis, prescribed, notes):
    return {
        "date": date_str,
        "reason": reason,
        "symptoms": symptoms,
        "severity": None,
        "estimated_severity": random.randint(3, 8),
        "diagnosis": diagnosis,
        "prescribed": prescribed,
        "doctor_notes": notes,
        "is_synthetic": True,
        "source_encounter": None,
        "extracted_patient_name": None,
        "extracted_age": None,
    }


# ─── IRON DEFICIENCY ─────────────────────────────────────────────────

def gen_iron_deficiency(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(4)
    hgb = random.randint(62, 88) if qualifying else random.randint(95, 115)
    ferritin = random.randint(3, 12) if qualifying else random.randint(22, 45)
    tsat = random.randint(5, 13) if qualifying else random.randint(18, 28)
    oral_iron = qualifying or random.random() < 0.3

    v1 = _visit(dates[0], "Fatigue and shortness of breath.",
        f"Patient reports progressive fatigue for {random.randint(6,16)} weeks, exertional dyspnea, pallor. "
        f"HR {random.randint(82,102)} bpm. BP {random.randint(105,130)}/{random.randint(65,80)}. Conjunctival pallor noted.",
        "Iron deficiency anemia (IDA); Fatigue.",
        "CBC, iron studies, ferritin ordered.",
        "Patient presents with symptomatic anemia. Lab work ordered to confirm IDA and assess severity. "
        "Dietary review discussed. Patient instructed to avoid NSAIDs.")

    v2_notes = (
        f"Lab results confirm iron deficiency anemia. Hemoglobin {hgb} g/L (low). "
        f"Ferritin {ferritin} µg/L (low). Transferrin saturation (TSAT) {tsat}% (low). "
    )
    if oral_iron:
        v2_notes += (
            "Initiated oral ferrous sulfate 300 mg three times daily. "
            "Patient counselled on dietary iron sources. Follow-up in 6 weeks."
        )
    else:
        v2_notes += "Patient declines oral iron therapy. Reviewing alternative management options."

    v2 = _visit(dates[1], "Lab review — confirmed IDA.",
        f"Fatigue persists. Hemoglobin {hgb} g/L. Ferritin {ferritin} µg/L. TSAT {tsat}%. Pallor unchanged.",
        "Iron deficiency anemia, confirmed by laboratory testing.",
        "Ferrous sulfate 300 mg TID initiated." if oral_iron else "Monitoring; patient declines oral iron.",
        v2_notes)

    if qualifying:
        v3_notes = (
            f"Patient has completed a minimum 4-week trial of oral ferrous sulfate 300 mg TID. "
            f"Hemoglobin remains low at {hgb + random.randint(2, 6)} g/L despite adequate trial. "
            f"Patient reports GI intolerance including nausea and constipation; unable to tolerate continued oral iron therapy. "
            f"Documented diagnosis of iron deficiency anemia confirmed by laboratory testing: "
            f"hemoglobin {hgb} g/L, ferritin {ferritin} µg/L, TSAT {tsat}%. "
            f"Patient meets criteria for IV ferric carboxymaltose. "
            f"Referral to IV infusion clinic arranged where appropriate monitoring and management "
            f"of hypersensitivity reactions is available. Special Authority request submitted."
        )
        v3_prescribed = "Ferric carboxymaltose IV infusion (SA requested)."
    else:
        v3_notes = (
            f"Patient reports mild GI symptoms with oral iron but has not completed a minimum 4-week trial. "
            f"Hemoglobin {hgb + random.randint(5,12)} g/L. Ferritin {ferritin} µg/L. TSAT {tsat}%. "
            f"Discussed importance of completing oral iron trial before escalating to IV therapy. "
            f"Continuing current regimen. Reassess in 4 weeks."
        )
        v3_prescribed = "Ferrous sulfate 300 mg TID (continue)."

    v3 = _visit(dates[2], "IDA treatment review.",
        f"Fatigue {'slightly improved' if not qualifying else 'persists despite oral iron'}. "
        f"GI side effects {'noted' if qualifying else 'mild'}. Pallor {'persists' if qualifying else 'resolving'}.",
        "Iron deficiency anemia; Oral iron {'intolerance' if qualifying else 'trial ongoing'}.",
        v3_prescribed, v3_notes)

    v4 = _visit(dates[3], "Follow-up — IV iron therapy.",
        f"Patient {'reports improved energy levels after IV infusion' if qualifying else 'on continued oral iron; improving slowly'}.",
        "Iron deficiency anemia.",
        "Repeat CBC and iron studies in 4 weeks.",
        f"{'IV ferric carboxymaltose administered in infusion clinic. Patient tolerated well. Hemoglobin improving.' if qualifying else 'Oral iron ongoing. Hemoglobin trending up. Will reassess IV iron need at next visit.'}"
    )
    return [v1, v2, v3, v4]


# ─── HEART FAILURE ────────────────────────────────────────────────────

def gen_heart_failure(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(5)
    lvef = random.randint(28, 40) if qualifying else random.randint(43, 52)
    nyha = random.choice(["II", "III"]) if qualifying else random.choice(["I", "II"])
    hosp = qualifying and random.random() < 0.8

    v1 = _visit(dates[0], "Shortness of breath and lower extremity edema.",
        f"Progressive dyspnea on exertion for {random.randint(4,10)} weeks. "
        f"Bilateral ankle edema 2+. JVD present. Crackles at lung bases. "
        f"HR {random.randint(78,100)} bpm. BP {random.randint(105,135)}/{random.randint(70,90)}.",
        "Congestive heart failure; Dyspnea.",
        "Furosemide 40 mg daily initiated. Echocardiogram ordered.",
        "Patient presents with signs and symptoms consistent with decompensated heart failure. "
        "Echocardiogram ordered urgently. BMP and BNP ordered. Dietary sodium restriction counselled.")

    v2_notes = (
        f"Echocardiogram results: left ventricular ejection fraction (LVEF) {lvef}% — "
        f"{'reduced ejection fraction (HFrEF)' if lvef < 45 else 'preserved ejection fraction (HFpEF)'}. "
        f"Patient classified as NYHA Class {nyha} heart failure. "
        f"BNP elevated at {random.randint(400,900)} pg/mL. "
        f"Initiating guideline-directed medical therapy (GDMT): "
        f"ACE inhibitor (lisinopril 10 mg daily), beta-blocker (carvedilol 6.25 mg BID), "
        f"and mineralocorticoid receptor antagonist (spironolactone 25 mg daily)."
    )
    if hosp:
        v2_notes += (
            f" Patient required hospitalization for IV diuresis {random.randint(2,5)} months ago. "
            f"Currently on optimal GDMT as adjunct therapy."
        )

    v2 = _visit(dates[1], "Heart failure workup results.",
        f"Dyspnea with minimal exertion. NYHA Class {nyha}. LVEF {lvef}% on echo. BNP elevated.",
        f"Heart failure with {'reduced' if lvef < 45 else 'preserved'} ejection fraction; NYHA Class {nyha}.",
        "Lisinopril 10 mg daily; Carvedilol 6.25 mg BID; Furosemide 40 mg daily; Spironolactone 25 mg daily.",
        v2_notes)

    if qualifying:
        v3_notes = (
            f"Patient {random.randint(18, 85)} years of age with symptomatic chronic heart failure. "
            f"LVEF {lvef}% (reduced ejection fraction, < 45%). NYHA Class {nyha} symptoms. "
            f"{'Recent hospitalization for HF decompensation requiring IV diuretic therapy within the past 6 months.' if hosp else 'Recent course of IV diuretics in outpatient setting within the last 6 months.'} "
            f"Currently on optimal standard of care therapy including ACE inhibitor (lisinopril), "
            f"beta-blocker (carvedilol), and MRA (spironolactone). "
            f"Vericiguat proposed as adjunct therapy. Patient is 18 years of age or older. "
            f"Special Authority request submitted for vericiguat."
        )
        v3_prescribed = "Vericiguat 2.5 mg daily (SA requested); continue GDMT."
    else:
        v3_notes = (
            f"Patient with heart failure. LVEF {lvef}% on echocardiogram — preserved ejection fraction. "
            f"NYHA Class {nyha} symptoms. No hospitalizations in the past 6 months. "
            f"Currently optimizing GDMT. Will reassess for advanced therapy options at next visit. "
            f"Does not currently meet criteria for vericiguat (LVEF not < 45%)."
        )
        v3_prescribed = "Lisinopril 20 mg daily (increased); Carvedilol 12.5 mg BID (increased)."

    v3 = _visit(dates[2], "Cardiology follow-up — advanced HF therapy.",
        f"Dyspnea on {'minimal' if qualifying else 'moderate'} exertion. LVEF {lvef}%. NYHA {nyha}.",
        "Chronic heart failure; Reduced ejection fraction." if qualifying else "Chronic heart failure; Preserved ejection fraction.",
        v3_prescribed, v3_notes)

    v4 = _visit(dates[3], "Heart failure management review.",
        "Patient reports stable symptoms. Tolerating medications well. No new hospitalizations.",
        "Heart failure; Stable.",
        "Continue current regimen. Repeat echo in 3 months.",
        f"Heart failure management reviewed. {'SA approval received. Vericiguat initiated. Patient tolerating well.' if qualifying else 'Optimizing GDMT. Repeat echo ordered to reassess LVEF.'}")

    return [v1, v2, v3, v4]


# ─── COPD ─────────────────────────────────────────────────────────────

def gen_copd(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(4)
    fev1_fvc = round(random.uniform(0.52, 0.67), 2) if qualifying else round(random.uniform(0.71, 0.80), 2)
    v1 = _visit(dates[0], "Chronic cough and shortness of breath.",
        f"Progressive exertional dyspnea over {random.randint(6,24)} months. Chronic productive cough. "
        f"Smoking history {random.randint(15,40)} pack-years. SpO2 {random.randint(90,95)}% on room air. "
        f"Expiratory wheeze on auscultation. Barrel chest.",
        "Chronic obstructive pulmonary disease (COPD); Dyspnea.",
        "Spirometry ordered. Salbutamol puffer PRN.",
        "Patient presents with symptoms consistent with COPD. Spirometry ordered with bronchodilator. "
        "Smoking cessation strongly encouraged. Pulmonology referral initiated.")

    v2 = _visit(dates[1], "Spirometry results review.",
        f"Cough persistent. Dyspnea on exertion. Post-bronchodilator FEV1/FVC ratio {fev1_fvc}. "
        f"SpO2 {random.randint(91,95)}%.",
        "COPD confirmed on spirometry; Airflow limitation.",
        "Tiotropium (Spiriva) 18 mcg inhaled once daily initiated.",
        f"Post-bronchodilator spirometry confirms diagnosis of COPD. "
        f"FEV1/FVC ratio {fev1_fvc} {'(< 0.70 — diagnostic for COPD)' if fev1_fvc < 0.70 else '(borderline — monitoring)'}. "
        f"Initiating tiotropium (long-acting muscarinic antagonist, LAMA) as first-line therapy. "
        f"Inhaler technique reviewed.")

    if qualifying:
        v3_notes = (
            f"Patient with confirmed diagnosis of COPD. Post-bronchodilator FEV1/FVC {fev1_fvc} (< 0.70). "
            f"Completed minimum one-month trial of tiotropium inhalers (LAMA) — inadequate symptom control, "
            f"patient reports continued dyspnea and exercise intolerance. "
            f"Also trialled umeclidinium (Incruse Ellipta) for one month — similarly inadequate response. "
            f"Has failed both regular benefit LAMA molecules: tiotropium inhalation solution and umeclidinium dry powder inhaler. "
            f"Aclidinium (Tudorza Genuair) requested under Special Authority as per criteria. "
            f"Special Authority request submitted."
        )
        v3_prescribed = f"{drug.split()[0].title()} inhaler (SA requested)."
    else:
        v3_notes = (
            f"Patient on tiotropium since last visit. Reports partial improvement. "
            f"FEV1/FVC {fev1_fvc}. Has not yet completed trial of all regular benefit LAMA molecules. "
            f"Will continue tiotropium for another month before considering alternative LAMA. "
            f"Pulmonary rehabilitation referral provided."
        )
        v3_prescribed = "Tiotropium (Spiriva) 18 mcg daily (continue)."

    v3 = _visit(dates[2], "COPD — LAMA therapy review.",
        f"Dyspnea {'persists despite LAMA therapy' if qualifying else 'partially improved on tiotropium'}. "
        f"FEV1/FVC {fev1_fvc}. SpO2 {random.randint(90,95)}%.",
        "COPD; Limited response to bronchodilator therapy.",
        v3_prescribed, v3_notes)

    v4 = _visit(dates[3], "COPD management follow-up.",
        "Dyspnea stable. Using inhalers as directed. No recent exacerbations.",
        "COPD; Stable.",
        "Continue current inhaler regimen. Annual influenza vaccine.",
        f"{'SA approved. Aclidinium initiated. Patient reports improved symptom control.' if qualifying else 'Continuing LAMA optimization. Reassess at next visit.'}")

    return [v1, v2, v3, v4]


# ─── ATOPIC DERMATITIS ────────────────────────────────────────────────

def gen_atopic_dermatitis(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(5)
    easi = random.randint(18, 38) if qualifying else random.randint(8, 14)
    viga = random.randint(3, 4) if qualifying else random.randint(1, 2)
    v1 = _visit(dates[0], "Severe eczema flare.",
        f"Widespread pruritic, erythematous, oozing plaques on trunk, extremities, and face. "
        f"EASI score {easi}. vIGA-AD score {viga}. Sleep disruption due to itch. "
        f"Prior use of topical corticosteroids and calcineurin inhibitors.",
        "Atopic dermatitis (AD), moderate-to-severe.",
        "Topical mometasone 0.1% cream, tacrolimus 0.1% ointment.",
        "Patient with long-standing moderate-to-severe atopic dermatitis. Extensive involvement noted. "
        "EASI score documented. Topical therapy reinforced. Dermatology referral provided.")

    v2 = _visit(dates[1], "Dermatology assessment — atopic dermatitis.",
        f"EASI score {easi}. vIGA-AD {viga}. Widespread involvement. Sleep disruption. "
        f"Maximally tolerated topical therapies have been inadequate.",
        "Moderate-to-severe atopic dermatitis; Inadequate response to topicals.",
        "Phototherapy referral; Methotrexate 10 mg weekly initiated." if qualifying else "Continue topical therapy. Phototherapy referral.",
        f"Dermatology assessment completed. Patient has severe atopic dermatitis with EASI {easi} and vIGA-AD {viga}. "
        f"Patient has failed maximally tolerated topical therapies for AD. "
        f"{'Initiating methotrexate as systemic immunomodulator. Phototherapy course completed — inadequate benefit.' if qualifying else 'Initiating phototherapy course. Will reassess systemic therapy need.'}")

    if qualifying:
        v3_notes = (
            f"Patient assessed by dermatologist with expertise in management of moderate-to-severe atopic dermatitis. "
            f"EASI score {easi} (≥ 16) and vIGA-AD score {viga} (≥ 3) documented. "
            f"Patient has failed maximally tolerated medical topical therapies combined with phototherapy. "
            f"Has also failed treatment with at least 2 of the 4 systemic immunomodulators: "
            f"methotrexate (inadequate response after 3 months) and cyclosporine (discontinued due to renal side effects). "
            f"Patient 12 years of age or older. "
            f"Biologic therapy (dupilumab / abrocitinib) requested under Special Authority. "
            f"Special Authority request submitted by dermatologist."
        )
        v3_prescribed = f"{drug.split()[0].title()} (SA requested by dermatologist)."
    else:
        v3_notes = (
            f"Atopic dermatitis management review. EASI {easi} — below threshold of 16 for biologic therapy. "
            f"vIGA-AD {viga}. Topical therapy ongoing. Has not yet completed trial of 2 systemic immunomodulators. "
            f"Will continue current regimen and optimize topical therapy. "
            f"Reassess for biologic eligibility if EASI worsens or systemic trials are exhausted."
        )
        v3_prescribed = "Cyclosporine 3 mg/kg/day initiated; continue topicals."

    v3 = _visit(dates[2], "Biologic therapy consideration for AD.",
        f"EASI {easi}. vIGA-AD {viga}. Significant impact on quality of life.",
        "Moderate-to-severe atopic dermatitis; {'Biologic therapy indicated' if qualifying else 'systemic therapy ongoing'}.",
        v3_prescribed, v3_notes)

    v4 = _visit(dates[3], "AD follow-up.",
        f"Skin {'significantly improved' if qualifying else 'partially improved'} on current regimen.",
        "Atopic dermatitis; {'Responding to biologic therapy' if qualifying else 'Ongoing management'}.",
        "Continue current therapy. Reassess EASI in 3 months.",
        f"{'SA approved. Biologic therapy initiated. EASI improving.' if qualifying else 'Optimizing systemic therapy. Monitor for adverse effects.'}")

    return [v1, v2, v3, v4]


# ─── PSORIASIS ────────────────────────────────────────────────────────

def gen_psoriasis(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(5)
    pasi = random.randint(12, 28) if qualifying else random.randint(4, 9)
    dlqi = random.randint(11, 20) if qualifying else random.randint(3, 8)
    bsa = random.randint(10, 35) if qualifying else random.randint(2, 8)

    v1 = _visit(dates[0], "Plaque psoriasis flare.",
        f"Thick erythematous plaques with silvery scale on elbows, knees, scalp, and trunk. "
        f"BSA involved {bsa}%. PASI score {pasi}. DLQI {dlqi}. Joint tenderness absent.",
        "Plaque psoriasis, moderate-to-severe.",
        "Topical calcipotriol/betamethasone ointment; emollients.",
        "Patient with chronic plaque psoriasis. Significant BSA involvement documented. "
        "PASI and DLQI scores recorded. Topical therapy reviewed. Dermatology referral.")

    v2 = _visit(dates[1], "Dermatology — psoriasis assessment.",
        f"PASI {pasi}. DLQI {dlqi}. BSA {bsa}%. Failed topical therapy.",
        "Moderate-to-severe plaque psoriasis; Inadequate topical response.",
        "Phototherapy (NBUVB) initiated." if qualifying else "Continue topical therapy. Phototherapy discussed.",
        f"Patient with moderate-to-severe plaque psoriasis. PASI {pasi}, DLQI {dlqi}, BSA {bsa}%. "
        f"{'Failed topical therapy. Starting phototherapy (NBUVB).' if qualifying else 'Continuing topicals. Phototherapy discussed.'}")

    if qualifying:
        v3_notes = (
            f"Dermatologist assessment for biologic therapy. PASI score {pasi} (moderate-to-severe), "
            f"DLQI {dlqi}, BSA {bsa}%. "
            f"Patient has failed two prior conventional systemic therapies: "
            f"methotrexate (inadequate response at 6 months) and cyclosporine (hepatotoxicity). "
            f"Phototherapy course completed — inadequate sustained response. "
            f"Patient is a candidate for biologic therapy under Special Authority. "
            f"Request submitted by dermatologist for {drug}. Baseline screening completed."
        )
        v3_prescribed = f"{drug.split()[0].title()} injection (SA requested by dermatologist)."
    else:
        v3_notes = (
            f"Psoriasis management review. PASI {pasi} — does not meet threshold for biologic therapy. "
            f"DLQI {dlqi}. Has not yet failed two conventional systemic therapies. "
            f"Currently trialling methotrexate. Will reassess in 3 months."
        )
        v3_prescribed = "Methotrexate 15 mg weekly; folic acid 5 mg weekly."

    v3 = _visit(dates[2], "Psoriasis — biologic therapy assessment.",
        f"PASI {pasi}. DLQI {dlqi}. {'Failed prior systemic therapies.' if qualifying else 'On systemic therapy.'}",
        "Moderate-to-severe plaque psoriasis.",
        v3_prescribed, v3_notes)

    v4 = _visit(dates[3], "Psoriasis follow-up.",
        f"Skin {'markedly improved' if qualifying else 'partially improved'} on current therapy.",
        "Plaque psoriasis; {'Biologic therapy response' if qualifying else 'Systemic therapy ongoing'}.",
        "Continue current therapy. PASI reassessment in 12 weeks.",
        f"{'SA approved. Biologic therapy initiated. PASI 75 response expected.' if qualifying else 'Methotrexate optimization ongoing. Reassess for biologic eligibility.'}")

    return [v1, v2, v3, v4]


# ─── RHEUMATOID ARTHRITIS ─────────────────────────────────────────────

def gen_rheumatoid_arthritis(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(5)
    das28 = round(random.uniform(3.5, 6.2), 1) if qualifying else round(random.uniform(1.8, 2.8), 1)
    tender = random.randint(6, 18) if qualifying else random.randint(1, 4)
    swollen = random.randint(4, 12) if qualifying else random.randint(0, 2)
    crp = random.randint(18, 65) if qualifying else random.randint(4, 12)

    v1 = _visit(dates[0], "Joint pain and morning stiffness.",
        f"Bilateral symmetric polyarthritis. Morning stiffness > 1 hour. "
        f"Tender joint count {tender}, swollen joint count {swollen}. "
        f"RF and anti-CCP positive. CRP {crp} mg/L.",
        "Rheumatoid arthritis (RA); Active disease.",
        "Naproxen 500 mg BID; Rheumatology referral.",
        "Patient presents with symmetrical polyarthritis consistent with RA. "
        "Serology positive. Baseline DAS28 and imaging ordered. Rheumatology referral provided.")

    v2 = _visit(dates[1], "Rheumatology — RA assessment.",
        f"DAS28 score {das28}. TJC {tender}, SJC {swollen}. CRP {crp} mg/L. RF positive. Anti-CCP positive.",
        "Rheumatoid arthritis, active disease.",
        "Methotrexate 15 mg weekly; Folic acid 5 mg weekly.",
        f"Rheumatology assessment confirms active RA. DAS28 {das28}. "
        f"Initiating methotrexate as first conventional DMARD. "
        f"Patient counselled on methotrexate side effects and monitoring requirements. "
        f"Baseline LFTs, CBC ordered.")

    if qualifying:
        v3_notes = (
            f"Patient with active rheumatoid arthritis assessed by rheumatologist. "
            f"DAS28 score {das28} (≥ 3.2 — moderate-to-severe disease activity). "
            f"Tender joint count {tender}, swollen joint count {swollen}. CRP {crp} mg/L. "
            f"Patient has failed an adequate trial of methotrexate (15 mg weekly x 6 months — "
            f"inadequate DAS28 response) and leflunomide (20 mg daily x 4 months — "
            f"GI intolerance requiring discontinuation). "
            f"Has trialled 2 conventional DMARDs including methotrexate as required. "
            f"Biologic DMARD (targeted therapy) indicated. Request submitted by rheumatologist "
            f"for {drug}. Baseline TB test, hepatitis B/C serology, chest X-ray completed."
        )
        v3_prescribed = f"{drug.split()[0].title()} (SA requested by rheumatologist)."
    else:
        v3_notes = (
            f"RA management review. DAS28 {das28} — low disease activity. "
            f"Patient currently on methotrexate monotherapy. TJC {tender}, SJC {swollen}. "
            f"Has not yet failed two conventional DMARDs. "
            f"Continue optimizing DMARD therapy before considering biologic. "
            f"Hydroxychloroquine added for additional disease control."
        )
        v3_prescribed = "Methotrexate 20 mg weekly (increased); Hydroxychloroquine 200 mg BID added."

    v3 = _visit(dates[2], "RA — biologic therapy assessment.",
        f"DAS28 {das28}. TJC {tender}, SJC {swollen}. {'Inadequate DMARD response.' if qualifying else 'Low disease activity on current therapy.'}",
        "Rheumatoid arthritis; {'Active, DMARD failure' if qualifying else 'Low disease activity'}.",
        v3_prescribed, v3_notes)

    v4 = _visit(dates[3], "RA follow-up.",
        f"Joint symptoms {'significantly improved' if qualifying else 'stable on current regimen'}.",
        "Rheumatoid arthritis; {'Biologic therapy response' if qualifying else 'Stable on DMARD'}.",
        "Continue therapy. DAS28 reassessment in 3 months.",
        f"{'SA approved. Biologic therapy initiated. DAS28 improving toward remission.' if qualifying else 'DMARD combination ongoing. Reassess in 3 months.'}")

    return [v1, v2, v3, v4]


# ─── INFLAMMATORY BOWEL ───────────────────────────────────────────────

def gen_inflammatory_bowel(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(5)
    hbi = random.randint(8, 16) if qualifying else random.randint(2, 5)
    crp = random.randint(25, 90) if qualifying else random.randint(3, 12)
    disease = random.choice(["Crohn's disease", "ulcerative colitis"])

    v1 = _visit(dates[0], "Abdominal pain and diarrhea.",
        f"Crampy abdominal pain, {random.randint(5,12)} loose stools/day, rectal bleeding, fatigue. "
        f"Weight loss {random.randint(3,8)} kg over {random.randint(3,6)} months. "
        f"CRP {crp} mg/L. Fecal calprotectin elevated.",
        f"{disease.title()}; Active disease.",
        "Mesalamine 4 g daily; Gastroenterology referral urgently.",
        f"Patient with active {disease}. Colonoscopy ordered. Gastroenterology referral provided.")

    v2 = _visit(dates[1], "Gastroenterology assessment.",
        f"Colonoscopy confirms active {disease}. Harvey-Bradshaw Index (HBI) {hbi}. CRP {crp} mg/L. "
        f"Calprotectin markedly elevated.",
        f"{disease.title()}, moderate-to-severe.",
        "Prednisone 40 mg daily tapering; Azathioprine 2.5 mg/kg daily initiated.",
        f"Gastroenterology assessment. {disease.title()} confirmed on colonoscopy — moderate-to-severe. "
        f"HBI {hbi}. Initiating corticosteroid induction and azathioprine maintenance.")

    if qualifying:
        v3_notes = (
            f"Gastroenterologist assessment for biologic therapy in {disease}. "
            f"Harvey-Bradshaw Index {hbi} (moderate-to-severe disease activity). CRP {crp} mg/L. "
            f"Patient has failed adequate trials of conventional therapy: "
            f"azathioprine 2.5 mg/kg x 6 months (inadequate response), "
            f"methotrexate 25 mg SC weekly x 4 months (hepatotoxicity). "
            f"Corticosteroid-dependent disease. "
            f"Biologic therapy (anti-TNF) indicated. Special Authority request submitted "
            f"by gastroenterologist for {drug}. TB test, hepatitis B/C serology completed."
        )
        v3_prescribed = f"{drug.split()[0].title()} injection (SA requested by gastroenterologist)."
    else:
        v3_notes = (
            f"IBD management review. HBI {hbi} — mild disease activity. "
            f"Patient has only trialled azathioprine monotherapy to date. "
            f"Has not yet failed two conventional therapies as required. "
            f"Adding methotrexate. Reassess for biologic eligibility in 6 months."
        )
        v3_prescribed = "Azathioprine 2 mg/kg (continue); Methotrexate 20 mg SC weekly added."

    v3 = _visit(dates[2], f"{disease.title()} — biologic therapy assessment.",
        f"HBI {hbi}. CRP {crp} mg/L. {'Multiple conventional therapy failures.' if qualifying else 'Ongoing conventional therapy.'}",
        f"{disease.title()}; {'Active, biologic indicated' if qualifying else 'Moderate activity, optimizing treatment'}.",
        v3_prescribed, v3_notes)

    v4 = _visit(dates[3], "IBD follow-up.",
        f"GI symptoms {'significantly improved' if qualifying else 'stabilizing on current therapy'}.",
        f"{disease.title()}; {'Biologic therapy response' if qualifying else 'Ongoing management'}.",
        "Repeat colonoscopy in 6 months. Continue therapy.",
        f"{'SA approved. Biologic therapy initiated. Symptoms improving.' if qualifying else 'Conventional therapy ongoing. Reassess for biologic eligibility.'}")

    return [v1, v2, v3, v4]


# ─── MULTIPLE SCLEROSIS ───────────────────────────────────────────────

def gen_multiple_sclerosis(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(5)
    edss = round(random.uniform(2.0, 5.5), 1) if qualifying else round(random.uniform(6.0, 7.5), 1)
    relapses = random.randint(2, 4) if qualifying else random.randint(0, 1)

    v1 = _visit(dates[0], "Visual disturbance and limb weakness.",
        f"Episode of optic neuritis resolved over 6 weeks. Transient right arm weakness. "
        f"Fatigue and cognitive fog. EDSS {edss}. MRI brain: {random.randint(4,12)} T2 lesions.",
        "Relapsing-remitting multiple sclerosis (RRMS); Active disease.",
        "Methylprednisolone 1000 mg IV x 3 days; Neurology referral.",
        "Patient with MS relapse. MRI confirms active inflammatory disease. Neurology referral provided.")

    v2 = _visit(dates[1], "Neurology — MS assessment.",
        f"EDSS {edss}. {relapses} clinical relapses in past 12 months. MRI: new T2 lesions on annual MRI.",
        "Relapsing-remitting MS; Active disease on MRI.",
        "Interferon beta-1a (Avonex) 30 mcg IM weekly initiated.",
        f"Neurologist assessment. RRMS confirmed. EDSS {edss}. "
        f"Annualized relapse rate {relapses} relapses/year. Initiating first-line DMT (interferon beta-1a).")

    if qualifying:
        v3_notes = (
            f"Neurology follow-up for highly active RRMS. "
            f"EDSS {edss}. Annualized relapse rate {relapses} relapses in past 12 months. "
            f"MRI demonstrates new T2/FLAIR lesions despite first-line DMT. "
            f"Patient has failed interferon beta-1a (inadequate efficacy — {relapses} relapses on therapy). "
            f"Has also trialled glatiramer acetate — discontinued due to injection site reactions. "
            f"Meets criteria for highly active MS requiring second-line high-efficacy DMT. "
            f"Special Authority request submitted by neurologist for {drug}. "
            f"Baseline MRI, JC virus antibody index, CBC, LFTs completed."
        )
        v3_prescribed = f"{drug.split()[0].title()} (SA requested by neurologist)."
    else:
        v3_notes = (
            f"MS management review. EDSS {edss}. {relapses} relapses in past year — low relapse rate. "
            f"Stable on current first-line DMT. No new MRI lesions. "
            f"Does not meet criteria for high-efficacy therapy escalation at this time. "
            f"Continue current disease-modifying therapy with annual monitoring."
        )
        v3_prescribed = "Interferon beta-1a 30 mcg IM weekly (continue). Annual MRI."

    v3 = _visit(dates[2], "MS — high-efficacy DMT assessment.",
        f"EDSS {edss}. {'Active disease on first-line DMT.' if qualifying else 'Stable on current DMT.'}",
        "Relapsing-remitting MS.",
        v3_prescribed, v3_notes)

    v4 = _visit(dates[3], "MS follow-up.",
        f"Neurological status {'stable on high-efficacy therapy' if qualifying else 'stable — no relapses'}.",
        "RRMS; Stable.",
        "Annual MRI. Continue DMT. Monitor CBC and LFTs.",
        f"{'SA approved. High-efficacy DMT initiated. No new relapses in 6 months.' if qualifying else 'First-line DMT continued. Reassess annually.'}")

    return [v1, v2, v3, v4]


# ─── PULMONARY ARTERIAL HYPERTENSION ─────────────────────────────────

def gen_pulmonary_hypertension(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(4)
    who_fc = random.choice(["II", "III"]) if qualifying else random.choice(["I"])
    six_mwt = random.randint(280, 380) if qualifying else random.randint(420, 500)
    mpap = random.randint(26, 55) if qualifying else random.randint(15, 22)

    v1 = _visit(dates[0], "Progressive dyspnea and syncope.",
        f"Progressive exertional dyspnea, pre-syncope, fatigue. WHO Functional Class {who_fc}. "
        f"6-minute walk test (6MWT) {six_mwt} metres. Loud P2. Right heart strain on ECG.",
        "Pulmonary arterial hypertension (PAH); Suspected.",
        "Cardiology referral; Echocardiogram ordered.",
        "Suspected PAH based on clinical presentation. Right heart catheterization (RHC) ordered.")

    v2 = _visit(dates[1], "PAH workup — right heart catheterization.",
        f"RHC: mean pulmonary arterial pressure (mPAP) {mpap} mmHg. "
        f"WHO FC {who_fc}. 6MWT {six_mwt} m.",
        f"Pulmonary arterial hypertension, {'confirmed on RHC' if mpap > 25 else 'borderline — monitoring'}. WHO FC {who_fc}.",
        "Sildenafil 20 mg TID initiated." if qualifying else "Observation; lifestyle modifications.",
        f"RHC confirms PAH: mPAP {mpap} mmHg {'(> 25 mmHg — diagnostic)' if mpap > 25 else '(borderline)'}. "
        f"WHO FC {who_fc}. 6MWT {six_mwt} m. {'Initiating oral PAH-specific therapy.' if qualifying else 'Monitoring — does not yet meet threshold for therapy.'}")

    if qualifying:
        v3_notes = (
            f"Pulmonary hypertension specialist assessment. PAH confirmed on right heart catheterization: "
            f"mPAP {mpap} mmHg. WHO Functional Class {who_fc}. 6-minute walk test {six_mwt} metres. "
            f"Patient requires PAH-specific combination therapy. "
            f"Ambrisentan / bosentan / treprostinil indicated as per Canadian PAH guidelines. "
            f"Special Authority request submitted for {drug} by pulmonary hypertension specialist."
        )
        v3_prescribed = f"{drug.split()[0].title()} (SA requested by PAH specialist)."
    else:
        v3_notes = (
            f"PAH assessment. mPAP {mpap} mmHg — does not meet PAH diagnostic threshold (>25 mmHg). "
            f"WHO FC {who_fc}. 6MWT {six_mwt} m — within normal range. "
            f"Does not meet criteria for PAH-specific therapy. Reassess in 6 months."
        )
        v3_prescribed = "Lifestyle modification. Repeat echo in 6 months."

    v3 = _visit(dates[2], "PAH specialist assessment.",
        f"WHO FC {who_fc}. 6MWT {six_mwt} m. mPAP {mpap} mmHg.",
        "Pulmonary arterial hypertension.",
        v3_prescribed, v3_notes)

    return [v1, v2, v3]


# ─── MIGRAINE ─────────────────────────────────────────────────────────

def gen_migraine(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(4)
    monthly = random.randint(8, 20) if qualifying else random.randint(2, 3)
    v1 = _visit(dates[0], "Frequent migraines.",
        f"Recurrent severe unilateral throbbing headaches with nausea, photophobia, phonophobia. "
        f"Average {monthly} migraine days per month over the past 3 months. "
        f"Significant functional impairment. HIT-6 score {random.randint(58, 68)}.",
        "Episodic migraine, high-frequency.",
        "Sumatriptan 100 mg PRN; Neurology referral.",
        "Patient with frequent episodic migraines. ICHD-3 criteria met. "
        "Preventive therapy indicated. Neurology referral provided.")

    v2 = _visit(dates[1], "Neurology — migraine prevention.",
        f"{monthly} migraine days/month. Failed acute therapy. Initiating preventive treatment.",
        "High-frequency episodic migraine; Preventive therapy initiated.",
        "Topiramate 50 mg BID initiated." if qualifying else "Amitriptyline 25 mg nightly initiated.",
        f"Neurologist assessment. {monthly} migraine days/month. "
        f"{'Initiating topiramate as first-line migraine prophylaxis.' if qualifying else 'Initiating amitriptyline as first-line prophylaxis.'} "
        f"Migraine diary requested.")

    if qualifying:
        v3_notes = (
            f"Migraine management review. Patient with {monthly} migraine days per month — "
            f"{'episodic migraine (≥ 8 days/month)' if monthly < 15 else 'chronic migraine (≥ 15 days/month)'}. "
            f"Has failed adequate trials of at least three preventive therapies: "
            f"topiramate 100 mg BID (2 months — inadequate response), "
            f"propranolol 80 mg BID (3 months — inadequate response), "
            f"amitriptyline 75 mg (2 months — discontinued due to sedation). "
            f"Candidate for CGRP monoclonal antibody therapy under Special Authority. "
            f"Special Authority request submitted by neurologist for {drug}. "
            f"Baseline migraine frequency documented via 90-day headache diary."
        )
        v3_prescribed = f"{drug.split()[0].title()} injection (SA requested by neurologist)."
    else:
        v3_notes = (
            f"Migraine review. {monthly} migraine days/month — below threshold for biologic therapy. "
            f"Currently trialling first-line prophylaxis. Has not yet failed the required number "
            f"of preventive therapies. Continue current preventive. Reassess in 3 months."
        )
        v3_prescribed = "Topiramate 75 mg BID (titrating); continue sumatriptan PRN."

    v3 = _visit(dates[2], "Migraine — CGRP inhibitor assessment.",
        f"{monthly} migraine days/month. {'Multiple preventive failures.' if qualifying else 'On first preventive therapy.'}",
        "Migraine, {'chronic/episodic' if qualifying else 'episodic'}; {'Refractory to multiple preventives' if qualifying else 'Initiating prophylaxis'}.",
        v3_prescribed, v3_notes)

    return [v1, v2, v3]


# ─── OSTEOPOROSIS ─────────────────────────────────────────────────────

def gen_osteoporosis(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(4)
    t_score = round(random.uniform(-3.5, -2.6), 1) if qualifying else round(random.uniform(-2.3, -1.5), 1)
    fracture = qualifying and random.random() < 0.7

    v1 = _visit(dates[0], "Fall and back pain — osteoporosis screening.",
        f"{'Vertebral fracture on plain X-ray. ' if fracture else ''}Back pain after minimal trauma. "
        f"Height loss {random.randint(2,5)} cm. DEXA scan ordered.",
        "Osteoporosis; Vertebral fracture." if fracture else "Osteopenia/Osteoporosis; Screening.",
        "Calcium 1000 mg daily; Vitamin D 1000 IU daily. DEXA ordered.",
        "Patient presents with osteoporosis risk factors. DEXA ordered. "
        "Calcium and vitamin D initiated. Fall prevention counselled.")

    v2 = _visit(dates[1], "DEXA scan results.",
        f"DEXA scan: T-score {'lumbar spine ' + str(t_score) + ', hip -' + str(round(abs(t_score) - 0.2, 1))}. "
        f"{'Vertebral fracture confirmed.' if fracture else 'No fracture on imaging.'}",
        f"Postmenopausal osteoporosis; T-score {t_score}.",
        "Alendronate 70 mg weekly initiated." if qualifying else "Calcium and vitamin D; lifestyle modification.",
        f"DEXA confirms osteoporosis: T-score {t_score} ({'< -2.5 — osteoporosis' if t_score < -2.5 else '-2.5 to -1.0 — osteopenia'}). "
        f"{'Vertebral fracture present.' if fracture else ''} "
        f"{'Initiating bisphosphonate therapy.' if qualifying else 'T-score above osteoporosis threshold. Continue calcium and Vitamin D.'}")

    if qualifying:
        v3_notes = (
            f"Postmenopausal osteoporosis management. DEXA T-score {t_score} (< -2.5 — diagnostic). "
            f"{'Vertebral fracture documented on imaging.' if fracture else 'High fracture risk by FRAX score.'} "
            f"Has failed or is intolerant to bisphosphonate therapy: "
            f"alendronate discontinued after 2 years due to jaw discomfort and GERD. "
            f"Meets criteria for denosumab / zoledronic acid / romosozumab under Special Authority. "
            f"Special Authority request submitted for {drug}. "
            f"25-OH Vitamin D level adequate. Patient is postmenopausal female."
        )
        v3_prescribed = f"{drug.split()[0].title()} (SA requested)."
    else:
        v3_notes = (
            f"Osteoporosis review. T-score {t_score} — does not meet threshold (< -2.5) for advanced therapy. "
            f"No fracture history. FRAX 10-year fracture risk within moderate range. "
            f"Continue calcium, vitamin D, and lifestyle modification. Reassess DEXA in 2 years."
        )
        v3_prescribed = "Calcium 1200 mg daily; Vitamin D 2000 IU daily; weight-bearing exercise."

    v3 = _visit(dates[2], "Osteoporosis advanced therapy assessment.",
        f"T-score {t_score}. {'Vertebral fracture history.' if fracture else 'No fractures.'} Risk stratification completed.",
        "Postmenopausal osteoporosis.",
        v3_prescribed, v3_notes)

    return [v1, v2, v3]


# ─── HEPATITIS ────────────────────────────────────────────────────────

def gen_hepatitis(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(4)
    hcv = "C" if "hepatitis c" in " ".join(criteria).lower() else "B"
    genotype = random.choice(["1a", "1b", "2", "3", "4"]) if hcv == "C" else None
    fibrosis = random.choice(["F2", "F3", "F4 (cirrhosis)"]) if qualifying else "F0-F1"
    viral_load = f"{random.randint(500000, 5000000):,} IU/mL" if qualifying else f"{random.randint(1000, 50000):,} IU/mL"

    v1 = _visit(dates[0], f"Hepatitis {hcv} — workup.",
        f"Incidental hepatitis {hcv} diagnosis. Fatigue, mild RUQ discomfort. "
        f"ALT {random.randint(60, 180)} U/L. AST {random.randint(45, 130)} U/L. "
        f"Hepatitis {hcv} RNA: {viral_load}.",
        f"Chronic hepatitis {hcv}.",
        "Hepatology referral. Liver biopsy / FibroScan ordered.",
        f"Chronic hepatitis {hcv} confirmed. FibroScan and hepatology referral arranged.")

    v2 = _visit(dates[1], "Hepatology assessment.",
        f"Hepatitis {hcv} RNA {viral_load}. {'Genotype ' + genotype + '. ' if genotype else ''}"
        f"FibroScan: liver stiffness consistent with fibrosis stage {fibrosis}.",
        f"Chronic hepatitis {hcv}; Fibrosis stage {fibrosis}.",
        "Antiviral therapy discussion; Treatment eligibility assessment.",
        f"Hepatology assessment. Fibrosis stage {fibrosis}. "
        f"{'Significant fibrosis — treatment strongly indicated.' if qualifying else 'Minimal fibrosis — monitoring appropriate.'} "
        f"{'Treatment planning initiated.' if qualifying else 'Annual surveillance recommended.'}")

    if qualifying:
        v3_notes = (
            f"Hepatitis {hcv} treatment assessment. "
            f"{'Genotype ' + genotype + '. ' if genotype else ''}"
            f"Viral load {viral_load}. Fibrosis stage {fibrosis}. "
            f"Patient meets criteria for direct-acting antiviral (DAA) therapy. "
            f"{'Compensated cirrhosis with Child-Pugh Class A.' if 'cirrhosis' in fibrosis else 'Significant hepatic fibrosis (F2/F3).'} "
            f"Patient has not previously received DAA therapy. "
            f"No contraindications identified. Renal function adequate (eGFR {random.randint(62,95)} mL/min/1.73m²). "
            f"Special Authority request submitted for {drug} by hepatologist."
        )
        v3_prescribed = f"{drug.split()[0].title()} (SA requested by hepatologist)."
    else:
        v3_notes = (
            f"Hepatitis {hcv} monitoring. Fibrosis stage {fibrosis} — minimal fibrosis. "
            f"Patient is treatment-naive. Low fibrosis stage does not meet criteria for immediate treatment. "
            f"Annual monitoring with FibroScan and LFTs. Abstinence from alcohol counselled."
        )
        v3_prescribed = "Lifestyle modification; Annual LFTs and FibroScan."

    v3 = _visit(dates[2], f"Hepatitis {hcv} — treatment decision.",
        f"{'Significant fibrosis — treatment indicated.' if qualifying else 'Minimal fibrosis — monitoring.'}",
        f"Chronic hepatitis {hcv}; Fibrosis {fibrosis}.",
        v3_prescribed, v3_notes)

    return [v1, v2, v3]


# ─── ASTHMA ───────────────────────────────────────────────────────────

def gen_asthma(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(5)
    acq5 = round(random.uniform(2.0, 4.5), 1) if qualifying else round(random.uniform(0.5, 1.5), 1)
    exacerbations = random.randint(2, 5) if qualifying else random.randint(0, 1)
    ige = random.randint(150, 800) if qualifying else random.randint(30, 100)
    eos = random.randint(300, 900) if qualifying else random.randint(50, 150)

    v1 = _visit(dates[0], "Poorly controlled asthma.",
        f"Recurrent wheeze, cough, and dyspnea. {exacerbations} exacerbations in past 12 months requiring oral steroids. "
        f"On high-dose ICS/LABA. SpO2 {random.randint(93,97)}%. Diffuse wheeze on auscultation.",
        "Severe allergic asthma; Inadequate control.",
        "Prednisone 40 mg x 5 days; Increase ICS dose.",
        "Severe asthma with poor control on high-dose ICS/LABA. Allergy testing ordered. Respirology referral.")

    v2 = _visit(dates[1], "Respirology assessment — severe asthma.",
        f"ACQ-5 score {acq5}. {exacerbations} exacerbations past 12 months. "
        f"IgE {ige} kIU/L. Blood eosinophils {eos} cells/µL. Positive skin test to house dust mite.",
        "Severe allergic asthma; Inadequately controlled on high-dose ICS.",
        "Optimize ICS/LABA/LAMA. Tiotropium add-on initiated.",
        f"Severe asthma assessment. ACQ-5 {acq5}. IgE {ige}. Eosinophils {eos}. "
        f"{'Positive perennial aeroallergen skin test. Eligible for biologic therapy assessment.' if qualifying else 'Controlled — biologic not indicated.'}")

    if qualifying:
        v3_notes = (
            f"Biologic therapy assessment for severe allergic asthma. Patient 12 years or older. "
            f"Symptoms inadequately controlled on high-dose ICS/LABA for minimum 6 months. "
            f"ACQ-5 score {acq5} (above MCID threshold). "
            f"{exacerbations} clinically significant asthma exacerbations in the past 12 months. "
            f"Positive skin test to perennial aeroallergen (house dust mite). "
            f"Baseline IgE {ige} kIU/L and weight documented prior to initiation. "
            f"Blood eosinophils {eos} cells/µL. "
            f"Special Authority request submitted by respirologist for omalizumab / mepolizumab. "
            f"Baseline ACQ-5 documented for renewal comparison."
        )
        v3_prescribed = f"{drug.split()[0].title()} injection (SA requested by respirologist)."
    else:
        v3_notes = (
            f"Asthma review. ACQ-5 {acq5} — well-controlled. {exacerbations} exacerbation in past year. "
            f"IgE {ige}. Does not meet threshold for biologic therapy. "
            f"Continue optimizing ICS/LABA. Add tiotropium. Reassess if control deteriorates."
        )
        v3_prescribed = "Fluticasone/salmeterol 500/50 BID; Tiotropium 18 mcg daily."

    v3 = _visit(dates[2], "Severe asthma — biologic therapy assessment.",
        f"ACQ-5 {acq5}. {exacerbations} exacerbations/year. IgE {ige}. Eos {eos}.",
        "Severe allergic asthma.",
        v3_prescribed, v3_notes)

    return [v1, v2, v3]


# ─── PSYCHIATRIC ─────────────────────────────────────────────────────

def gen_psychiatric(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(4)
    failed_n = random.randint(2, 4) if qualifying else 0
    panss = random.randint(80, 110) if qualifying else random.randint(45, 65)

    v1 = _visit(dates[0], "Psychiatric assessment — psychosis.",
        f"Auditory hallucinations, disorganized thought, paranoid ideation. "
        f"PANSS total score {panss}. Functional decline over {random.randint(3,12)} months.",
        "Schizophrenia; Active psychosis.",
        "Risperidone 4 mg daily initiated.",
        "Psychiatry assessment. Schizophrenia confirmed. First-generation antipsychotic initiated.")

    v2 = _visit(dates[1], "Psychiatry follow-up.",
        f"Partial response. PANSS {panss - random.randint(5,15)}. Persistent positive symptoms. "
        f"{'Trialled risperidone, olanzapine, haloperidol — inadequate response.' if qualifying else 'Initiating first antipsychotic.'}",
        "Schizophrenia; {'Refractory' if qualifying else 'First-episode psychosis'}.",
        "Olanzapine 10 mg daily (switch)." if qualifying else "Risperidone 6 mg daily (titrating).",
        f"{'Multiple antipsychotic failures documented. Considering clozapine / depot injection.' if qualifying else 'Titrating risperidone. Monitoring for EPS.'}")

    if qualifying:
        v3_notes = (
            f"Psychiatrist assessment for refractory schizophrenia. "
            f"PANSS total score {panss}. "
            f"Patient has failed adequate trials of {failed_n} antipsychotic agents: "
            f"risperidone (inadequate response), olanzapine (weight gain, metabolic syndrome), "
            f"haloperidol (EPS). "
            f"Identified psychiatric diagnosis confirmed. "
            f"Patient meets criteria for {drug} under Special Authority. "
            f"Special Authority request submitted by psychiatrist."
        )
        v3_prescribed = f"{drug.split()[0].title()} (SA requested by psychiatrist)."
    else:
        v3_notes = (
            f"Schizophrenia management. PANSS {panss}. First-episode, on initial antipsychotic. "
            f"Has not failed multiple agents. Continue optimizing current therapy. "
            f"Clozapine/depot not indicated at this stage."
        )
        v3_prescribed = "Risperidone 4 mg daily (continue). Psychosocial support."

    v3 = _visit(dates[2], "Schizophrenia — medication review.",
        f"PANSS {panss}. {'Multiple antipsychotic failures.' if qualifying else 'First-line treatment ongoing.'}",
        "Schizophrenia.",
        v3_prescribed, v3_notes)

    return [v1, v2, v3]


# ─── INSOMNIA ─────────────────────────────────────────────────────────

def gen_insomnia(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(3)
    # Pick a qualifying pathway from the criteria
    pathway = random.choice(["psychiatric", "benzos", "elderly"]) if qualifying else "none"

    v1 = _visit(dates[0], "Chronic insomnia.",
        f"Difficulty initiating and maintaining sleep for {random.randint(6,24)} months. "
        f"{'Concurrent psychiatric diagnosis (major depressive disorder).' if pathway == 'psychiatric' else 'No mood disorder.'} "
        f"Sleep diary shows average {random.randint(3,5)} hours/night.",
        "Chronic insomnia.",
        "Sleep hygiene counselling; CBT-I referral.",
        "Chronic insomnia assessed. Non-pharmacological therapy (CBT-I) initiated. "
        "Medication review to identify contributing factors.")

    if qualifying:
        if pathway == "psychiatric":
            v2_notes = (
                "Identified psychiatric diagnosis: major depressive disorder, confirmed. "
                "Patient meets criteria for zopiclone under Special Authority due to concurrent psychiatric diagnosis. "
                "Special Authority request submitted. Short-term zopiclone prescribed alongside psychiatric treatment."
            )
        elif pathway == "benzos":
            v2_notes = (
                "Patient has trialled and failed at least three benzodiazepines: "
                "lorazepam (tolerance developed), temazepam (morning hangover, discontinued), "
                "clonazepam (rebound insomnia). "
                "Also trialled one other hypnotic agent (trazodone — inadequate). "
                "Meets criteria for zopiclone under Special Authority. "
                "Special Authority request submitted."
            )
        else:
            v2_notes = (
                f"Patient is a fragile elderly patient ({age} years). "
                f"Severe chronic insomnia refractory to non-pharmacological measures. "
                f"Short-term zopiclone indicated under Special Authority for fragile elderly patient. "
                f"Lowest effective dose prescribed. Fall precautions counselled."
            )
        v2_prescribed = "Zopiclone 3.75 mg nightly (SA requested)."
    else:
        v2_notes = (
            "Insomnia management. CBT-I ongoing. Patient has not trialled multiple pharmacological agents. "
            "Referred to sleep clinic. Does not currently meet criteria for zopiclone SA coverage. "
            "Diphenhydramine 25 mg PRN for short-term use only."
        )
        v2_prescribed = "Diphenhydramine 25 mg PRN; continue CBT-I."

    v2 = _visit(dates[1], "Insomnia medication review.",
        f"Persistent insomnia. {'Prior benzodiazepine failures documented.' if pathway == 'benzos' else 'Sleep hygiene poor.'}",
        "Chronic insomnia.",
        v2_prescribed, v2_notes)

    return [v1, v2]


# ─── SIMPLE / DIAGNOSIS-BASED ─────────────────────────────────────────

def gen_simple(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(3)
    # Extract the condition from criteria or drug name
    condition = drug.replace("for", "—").title()

    v1 = _visit(dates[0], f"Assessment — {condition}.",
        "Patient presents for evaluation. Symptoms consistent with underlying condition. "
        "Relevant clinical history reviewed.",
        condition,
        "Referral to specialist as appropriate.",
        f"Patient assessed for {condition}. Diagnostic workup initiated. Specialist referral arranged.")

    if qualifying:
        # Build qualifying note from criteria text
        criteria_summary = "; ".join(c[:80] for c in criteria[:3])
        v2_notes = (
            f"Patient meets Special Authority criteria for {drug}. "
            f"Documentation confirms: {criteria_summary}. "
            f"Special Authority request submitted. Patient counselled on coverage and expectations."
        )
        v2_prescribed = f"{drug.split()[0].title()} (SA requested)."
    else:
        v2_notes = (
            f"Patient assessed for {drug}. Clinical documentation incomplete at this time. "
            f"Key SA criteria not yet fully documented: {criteria[0][:100] if criteria else 'see policy'}. "
            f"Follow-up required to complete documentation before SA submission."
        )
        v2_prescribed = "Supportive care; Follow-up in 4 weeks."

    v2 = _visit(dates[1], f"SA eligibility review — {condition}.",
        f"{'All criteria documented. SA submission ready.' if qualifying else 'Incomplete documentation — follow-up required.'}",
        condition,
        v2_prescribed, v2_notes)

    v3 = _visit(dates[2], "Follow-up.",
        f"Patient {'stable on therapy' if qualifying else 'documentation being completed'}.",
        condition,
        "Continue current management.",
        f"{'SA approved. Therapy initiated. Patient tolerating well.' if qualifying else 'Additional documentation gathered. SA submission pending.'}")

    return [v1, v2, v3]


# ─── ONCOLOGY SUPPORT ─────────────────────────────────────────────────

def gen_oncology_support(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(3)

    v1 = _visit(dates[0], "Oncology — chemotherapy planning.",
        f"Patient undergoing chemotherapy for malignancy. "
        f"Regimen: {'myelosuppressive' if qualifying else 'non-myelosuppressive'} chemotherapy. "
        f"Baseline ANC {round(random.uniform(1.5, 4.0), 1)} × 10⁹/L.",
        "Malignancy; Chemotherapy-induced complications management.",
        "Oncology referral; Supportive care planning.",
        "Oncology assessment. Chemotherapy regimen reviewed. Supportive care plan initiated.")

    if qualifying:
        v2_notes = (
            f"Patient receiving myelosuppressive chemotherapy with significant risk of febrile neutropenia. "
            f"Granulocyte colony-stimulating factor (G-CSF) indicated for primary or secondary prophylaxis. "
            f"Patient meets criteria for {drug} under Special Authority. "
            f"Special Authority request submitted by oncologist."
        )
        v2_prescribed = f"{drug.split()[0].title()} injection (SA requested by oncologist)."
    else:
        v2_notes = (
            "Chemotherapy regimen does not have high risk of febrile neutropenia (< 20% risk). "
            "G-CSF prophylaxis not indicated at this time. "
            "Monitoring CBC weekly. G-CSF initiated only if ANC < 0.5 × 10⁹/L with fever."
        )
        v2_prescribed = "CBC monitoring weekly. G-CSF on standby PRN."

    v2 = _visit(dates[1], "Oncology — G-CSF assessment.",
        f"On myelosuppressive chemotherapy. Febrile neutropenia risk {'high' if qualifying else 'low to moderate'}.",
        "Chemotherapy-induced neutropenia risk.",
        v2_prescribed, v2_notes)

    return [v1, v2]


# ─── NARCOLEPSY ───────────────────────────────────────────────────────

def gen_narcolepsy(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(3)

    v1 = _visit(dates[0], "Excessive daytime sleepiness.",
        f"Excessive daytime somnolence, sleep attacks, cataplexy. "
        f"Epworth Sleepiness Scale score {random.randint(16, 22)}. Falling asleep at work and while driving.",
        "Narcolepsy (suspected); Excessive daytime sleepiness.",
        "Sleep study referral; Neurology referral.",
        "Narcolepsy suspected based on clinical presentation. Polysomnography and MSLT ordered.")

    if qualifying:
        v2_notes = (
            "Narcolepsy confirmed on polysomnography and multiple sleep latency test (MSLT): "
            "mean sleep latency < 8 minutes, ≥ 2 sleep-onset REM periods. "
            "Diagnosis of narcolepsy confirmed. Patient meets criteria for modafinil under Special Authority. "
            "Special Authority request submitted. Patient counselled on driving restrictions."
        )
        v2_prescribed = "Modafinil 200 mg daily (SA requested)."
    else:
        v2_notes = (
            "Sleep study results non-diagnostic for narcolepsy. Idiopathic hypersomnia considered. "
            "Does not meet diagnostic criteria for narcolepsy at this time. "
            "Further sleep specialist assessment arranged."
        )
        v2_prescribed = "Sleep hygiene counselling. Caffeine restriction. Repeat sleep study."

    v2 = _visit(dates[1], "Narcolepsy diagnosis and SA request.",
        f"{'Narcolepsy confirmed on MSLT.' if qualifying else 'Sleep study inconclusive.'}",
        "Narcolepsy." if qualifying else "Idiopathic hypersomnia — under investigation.",
        v2_prescribed, v2_notes)

    return [v1, v2]


# ─── DYSLIPIDEMIA ─────────────────────────────────────────────────────

def gen_dyslipidemia(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(3)
    ldl = round(random.uniform(2.5, 5.0) if qualifying else random.uniform(1.5, 2.3), 1)

    v1 = _visit(dates[0], "Cardiovascular risk assessment.",
        f"LDL-C {ldl} mmol/L. Total cholesterol elevated. Family history of premature CAD. "
        f"No current statin therapy or statin intolerance.",
        "Dyslipidemia; Cardiovascular risk.",
        "Diet modification; Statin therapy consideration.",
        "Dyslipidemia assessed. Cardiovascular risk calculated. Dietary counselling provided.")

    if qualifying:
        v2_notes = (
            f"High cardiovascular risk patient. LDL-C {ldl} mmol/L despite dietary modification. "
            f"Has failed or is intolerant to maximally tolerated statin therapy: "
            f"atorvastatin (myopathy), rosuvastatin (elevated CK). "
            f"Meets criteria for {drug} under Special Authority. "
            f"Special Authority request submitted."
        )
        v2_prescribed = f"{drug.split()[0].title()} (SA requested)."
    else:
        v2_notes = (
            f"Dyslipidemia management. LDL-C {ldl} mmol/L — at target for cardiovascular risk category. "
            f"No indication for special authority drug at this time. Continue lifestyle measures."
        )
        v2_prescribed = "Lifestyle modification; Reassess in 6 months."

    v2 = _visit(dates[1], "Dyslipidemia management.",
        f"LDL-C {ldl} mmol/L. {'Statin intolerance documented.' if qualifying else 'LDL at target.'}",
        "Dyslipidemia.",
        v2_prescribed, v2_notes)

    return [v1, v2]


# ─── ANTIEMETIC ───────────────────────────────────────────────────────

def gen_antiemetic(drug, criteria, qualifying, age, gender):
    dates = visit_date_seq(2)

    v1 = _visit(dates[0], "Chemotherapy-induced nausea and vomiting.",
        f"Severe CINV following highly emetogenic chemotherapy. "
        f"Ondansetron alone {'inadequate' if qualifying else 'adequate'} for control.",
        "Chemotherapy-induced nausea and vomiting (CINV).",
        "Ondansetron 8 mg IV; Dexamethasone 12 mg IV.",
        "CINV management reviewed. Patient on highly emetogenic chemotherapy regimen.")

    if qualifying:
        v2_notes = (
            f"Patient on highly emetogenic chemotherapy (e.g. cisplatin-based). "
            f"Standard antiemetics inadequate. NK1 receptor antagonist indicated. "
            f"Special Authority request submitted for {drug} by oncologist."
        )
        v2_prescribed = f"{drug.split()[0].title()} (SA requested by oncologist)."
    else:
        v2_notes = (
            "CINV adequately controlled on standard prophylaxis. "
            "NK1 antagonist not required at this time."
        )
        v2_prescribed = "Ondansetron 8 mg TID; Dexamethasone 8 mg BID."

    v2 = _visit(dates[1], "CINV management.",
        f"CINV {'poorly controlled' if qualifying else 'well controlled'} on current regimen.",
        "CINV; Chemotherapy support.",
        v2_prescribed, v2_notes)

    return [v1, v2]


# ─── Dispatcher ──────────────────────────────────────────────────────

GENERATORS = {
    "iron_deficiency":       gen_iron_deficiency,
    "heart_failure":         gen_heart_failure,
    "copd":                  gen_copd,
    "atopic_dermatitis":     gen_atopic_dermatitis,
    "psoriasis":             gen_psoriasis,
    "rheumatoid_arthritis":  gen_rheumatoid_arthritis,
    "inflammatory_bowel":    gen_inflammatory_bowel,
    "multiple_sclerosis":    gen_multiple_sclerosis,
    "pulmonary_hypertension":gen_pulmonary_hypertension,
    "migraine":              gen_migraine,
    "osteoporosis":          gen_osteoporosis,
    "hepatitis":             gen_hepatitis,
    "asthma":                gen_asthma,
    "psychiatric":           gen_psychiatric,
    "insomnia":              gen_insomnia,
    "narcolepsy":            gen_narcolepsy,
    "oncology_support":      gen_oncology_support,
    "antiemetic":            gen_antiemetic,
    "dyslipidemia":          gen_dyslipidemia,
    "simple":                gen_simple,
}


def build_patient(pid, drug_name, criteria, qualifying):
    cat = categorize(drug_name, criteria)
    gen = GENERATORS.get(cat, gen_simple)
    gender = random.choice(["M", "F"])
    age = random.randint(22, 82)
    city = random.choice(BC_CITIES)
    try:
        visits = gen(drug_name, criteria, qualifying, age, gender)
    except Exception:
        visits = gen_simple(drug_name, criteria, qualifying, age, gender)
    visits = [
        {
            **{
                key: visit[key]
                for key in PUBLIC_VISIT_FIELDS
                if visit.get(key) not in (None, "")
            },
            "is_synthetic": True,
        }
        for visit in visits
    ]
    return {
        "id": f"DEMO-{pid:03d}",
        "name": f"Demo Patient {pid:03d}",
        "age": age,
        "city": city,
        "gender": gender,
        "target_drug": drug_name,
        "qualifies": qualifying,
        "has_family_doctor": random.random() < 0.75,
        "is_synthetic_profile": True,
        "visits": visits,
    }


# ── Distribution planner ───────────────────────────────────────────────

HIGH_VOLUME = {
    "copd", "atopic_dermatitis", "psoriasis", "rheumatoid_arthritis",
    "inflammatory_bowel", "migraine", "heart_failure", "osteoporosis",
    "hepatitis", "asthma", "insomnia", "psychiatric",
}

def plan_distribution(drugs: list, target: int) -> list:
    """
    Returns list of (drug_name, criteria, qualifying) tuples totalling ~target.
    Every drug gets at least 1 patient. High-volume categories get more.
    """
    categorized = defaultdict(list)
    for drug_name, data in drugs:
        cat = categorize(drug_name, data["criteria"])
        categorized[cat].append((drug_name, data["criteria"]))

    assignments = []
    # Guarantee 1 qualifying + 1 non-qualifying for high-volume categories
    for cat, drug_list in categorized.items():
        for (dn, cr) in drug_list:
            qual = random.random() < 0.6
            assignments.append((dn, cr, qual))

    # Top up to target by adding extra patients for high-volume categories
    extra_needed = target - len(assignments)
    hv_drugs = [(dn, cr) for cat in sorted(HIGH_VOLUME)
                for (dn, cr) in categorized.get(cat, [])]
    if hv_drugs and extra_needed > 0:
        for _ in range(extra_needed):
            dn, cr = random.choice(hv_drugs)
            assignments.append((dn, cr, random.random() < 0.6))

    random.shuffle(assignments)
    return assignments[:target]


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic demo patients")
    parser.add_argument("--count", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "data", "demo_patients.json"),
    )
    args = parser.parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    random.seed(args.seed)

    cache_path = os.path.join(
        os.path.dirname(__file__), "data", "demo_criteria_cache.json"
    )
    patients_path = args.output

    print("Loading criteria cache...")
    cache = json.load(open(cache_path))
    drugs = [(k, v) for k, v in cache.items()]
    print(f"  {len(drugs)} drugs loaded")

    TARGET = args.count
    print(f"\nPlanning {TARGET} new patients across {len(drugs)} drugs...")
    assignments = plan_distribution(drugs, TARGET)

    print(f"Generating {len(assignments)} patients...\n")
    new_patients = []
    cats = defaultdict(int)

    for i, (drug_name, criteria, qualifying) in enumerate(assignments):
        pid = i + 1
        cat = categorize(drug_name, criteria)
        cats[cat] += 1
        patient = build_patient(pid, drug_name, criteria, qualifying)
        new_patients.append(patient)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(assignments)} generated...")

    print("\nCategory distribution:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:30s}: {count}")

    qual_count = sum(1 for p in new_patients if p["qualifies"])
    print(f"\nQualifying:     {qual_count} ({qual_count/len(new_patients)*100:.0f}%)")
    print(f"Non-qualifying: {len(new_patients)-qual_count} ({(len(new_patients)-qual_count)/len(new_patients)*100:.0f}%)")

    data = {
        "notice": (
            "Entirely synthetic demonstration records. Never replace this file "
            "with identifiable patient information."
        ),
        "patients": new_patients,
    }
    os.makedirs(os.path.dirname(os.path.abspath(patients_path)), exist_ok=True)
    with open(patients_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nDone. Wrote {len(new_patients)} synthetic patients to {patients_path}.")


if __name__ == "__main__":
    main()
