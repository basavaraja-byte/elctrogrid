"""Master training orchestrator for all 4 DispatchGrid AI models."""

from __future__ import annotations

import sys
from app.ai.training.train_duration import train_duration_model
from app.ai.training.train_delay import train_delay_model
from app.ai.training.train_demand import train_demand_model
from app.ai.training.train_disruption import train_disruption_model


def train_all_models() -> dict[str, dict]:
    """Train all DispatchGrid AI models sequentially and return evaluation summaries."""
    print("================================================================================")
    print("         DISPATCHGRID AI LAYER — COMPREHENSIVE MODEL TRAINING & EVALUATION     ")
    print("================================================================================\n")

    print("[1/4] Training Model 1: Job Duration Prediction Regressor...")
    dur_meta = train_duration_model()
    print("--------------------------------------------------------------------------------\n")

    print("[2/4] Training Model 2: SLA Delay Risk Classifier...")
    delay_meta = train_delay_model()
    print("--------------------------------------------------------------------------------\n")

    print("[3/4] Training Model 3: Electrical Service Demand Forecaster...")
    demand_meta = train_demand_model()
    print("--------------------------------------------------------------------------------\n")

    print("[4/4] Training Model 4: Schedule Disruption Risk Classifier...")
    disr_meta = train_disruption_model()
    print("--------------------------------------------------------------------------------\n")

    print("================================================================================")
    print("                       TRAINING & EVALUATION SUMMARY TABLE                      ")
    print("================================================================================")
    print(f"{'Model Purpose':<28} | {'Best Algorithm':<30} | {'Key Evaluation Metric':<20}")
    print("-" * 84)
    print(f"{'1. Job Duration':<28} | {dur_meta['model_name']:<30} | MAE: {dur_meta['metrics']['MAE']} min (R²: {dur_meta['metrics']['R2']})")
    print(f"{'2. SLA Delay Risk':<28} | {delay_meta['model_name']:<30} | F1: {delay_meta['metrics']['F1']} (ROC-AUC: {delay_meta['metrics']['ROC_AUC']})")
    print(f"{'3. Demand Forecasting':<28} | {demand_meta['model_name']:<30} | WAPE: {demand_meta['metrics']['WAPE']*100:.1f}% (MAE: {demand_meta['metrics']['MAE']})")
    print(f"{'4. Disruption Risk':<28} | {disr_meta['model_name']:<30} | F1: {disr_meta['metrics']['F1']} (ROC-AUC: {disr_meta['metrics']['ROC_AUC']})")
    print("================================================================================\n")

    return {
        "duration": dur_meta,
        "delay": delay_meta,
        "demand": demand_meta,
        "disruption": disr_meta,
    }


if __name__ == "__main__":
    train_all_models()

