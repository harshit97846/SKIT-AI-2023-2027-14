import React, { useMemo } from "react";
import { printClinicalReport } from "../utils/printReport";
import { buildAiReportData } from "../utils/aiReport";
import ClinicalReportPrintDocument from "./ClinicalReportPrintDocument";

const AiReport = ({ patient, testData }) => {
    const report = useMemo(() => buildAiReportData(patient, testData), [patient, testData]);
    const score = report.scorePercent === null ? "—" : `${report.scorePercent}%`;
    const latestPrediction = {
        id: patient?.prediction_id || patient?.assessment_id,
        risk_score: report.scorePercent === null ? null : report.scorePercent / 100,
        risk_level: report.risk,
        model_name: report.model,
        feature_contributions: report.features
            .filter((feature) => feature.impact !== null)
            .map((feature) => ({ feature: feature.name, contribution: feature.impact })),
        top_contributing_features: report.features.map((feature) => feature.name),
    };

    return (
        <div className="dashboard-section ai-report-section">
            <div className="section-heading">
                <div>
                    <span className="welcome-label">AI REPORT</span>
                    <h2>Clinical Assessment Summary</h2>
                    <p>
                        Structured summary based on the assessment and clinical explanation data currently available in the dashboard.
                    </p>
                </div>
                <span className="ai-report-badge">CLINICAL SUMMARY</span>
            </div>

            <div className="ai-report-card">
                <div className="ai-report-header">
                    <div>
                        <span>Patient</span>
                        <strong>{report.patientName}</strong>
                    </div>
                    <div>
                        <span>Patient ID</span>
                        <strong>{report.patientId}</strong>
                    </div>
                    <div>
                        <span>Age / Sex</span>
                        <strong>{report.age} / {report.sex}</strong>
                    </div>
                    <div>
                        <span>Assessment</span>
                        <strong>{report.risk}</strong>
                    </div>
                    <div>
                        <span>Risk Score</span>
                        <strong>{score}</strong>
                    </div>
                    <div>
                        <span>Model</span>
                        <strong>{report.model}</strong>
                    </div>
                </div>

                <div className="ai-report-grid">
                    <section className="ai-report-block">
                        <h3>Clinical Summary</h3>
                        <p>
                            {score !== "—"
                                ? <>The stored model result is <strong>{report.risk}</strong> ({score}) from the {report.model}. Review it alongside the recorded measurements: heart rate <strong>{report.heartRate} BPM</strong>, cholesterol <strong>{report.cholesterol} mg/dL</strong>, and blood pressure <strong>{report.bloodPressure} mmHg</strong>.</>
                                : "No model assessment is stored for this patient. Complete an assessment and verify the source data before generating a clinical summary."}
                        </p>
                    </section>

                    <section className="ai-report-block">
                        <h3>Model Explanation</h3>
                        {report.features.length > 0 ? (
                            <ol className="ai-report-feature-list">
                                {report.features.slice(0, 5).map((feature, index) => (
                                    <li key={`${feature.name}-${index}`}>
                                        <strong>{feature.name}</strong>
                                        <span>
                                            {feature.impact === null
                                                ? feature.direction
                                                : `${feature.direction} (${feature.impact > 0 ? "+" : ""}${feature.impact.toFixed(3)})`}
                                        </span>
                                    </li>
                                ))}
                            </ol>
                        ) : (
                            <p>No stored feature attribution is available for this assessment.</p>
                        )}
                    </section>

                    <section className="ai-report-block">
                        <h3>ECG Summary</h3>
                        <p>
                            {report.rhythm !== "—"
                                ? <>The attached ECG result reports a rhythm of <strong>{report.rhythm}</strong>.</>
                                : report.ecgStatus}
                        </p>
                    </section>

                    <section className="ai-report-block">
                        <h3>Clinical Review</h3>
                        <p>
                            This summary supports clinician review only. Confirm the source data and model output before making clinical decisions; it is not a standalone diagnosis or treatment recommendation.
                        </p>
                    </section>
                </div>

                <div className="ai-report-footer">
                    <span>Review source data and confirm the model result before clinical use.</span>
                    <button type="button" className="secondary-btn" onClick={() => printClinicalReport("clinical-report-printable-area")}>
                        Print Report
                    </button>
                </div>
            </div>

            <div className="printable-clinical-report hidden-screen" aria-hidden="true">
                <ClinicalReportPrintDocument
                    patient={patient}
                    latestClinical={report.clinicalRecord}
                    latestPrediction={latestPrediction}
                />
            </div>
        </div>
    );
};

export default AiReport;
