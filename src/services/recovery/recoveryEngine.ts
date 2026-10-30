import {
  DisruptionRecord,
  DisruptionType,
  User,
  Job,
} from '../../types';
import { mockStore } from '../mock/mockStore';
import { generateScheduleRecommendations } from '../scheduling/engine';

export interface DisruptionSimulationOptions {
  type: DisruptionType;
  targetElectricianId?: string;
  targetJobId?: string;
  notes?: string;
}

export interface ReassignmentItem {
  jobId: string;
  jobTitle: string;
  previousElectricianId?: string;
  previousElectricianName?: string;
  newElectricianId: string;
  newElectricianName: string;
  originalTime: string;
  newTime: string;
  reason: string;
  requiresApproval: boolean;
}

export function simulateOperationalDisruption(
  options: DisruptionSimulationOptions,
  actorUser: User
): DisruptionRecord {
  const electricians = mockStore.getElectricians();
  const allJobs = mockStore.getJobs();
  const policies = mockStore.getPolicies();

  const disruptionId = `DISR-2026-${Math.floor(10 + Math.random() * 90)}`;
  let title = '';
  let description = options.notes || '';
  let affectedElectricianId = options.targetElectricianId;
  const affectedJobIds: string[] = [];

  // Determine affected jobs based on disruption scenario
  if (options.type === 'electrician_unavailable') {
    const tech = affectedElectricianId
      ? mockStore.getElectricianById(affectedElectricianId)
      : electricians.find((e) => e.status === 'busy') || electricians[0];

    affectedElectricianId = tech?.id;
    title = `Unscheduled Absence: ${tech?.name || 'Technician'} unavailable`;
    if (!description) {
      description = `Technician ${tech?.name} reported sudden mechanical vehicle breakdown. Field assignment halted immediately.`;
    }

    // Mark electrician status to 'off_duty'
    if (tech) {
      mockStore.updateElectrician(tech.id, {
        isAvailable: false,
        status: 'off_duty',
      });
    }

    // Find all future / active jobs assigned to this electrician (preserve completed/closed)
    const techJobs = allJobs.filter(
      (j) =>
        j.assignedElectricianId === tech?.id &&
        j.status !== 'completed' &&
        j.status !== 'closed' &&
        j.status !== 'cancelled'
    );

    techJobs.forEach((j) => affectedJobIds.push(j.id));
  } else if (options.type === 'technician_delay') {
    const tech = (affectedElectricianId
      ? mockStore.getElectricianById(affectedElectricianId)
      : electricians[1]) || electricians[0];

    affectedElectricianId = tech.id;
    title = `Major Transit Delay: ${tech.name} delayed by 90 minutes`;
    description = description || 'Major highway accident gridlock delaying technician ETA by 1.5 hours.';

    const techJobs = allJobs.filter(
      (j) =>
        j.assignedElectricianId === tech.id &&
        (j.status === 'assigned' || j.status === 'dispatched' || j.status === 'en_route')
    );
    techJobs.forEach((j) => affectedJobIds.push(j.id));
  } else if (options.type === 'emergency_job_injection') {
    title = 'Priority Emergency Injected: Substation Arc Flash Danger';
    description = description || 'Urgent 911 dispatch: Critical electrical fire hazard at Municipal Water Pump 4. Reallocation required.';
    const highPriJob = allJobs.find((j) => j.priority === 'emergency' && j.status !== 'completed') || allJobs[0];
    if (highPriJob) {
      affectedJobIds.push(highPriJob.id);
    }
  } else if (options.type === 'equipment_failure') {
    title = 'Critical Tool Failure: High-Voltage PPE / Fault Locator inoperable';
    description = description || 'Cable Fault Locator failed self-test verification. Requires equipment replacement or job swap.';
    const tech = electricians.find((e) => e.equipment.some((eq) => eq.includes('Locator'))) || electricians[0];
    affectedElectricianId = tech.id;
    const techJobs = allJobs.filter(
      (j) => j.assignedElectricianId === tech.id && j.status !== 'completed'
    );
    techJobs.slice(0, 2).forEach((j) => affectedJobIds.push(j.id));
  } else {
    title = `Operational Disruption (${options.type})`;
    description = description || 'Field variance detected requiring automated schedule re-balancing.';
    const sampleJob = allJobs.find((j) => j.status === 'assigned');
    if (sampleJob) affectedJobIds.push(sampleJob.id);
  }

  // Generate intelligent alternative assignments for affected jobs
  const reassignments: ReassignmentItem[] = [];

  for (const jId of affectedJobIds) {
    const job = mockStore.getJobById(jId);
    if (!job) continue;

    // Run scheduler engine
    const recommendation = generateScheduleRecommendations(job.id);
    // Filter out the disrupted electrician
    const candidate =
      recommendation.recommendedElectrician?.electricianId !== affectedElectricianId
        ? recommendation.recommendedElectrician
        : recommendation.alternatives.find(
            (alt) => alt.electricianId !== affectedElectricianId
          );

    if (candidate) {
      const targetTech = mockStore.getElectricianById(candidate.electricianId);
      reassignments.push({
        jobId: job.id,
        jobTitle: job.title,
        previousElectricianId: job.assignedElectricianId || undefined,
        previousElectricianName: job.assignedElectricianName || 'Unassigned',
        newElectricianId: candidate.electricianId,
        newElectricianName: targetTech?.name || candidate.electricianName,
        originalTime: job.scheduledStartTime || '09:00',
        newTime: '10:45',
        reason: `${candidate.recommendationReason} (Score: ${candidate.overallScore}%)`,
        requiresApproval: reassignments.length >= policies.requireManagementApprovalForReassignmentsCount || job.priority === 'emergency',
      });
    }
  }

  const requiresManagementApproval = reassignments.some((r: ReassignmentItem) => r.requiresApproval);
  const impactSummary = `${affectedJobIds.length} job(s) impacted. Proposed ${reassignments.length} automated reassignment(s) with minimal travel shift.`;

  const disruptionRecord: DisruptionRecord = {
    id: disruptionId,
    type: options.type,
    title,
    description,
    affectedElectricianId,
    affectedJobIds,
    timestamp: new Date().toISOString(),
    status: requiresManagementApproval ? 'escalated' : 'analyzing',
    proposedResolution: {
      reassignments,
      impactSummary,
    },
  };

  // Log in Audit Trail
  mockStore.logAudit({
    userId: actorUser.id,
    userName: actorUser.name,
    userRole: actorUser.role,
    action: 'DISRUPTION_DETECTED',
    entityType: 'disruption',
    entityId: disruptionId,
    newValue: title,
    reason: description,
  });

  // Save Disruption to Mock Store
  mockStore.addDisruption(disruptionRecord);

  // Notify Supervisor & Operations
  mockStore.addNotification({
    targetRole: 'supervisor',
    title: `Disruption Detected: ${title}`,
    message: `${impactSummary}. Recovery engine computing autonomous schedule adjustments.`,
    type: 'alert',
    linkUrl: '/supervisor/recovery',
  });

  mockStore.addNotification({
    targetRole: 'dispatcher',
    title: `Disruption Detected: ${title}`,
    message: `${impactSummary}. Review recovery options.`,
    type: 'alert',
    linkUrl: '/supervisor/recovery',
  });

  mockStore.addNotification({
    targetRole: 'operations',
    title: `Field Disruption Alert`,
    message: `${title} - ${affectedJobIds.length} jobs affected.`,
    type: 'warning',
    linkUrl: '/operations/alerts',
  });

  // If management approval required, create formal approval request
  if (requiresManagementApproval) {
    mockStore.createApprovalRequest(
      {
        title: `Schedule Recovery Override: ${title}`,
        category: 'high_impact_schedule',
        relatedDisruptionId: disruptionId,
        details: `${description} | ${impactSummary}`,
        requestedBy: actorUser.name,
        requesterRole: actorUser.role,
        impactLevel: 'critical',
      },
      actorUser
    );
  }

  return disruptionRecord;
}

export function applyDisruptionResolution(
  disruption: DisruptionRecord,
  actorUser: User
): boolean {
  if (!disruption.proposedResolution) return false;

  const { reassignments } = disruption.proposedResolution;

  for (const item of reassignments) {
    const job = mockStore.getJobById(item.jobId);
    if (!job) continue;

    mockStore.assignAndDispatchJob(
      item.jobId,
      item.newElectricianId,
      item.newTime,
      '12:30',
      'override',
      actorUser
    );

    mockStore.logAudit({
      userId: actorUser.id,
      userName: actorUser.name,
      userRole: actorUser.role,
      action: 'RECOVERY_REASSIGNMENT_EXECUTED',
      entityType: 'job',
      entityId: item.jobId,
      previousValue: item.previousElectricianName,
      newValue: item.newElectricianName,
      reason: `Disruption recovery resolution: ${item.reason}`,
    });
  }

  disruption.status = 'resolved';
  mockStore.updateDisruption(disruption);

  mockStore.addNotification({
    targetRole: 'supervisor',
    title: 'Disruption Resolved',
    message: `Recovery schedule implemented for ${disruption.id}. All affected technicians notified.`,
    type: 'success',
    linkUrl: '/supervisor/recovery',
  });

  return true;
}
