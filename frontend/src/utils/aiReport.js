const firstPresent = (...values) => values.find(
    (value) => value !== undefined && value !== null && value !== ""
);

const toFiniteNumber = (value) => {
    if (typeof value === "string") {
        const normalized = value.trim().replace(/%$/, "");
        if (!normalized) return null;
        value = normalized;
    }
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
};

export const normalizeRiskScorePercent = (value) => {
    const explicitPercent = typeof value === "string" && value.trim().endsWith("%");
    const score = toFiniteNumber(value);
    if (score === null) return null;
    const percent = explicitPercent ? score : Math.abs(score) <= 1 ? score * 100 : score;
    return Math.round(Math.min(100, Math.max(0, percent)));
};

const normalizeFeature = (feature) => {
    if (typeof feature === "string") {
        return { name: feature, impact: null, direction: "Direction unavailable" };
    }
    if (!feature || typeof feature !== "object") return null;

    const name = firstPresent(feature.feature, feature.feature_name, feature.name);
    if (!name) return null;

    const explicitSignedValue = toFiniteNumber(
        firstPresent(feature.shap_value, feature.signedValue, feature.value)
    );
    const contribution = toFiniteNumber(
        firstPresent(feature.contribution, feature.importance)
    );
    const rawDirection = String(feature.direction || "").toLowerCase();
    let impact = explicitSignedValue ?? contribution;

    if (impact !== null && explicitSignedValue === null) {
        if (rawDirection.includes("negative") || rawDirection.includes("decrease") || rawDirection.includes("down")) {
            impact = -Math.abs(impact);
        } else if (rawDirection.includes("positive") || rawDirection.includes("increase") || rawDirection.includes("up")) {
            impact = Math.abs(impact);
        } else if (feature.contribution !== undefined && feature.contribution !== null) {
            impact = null;
        }
    }

    const direction = impact === null
        ? "Direction unavailable"
        : impact > 0
            ? "Increases model output"
            : impact < 0
                ? "Decreases model output"
                : "No directional impact";

    return { name: String(name), impact, direction };
};

export const buildAiReportData = (patient = {}, testData = {}) => {
    const assessment = testData.assessment || {};
    const metrics = testData.clinicalMetrics || {};
    const explanation = testData.explainability || {};
    const ecg = testData.ecg || {};
    const rawFeatures = Array.isArray(explanation.topFeatures) ? explanation.topFeatures : [];
    const features = rawFeatures
        .map(normalizeFeature)
        .filter(Boolean)
        .sort((a, b) => Math.abs(b.impact ?? 0) - Math.abs(a.impact ?? 0));

    const scorePercent = [assessment.riskScore, assessment.risk_score, patient.risk_score]
        .map(normalizeRiskScorePercent)
        .find((score) => score !== null) ?? null;

    return {
        patientName: firstPresent(patient.name, patient.patientName, testData.patient?.patientName) || "No patient selected",
        patientId: firstPresent(patient.patientId, patient.patient_id, patient._id, patient.id, testData.patient?.patientId) || "—",
        age: firstPresent(patient.age, metrics.age) ?? "—",
        sex: firstPresent(patient.gender, patient.sex, metrics.sex) || "—",
        risk: firstPresent(assessment.prediction, assessment.riskLevel, patient.riskLevel, patient.risk_level, "Pending assessment"),
        scorePercent,
        model: firstPresent(assessment.model, patient.model_name, "Model name unavailable"),
        features,
        heartRate: firstPresent(metrics.averageHeartRate, patient.heartRate, patient.heart_rate) ?? "—",
        cholesterol: firstPresent(metrics.averageCholesterol, patient.cholesterol) ?? "—",
        bloodPressure: firstPresent(
            metrics.bloodPressure,
            metrics.averageSystolicBP && metrics.averageDiastolicBP
                ? `${metrics.averageSystolicBP}/${metrics.averageDiastolicBP}`
                : undefined,
            patient.bloodPressure,
            patient.blood_pressure
        ) ?? "—",
        rhythm: firstPresent(ecg.rhythm, patient.ecg_rhythm) || "—",
        ecgStatus: firstPresent(ecg.status, patient.ecg_status) || "No ECG result is attached to this assessment.",
        clinicalRecord: {
            age: firstPresent(patient.age, metrics.age),
            sex: firstPresent(patient.sex, patient.gender, metrics.sex),
            resting_bp: firstPresent(patient.resting_bp, patient.bloodPressure, patient.blood_pressure),
            cholesterol: firstPresent(patient.cholesterol, metrics.averageCholesterol),
            max_heart_rate: firstPresent(patient.max_heart_rate, patient.heartRate, patient.heart_rate, metrics.averageHeartRate),
            fasting_blood_sugar: firstPresent(patient.fasting_blood_sugar, patient.fastingBloodSugar),
            resting_ecg: firstPresent(patient.resting_ecg),
            st_depression: firstPresent(patient.st_depression),
            chest_pain_type: firstPresent(patient.chest_pain_type),
            st_slope: firstPresent(patient.st_slope),
        },
    };
};
