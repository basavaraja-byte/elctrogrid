"""Explanation service generating human-readable insights for dispatchers and supervisors."""

from __future__ import annotations


class ExplanationService:
    """Generates transparent, rule-backed explanations for AI predictions."""

    @staticmethod
    def explain_duration(
        job_type: str,
        predicted_duration: float,
        lower_bound: float,
        upper_bound: float,
        service_zone: str,
        customer_type: str,
    ) -> str:
        cust_note = "commercial facility (higher complexity)" if customer_type == "commercial" else "residential customer"
        return (
            f"Estimated service duration for {job_type.replace('_', ' ')} in {service_zone} is "
            f"{predicted_duration:.0f} minutes (expected range: {lower_bound:.0f} - {upper_bound:.0f} min). "
            f"Prediction reflects baseline trade complexity for {cust_note}."
        )

    @staticmethod
    def explain_sla_delay(
        job_id: str | None,
        job_type: str,
        priority: str,
        delay_prob: float,
        predicted_duration: float,
        slack_min: float,
        travel_min: float,
        buffer_slack: float,
    ) -> tuple[list[str], str]:
        factors = []
        job_ref = f"Job {job_id}" if job_id else "This job"

        if buffer_slack < 15.0:
            factors.append(
                f"Severe buffer deficit: Service duration ({predicted_duration:.0f}m) + travel ({travel_min:.0f}m) "
                f"leaves only {max(0.0, buffer_slack):.0f} minutes before SLA deadline."
            )
        elif buffer_slack < 45.0:
            factors.append(
                f"Tight buffer margin: Remaining slack after travel and work is only {buffer_slack:.0f} minutes."
            )
        else:
            factors.append(
                f"Adequate buffer margin: Remaining slack after work and travel is {buffer_slack:.0f} minutes."
            )

        if priority in ["Critical", "High"]:
            factors.append(f"Elevated priority ({priority}) imposes accelerated response deadline.")

        if travel_min > 30.0:
            factors.append(f"Cross-zone transit estimated at {travel_min:.0f} minutes introduces traffic friction.")

        # Action recommendation
        if delay_prob >= 0.70:
            action = (
                f"{job_ref} is at HIGH risk of missing its SLA deadline. "
                "Action: Reassign to an idle technician in the same zone or escalate priority queue immediately."
            )
        elif delay_prob >= 0.30:
            action = (
                f"{job_ref} has MODERATE risk of delay. "
                "Action: Monitor technician travel progress; prepare standby technician in adjacent zone."
            )
        else:
            action = (
                f"{job_ref} has LOW risk of delay. "
                "Action: Proceed with standard automated dispatch schedule."
            )

        return factors, action

    @staticmethod
    def explain_disruption_risk(
        technician_id: str,
        workload_hours: float,
        tight_buffers: int,
        disruption_prob: float,
    ) -> tuple[list[str], str]:
        factors = []
        if workload_hours >= 8.0:
            factors.append(
                f"Technician workload strain: Assigned {workload_hours:.1f} hours today exceeds 8.0h standard shift limit."
            )
        if tight_buffers >= 2:
            factors.append(
                f"Schedule compression: {tight_buffers} consecutive assignments have less than 15-minute transit buffers."
            )

        if not factors:
            factors.append("Workload balance and transit buffers are within safe operating limits.")

        if disruption_prob >= 0.65:
            action = (
                f"Technician {technician_id} schedule has HIGH disruption risk. "
                "Action: Insert a 30-minute buffer window or rebalance next ticket to secondary technician."
            )
        elif disruption_prob >= 0.25:
            action = (
                f"Technician {technician_id} schedule has MODERATE disruption risk. "
                "Action: Enable live GPS tracking; alert supervisor if travel exceeds 25 minutes."
            )
        else:
            action = "Technician schedule is stable. Maintain current dispatch order."

        return factors, action

