export type UserRole =
  | 'customer'
  | 'technician'
  | 'supervisor'
  | 'dispatcher'
  | 'electrician'
  | 'operations'
  | 'management';

export type CustomerCategory = 'individual' | 'commercial';

export type JobPriority = 'low' | 'medium' | 'high' | 'emergency';

export type ProblemCategory =
  | 'residential_wiring'
  | 'power_outage'
  | 'switch_socket'
  | 'panel_breaker'
  | 'short_circuit'
  | 'lighting_fixture'
  | 'fan_motor_repair'
  | 'three_phase_power'
  | 'solar_inverter'
  | 'ev_charging'
  | 'generator_backup'
  | 'transformer_substation'
  | 'preventive_maintenance'
  | 'other_electrical'
  | 'wiring_fault'
  | 'equipment_failure'
  | 'lighting_problem'
  | 'other';

export type JobStatus =
  | 'submitted'
  | 'under_review'
  | 'validated'
  | 'scheduling'
  | 'awaiting_approval'
  | 'assigned'
  | 'dispatched'
  | 'acknowledged'
  | 'en_route'
  | 'in_progress'
  | 'on_hold'
  | 'completed'
  | 'customer_confirmed'
  | 'closed'
  | 'cancelled'
  | 'unassigned';

export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low';

export type ShiftType = 'morning' | 'afternoon' | 'evening' | 'night' | 'flexible';

export interface LocationCoordinates {
  lat: number;
  lng: number;
  address: string;
  city: string;
  postalCode: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone: string;
  password?: string;
  avatar?: string;
  department?: string;
  active: boolean;
  createdAt: string;
  // Specific role metadata
  customerCategory?: CustomerCategory;
  companyName?: string;
  commercialLocations?: LocationCoordinates[];
  employeeId?: string;
}

export interface Electrician {
  id: string;
  userId: string;
  name: string;
  employeeId: string;
  phone: string;
  email: string;
  avatar: string;
  skills: string[]; // e.g., 'High Voltage', 'Solar Panels', 'Industrial Wiring', 'Residential', 'Transformer Diagnostics'
  certifications: string[];
  equipment: string[]; // e.g., 'Thermal Camera', 'Bucket Truck', 'Cable Fault Locator', 'Arc Flash PPE'
  shift: ShiftType;
  shiftHours: { start: string; end: string };
  isAvailable: boolean;
  status: 'available' | 'busy' | 'en_route' | 'on_break' | 'off_duty' | 'leave';
  currentJobId?: string | null;
  currentWorkload: number; // in hours or job count
  maxDailyHours: number;
  currentLocation: {
    lat: number;
    lng: number;
    lastUpdated: string;
    isSimulated: boolean;
  };
  rating: number; // 1-5
  jobsCompletedTotal: number;
}

export type Technician = Electrician;

export interface ServiceRequest {
  id: string; // e.g. "REQ-2026-1042"
  customerId: string;
  customerName: string;
  customerType: CustomerCategory;
  customerPhone: string;
  customerEmail: string;
  title: string;
  description: string;
  category: ProblemCategory;
  priority: JobPriority;
  location: LocationCoordinates;
  preferredDate: string;
  preferredTimeWindow: string; // e.g. "09:00 - 12:00"
  attachments: string[]; // mock file names or data URLs
  additionalInstructions?: string;
  status: JobStatus;
  submittedAt: string;
  validatedAt?: string;
  validationNotes?: string;
  rejectionReason?: string;
  associatedJobId?: string;
}

export interface JobTimelineEvent {
  status: JobStatus;
  timestamp: string;
  updatedBy: string;
  role: UserRole;
  notes?: string;
}

export interface CompletionReport {
  workPerformed: string;
  faultIdentified: string;
  materialsUsed: string[];
  notes: string;
  beforePhotos: string[];
  afterPhotos: string[];
  completionTimestamp: string;
  signedOffByElectrician: string;
}

export interface CustomerFeedback {
  rating: number; // 1 to 5
  comments: string;
  submittedAt: string;
}

export interface JobPaymentRecord {
  paymentId: string;
  orderId?: string;
  amountPaise: number;
  amountInr: number;
  currency: string;
  status: 'pending' | 'completed' | 'failed';
  razorpayPaymentId?: string;
  razorpayOrderId?: string;
  razorpaySignature?: string;
  paidAt?: string;
  method?: string;
  serviceCharge?: number;
  partsCharge?: number;
  taxAmount?: number;
  receiptNumber?: string;
}

export interface Job {
  id: string; // e.g. "JOB-2026-4011"
  requestId: string;
  title: string;
  description: string;
  category: ProblemCategory;
  priority: JobPriority;
  status: JobStatus;
  location: LocationCoordinates;
  customerId: string;
  customerName: string;
  customerPhone: string;

  // Operational specifications
  estimatedDurationHours: number;
  requiredSkills: string[];
  requiredEquipment: string[];
  serviceDeadline: string;
  preferredTimeWindow: string;

  // Assignment
  assignedElectricianId?: string | null;
  assignedElectricianName?: string | null;
  scheduledStartTime?: string;
  scheduledEndTime?: string;
  dispatchType?: 'automatic' | 'manual' | 'override';

  // Derived alerts
  isOverdue?: boolean;
  slaRisk?: 'normal' | 'warning' | 'breached';

  // Lifecycle tracking
  timeline: JobTimelineEvent[];
  completionReport?: CompletionReport;
  feedback?: CustomerFeedback;
  payment?: JobPaymentRecord;

  createdAt: string;
  updatedAt: string;
}

export interface ScoringWeights {
  skillCompatibility: number; // default 25
  availabilityShift: number;  // default 20
  proximityTravel: number;    // default 20
  workloadBalance: number;    // default 15
  deadlineFeasibility: number;// default 10
  equipmentMatch: number;     // default 10
}

export interface ElectricianScoreBreakdown {
  electricianId: string;
  electricianName: string;
  isFeasible: boolean;
  infeasibilityReasons: string[];
  overallScore: number; // 0 - 100
  scores: {
    skillScore: number;
    availabilityScore: number;
    travelScore: number;
    workloadScore: number;
    deadlineScore: number;
    equipmentScore: number;
  };
  metrics: {
    estimatedDistanceKm: number;
    estimatedTravelMinutes: number;
    currentWorkloadHours: number;
    workloadAfterHours: number;
    missingSkills: string[];
    missingEquipment: string[];
  };
  recommendationReason: string;
}

export interface ScheduleRecommendationResult {
  jobId: string;
  recommendedElectrician: ElectricianScoreBreakdown | null;
  alternatives: ElectricianScoreBreakdown[];
  allCandidatesEvaluated: number;
  feasibleCandidatesCount: number;
  infeasibleReasonsSummary: string[];
  weightsUsed: ScoringWeights;
  timestamp: string;
}

export type DisruptionType =
  | 'electrician_unavailable'
  | 'technician_delay'
  | 'emergency_job_injection'
  | 'job_duration_extension'
  | 'equipment_failure'
  | 'customer_cancellation';

export interface DisruptionRecord {
  id: string;
  type: DisruptionType;
  title: string;
  description: string;
  affectedElectricianId?: string;
  affectedJobIds: string[];
  timestamp: string;
  status: 'detected' | 'analyzing' | 'resolved' | 'escalated';
  proposedResolution?: {
    reassignments: {
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
    }[];
    impactSummary: string;
  };
  approvedBy?: string;
  approvedAt?: string;
}

export interface EscalationAlert {
  id: string;
  jobId?: string;
  disruptionId?: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  sourceRole: UserRole;
  raisedBy: string;
  assignedToRole: 'dispatcher' | 'operations' | 'management';
  status: 'open' | 'under_review' | 'resolved' | 'rejected';
  createdAt: string;
  resolutionNotes?: string;
  resolvedAt?: string;
}

export interface ApprovalRequest {
  id: string;
  title: string;
  category: 'high_impact_schedule' | 'major_sla_exception' | 'policy_override' | 'escalated_decision';
  relatedJobId?: string;
  relatedDisruptionId?: string;
  details: string;
  requestedBy: string;
  requesterRole: UserRole;
  currentStatus: 'pending' | 'approved' | 'rejected' | 'clarification_requested';
  impactLevel: 'medium' | 'high' | 'critical';
  submittedAt: string;
  reviewedBy?: string;
  reviewedAt?: string;
  reviewNotes?: string;
}

export interface AuditLogEntry {
  id: string;
  userId: string;
  userName: string;
  userRole: UserRole;
  action: string;
  entityType: 'service_request' | 'job' | 'electrician' | 'schedule' | 'disruption' | 'approval' | 'policy' | 'user';
  entityId: string;
  previousValue?: string;
  newValue?: string;
  reason?: string;
  timestamp: string;
}

export interface NotificationItem {
  id: string;
  targetRole?: UserRole;
  targetUserId?: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'alert';
  linkUrl?: string;
  timestamp: string;
  isRead: boolean;
}

export interface PolicySettings {
  autoDispatchEnabled: boolean;
  autoDispatchMinScoreThreshold: number; // e.g. 75
  emergencyAutoEscalate: boolean;
  maxDailyWorkloadHours: number; // e.g. 9
  slaHighPriorityMinutes: number; // e.g. 120
  slaEmergencyMinutes: number; // e.g. 45
  requireManagementApprovalForReassignmentsCount: number; // e.g. 3 or more jobs reassigned
  weights: ScoringWeights;
}

