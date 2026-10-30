import {
  Electrician,
  Job,
  ScoringWeights,
  ElectricianScoreBreakdown,
  ScheduleRecommendationResult,
} from '../../types';
import { mockStore } from '../mock/mockStore';

// Calculate Haversine distance in kilometers
export function calculateDistanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371; // Radius of the Earth in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
    Math.cos((lat2 * Math.PI) / 180) *
    Math.sin(dLon / 2) *
    Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Number((R * c).toFixed(1));
}

// Convert km to travel minutes in urban metro (approx 35 km/h average with traffic)
export function estimateTravelMinutes(distanceKm: number): number {
  const avgSpeedKmH = 35;
  const minutes = (distanceKm / avgSpeedKmH) * 60 + 5; // +5 mins parking/setup
  return Math.max(5, Math.round(minutes));
}

export function evaluateElectricianForJob(
  electrician: Electrician,
  job: Job,
  weights: ScoringWeights
): ElectricianScoreBreakdown {
  const infeasibilityReasons: string[] = [];
  const missingSkills: string[] = [];
  const missingEquipment: string[] = [];

  // --- HARD CONSTRAINTS ---

  // 1. Mandatory Skills Check
  if (job.requiredSkills && job.requiredSkills.length > 0) {
    for (const reqSkill of job.requiredSkills) {
      const hasSkill = electrician.skills.some(
        (s) => s.toLowerCase() === reqSkill.toLowerCase()
      );
      if (!hasSkill) {
        missingSkills.push(reqSkill);
      }
    }
  }

  // In emergency or high voltage jobs, missing skill is a strict hard failure
  if (missingSkills.length > 0) {
    infeasibilityReasons.push(
      `Lacks mandatory skill(s): ${missingSkills.join(', ')}`
    );
  }

  // 2. Required Equipment Check
  if (job.requiredEquipment && job.requiredEquipment.length > 0) {
    for (const reqEquip of job.requiredEquipment) {
      const hasEquip = electrician.equipment.some(
        (e) => e.toLowerCase() === reqEquip.toLowerCase()
      );
      if (!hasEquip) {
        missingEquipment.push(reqEquip);
      }
    }
  }

  if (missingEquipment.length > 0) {
    infeasibilityReasons.push(
      `Missing required equipment: ${missingEquipment.join(', ')}`
    );
  }

  // 3. Availability and Working Hours Overload Check
  const estimatedHours = job.estimatedDurationHours || 2.0;
  const workloadAfter = electrician.currentWorkload + estimatedHours;
  if (electrician.status === 'leave' || electrician.status === 'off_duty') {
    infeasibilityReasons.push(`Technician is currently on leave or off duty`);
  }

  if (workloadAfter > electrician.maxDailyHours) {
    infeasibilityReasons.push(
      `Exceeds maximum daily workload (${workloadAfter.toFixed(1)}h / ${electrician.maxDailyHours}h limit)`
    );
  }

  const isFeasible = infeasibilityReasons.length === 0;

  // --- SCORING MODEL (0 - 100 for each component) ---

  // 1. Skill Compatibility (weight: 25%)
  let skillScore = 100;
  if (job.requiredSkills.length > 0) {
    const matchedCount = job.requiredSkills.length - missingSkills.length;
    skillScore = Math.round((matchedCount / job.requiredSkills.length) * 100);
  }

  // Bonus if master electrician or high rating
  if (electrician.certifications.some((c) => c.includes('Master'))) {
    skillScore = Math.min(100, skillScore + 5);
  }

  // 2. Availability and Shift Compatibility (weight: 20%)
  let availabilityScore = 70;
  if (electrician.status === 'available') {
    availabilityScore = 100;
  } else if (electrician.status === 'en_route') {
    availabilityScore = 75;
  } else if (electrician.status === 'busy') {
    // Has an active job, but within shift
    availabilityScore = 55;
  } else {
    availabilityScore = 0;
  }

  // Shift matching
  if (job.preferredTimeWindow) {
    if (
      job.preferredTimeWindow.includes('08:00') &&
      electrician.shift === 'morning'
    ) {
      availabilityScore = Math.min(100, availabilityScore + 10);
    }
  }

  // 3. Proximity / Travel Distance (weight: 20%)
  const distanceKm = calculateDistanceKm(
    electrician.currentLocation.lat,
    electrician.currentLocation.lng,
    job.location.lat,
    job.location.lng
  );
  const travelMinutes = estimateTravelMinutes(distanceKm);

  // Score decreases as distance increases (100 at 0km, ~60 at 20km, ~20 at 40km)
  let travelScore = Math.max(10, Math.round(100 - distanceKm * 2.2));

  // 4. Workload Balance (weight: 15%)
  // Preference given to electricians with lighter current workloads to prevent burnout
  const workloadRatio = electrician.currentWorkload / electrician.maxDailyHours;
  let workloadScore = Math.max(10, Math.round((1 - workloadRatio) * 100));

  // 5. Deadline Feasibility (weight: 10%)
  // Feasibility of completing within deadline
  let deadlineScore = 90;
  if (job.priority === 'emergency') {
    // If technician is more than 30 mins away, deadline score drops
    if (travelMinutes > 35) {
      deadlineScore = 40;
    } else {
      deadlineScore = 100;
    }
  } else if (job.isOverdue) {
    deadlineScore = 50;
  }

  // 6. Equipment Match (weight: 10%)
  let equipmentScore = 100;
  if (job.requiredEquipment.length > 0) {
    const matchedEquip = job.requiredEquipment.length - missingEquipment.length;
    equipmentScore = Math.round(
      (matchedEquip / job.requiredEquipment.length) * 100
    );
  }

  // Calculate Weighted Overall Score
  const totalWeight =
    weights.skillCompatibility +
    weights.availabilityShift +
    weights.proximityTravel +
    weights.workloadBalance +
    weights.deadlineFeasibility +
    weights.equipmentMatch;

  const rawWeightedScore =
    (skillScore * weights.skillCompatibility +
      availabilityScore * weights.availabilityShift +
      travelScore * weights.proximityTravel +
      workloadScore * weights.workloadBalance +
      deadlineScore * weights.deadlineFeasibility +
      equipmentScore * weights.equipmentMatch) /
    totalWeight;

  // If infeasible, penalize overall score drastically so it ranks below all feasible candidates
  const overallScore = isFeasible
    ? Number(rawWeightedScore.toFixed(1))
    : Number((rawWeightedScore * 0.25).toFixed(1));

  // Build recommendation explanation
  let recommendationReason = '';
  if (isFeasible) {
    const reasons: string[] = [];
    if (distanceKm < 8) reasons.push(`Close proximity (${distanceKm} km, ~${travelMinutes}m travel)`);
    if (electrician.status === 'available') reasons.push('Immediately available');
    if (skillScore === 100) reasons.push('100% skill match');
    if (electrician.currentWorkload < 4) reasons.push(`Light current workload (${electrician.currentWorkload}h)`);
    if (electrician.rating >= 4.8) reasons.push(`High customer satisfaction rating (${electrician.rating}★)`);
    recommendationReason = reasons.join(' • ');
  } else {
    recommendationReason = `Infeasible: ${infeasibilityReasons.join('; ')}`;
  }

  return {
    electricianId: electrician.id,
    electricianName: electrician.name,
    isFeasible,
    infeasibilityReasons,
    overallScore,
    scores: {
      skillScore,
      availabilityScore,
      travelScore,
      workloadScore,
      deadlineScore,
      equipmentScore,
    },
    metrics: {
      estimatedDistanceKm: distanceKm,
      estimatedTravelMinutes: travelMinutes,
      currentWorkloadHours: electrician.currentWorkload,
      workloadAfterHours: Number(workloadAfter.toFixed(1)),
      missingSkills,
      missingEquipment,
    },
    recommendationReason,
  };
}

export function evaluateAllCandidatesForJob(
  job: Job,
  electricians: Electrician[],
  weights: ScoringWeights
): ScheduleRecommendationResult {
  const candidateEvaluations: ElectricianScoreBreakdown[] = electricians.map(
    (tech) => evaluateElectricianForJob(tech, job, weights)
  );

  const feasibleCandidates = candidateEvaluations
    .filter((c) => c.isFeasible)
    .sort((a, b) => b.overallScore - a.overallScore);

  const infeasibleCandidates = candidateEvaluations
    .filter((c) => !c.isFeasible)
    .sort((a, b) => b.overallScore - a.overallScore);

  const recommendedElectrician = feasibleCandidates[0] || null;
  const alternatives = feasibleCandidates.slice(1, 5);

  const infeasibleReasonsSummary = Array.from(
    new Set(infeasibleCandidates.flatMap((c) => c.infeasibilityReasons))
  );

  return {
    jobId: job.id,
    recommendedElectrician,
    alternatives,
    allCandidatesEvaluated: candidateEvaluations.length,
    feasibleCandidatesCount: feasibleCandidates.length,
    infeasibleReasonsSummary,
    weightsUsed: weights,
    timestamp: new Date().toISOString(),
  };
}

export function generateScheduleRecommendations(
  jobId: string,
  customWeights?: Partial<ScoringWeights>
): ScheduleRecommendationResult {
  const job = mockStore.getJobById(jobId);
  const electricians = mockStore.getElectricians();
  const currentPolicies = mockStore.getPolicies();

  const weights: ScoringWeights = {
    ...currentPolicies.weights,
    ...customWeights,
  };

  if (!job) {
    return {
      jobId,
      recommendedElectrician: null,
      alternatives: [],
      allCandidatesEvaluated: electricians.length,
      feasibleCandidatesCount: 0,
      infeasibleReasonsSummary: ['Job not found'],
      weightsUsed: weights,
      timestamp: new Date().toISOString(),
    };
  }

  return evaluateAllCandidatesForJob(job, electricians, weights);
}

