import test from "node:test";
import assert from "node:assert/strict";
import { buildAiReportData, normalizeRiskScorePercent } from "../../src/utils/aiReport.js";

test("normalizes fractional, percentage, and invalid risk scores", () => {
    assert.equal(normalizeRiskScorePercent(0.643), 64);
    assert.equal(normalizeRiskScorePercent("72%"), 72);
    assert.equal(normalizeRiskScorePercent(91), 91);
    assert.equal(normalizeRiskScorePercent("not available"), null);
});

test("uses stored patient risk when the report score is unavailable", () => {
    const report = buildAiReportData(
        { name: "Asha", patientId: "P-12", risk_score: 0.42 },
        { assessment: { riskScore: "—", prediction: "Moderate risk" } }
    );

    assert.equal(report.patientName, "Asha");
    assert.equal(report.patientId, "P-12");
    assert.equal(report.scorePercent, 42);
    assert.equal(report.risk, "Moderate risk");
});

test("ranks signed model attributions by their absolute impact", () => {
    const report = buildAiReportData({}, {
        explainability: {
            topFeatures: [
                { feature: "age", contribution: 0.1, shap_value: 0.1 },
                { feature: "blood pressure", contribution: 0.7, shap_value: -0.7 },
            ],
        },
    });

    assert.deepEqual(report.features.map((feature) => feature.name), ["blood pressure", "age"]);
    assert.equal(report.features[0].impact, -0.7);
    assert.equal(report.features[0].direction, "Decreases model output");
});

test("does not invent attribution direction when only magnitude is stored", () => {
    const report = buildAiReportData({}, {
        explainability: { topFeatures: [{ feature_name: "cholesterol", contribution: 0.3 }] },
    });

    assert.equal(report.features[0].impact, null);
    assert.equal(report.features[0].direction, "Direction unavailable");
});
