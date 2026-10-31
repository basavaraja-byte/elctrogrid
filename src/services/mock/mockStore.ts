import {
  User,
  Electrician,
  ServiceRequest,
  Job,
  ApprovalRequest,
  EscalationAlert,
  AuditLogEntry,
  NotificationItem,
  PolicySettings,
  JobStatus,
  DisruptionRecord,
  JobPaymentRecord,
  AssignmentOfferItem,
  OfferStatus,
} from '../../types';

import {
  SEED_USERS,
  SEED_ELECTRICIANS,
  SEED_SERVICE_REQUESTS,
  SEED_JOBS,
  SEED_APPROVALS,
  SEED_ESCALATIONS,
  SEED_DISRUPTIONS,
  SEED_NOTIFICATIONS,
  SEED_AUDIT_LOGS,
  SEED_POLICIES,
  MYSURU_LOCALITIES,
} from '../../data/seedData';
import { evaluateAllCandidatesForJob, calculateDistanceKm } from '../scheduling/engine';

export const DEMO_ACCEPTANCE_TIMEOUT_SECONDS = 60;

export function getTechnicianLocationCoords(tech: Electrician): { lat: number; lng: number } {
  if (tech.currentLocation && typeof tech.currentLocation.lat === 'number' && typeof tech.currentLocation.lng === 'number') {
    return { lat: tech.currentLocation.lat, lng: tech.currentLocation.lng };
  }
  return { lat: 12.3025, lng: 76.6315 }; // Central Mysuru fallback
}

interface StoreData {
  users: User[];
  electricians: Electrician[];
  serviceRequests: ServiceRequest[];
  jobs: Job[];
  approvals: ApprovalRequest[];
  escalations: EscalationAlert[];
  disruptions: DisruptionRecord[];
  notifications: NotificationItem[];
  auditLogs: AuditLogEntry[];
  policies: PolicySettings;
}

const STORAGE_KEY = 'dispatchgrid_store_mysuru_v4';

function isWaterTankProblem(item: { title?: string; description?: string }): boolean {
  const text = `${item.title || ''} ${item.description || ''}`.toLowerCase();
  return (
    (text.includes('water') && text.includes('tank')) ||
    text.includes('watertank') ||
    text.includes('water-tank') ||
    (text.includes('tank') && (text.includes('problem') || text.includes('issue') || text.includes('motor') || text.includes('pump') || text.includes('overflow') || text.includes('leak')))
  );
}

export function calculateTimeBilling(durationMinutes: number) {
  const mins = Math.max(1, durationMinutes);
  const baseInr = 500;
  let additionalBlocks = 0;
  let additionalInr = 0;
  if (mins > 60) {
    additionalBlocks = Math.ceil((mins - 60) / 30);
    additionalInr = additionalBlocks * 100;
  }
  const labourTotalInr = baseInr + additionalInr;
  const hrs = Math.floor(mins / 60);
  const remMins = mins % 60;
  const durationFormatted =
    hrs > 0
      ? `${hrs} hour${hrs !== 1 ? 's' : ''} ${remMins} min${remMins !== 1 ? 's' : ''}`
      : `${mins} minutes`;

  return {
    durationMinutes: mins,
    durationFormatted,
    baseAmountInr: baseInr,
    baseAmountPaise: baseInr * 100,
    additionalBlocks,
    additionalAmountInr: additionalInr,
    additionalAmountPaise: additionalInr * 100,
    labourTotalInr,
    labourTotalPaise: labourTotalInr * 100,
  };
}

class MockStore {
  private data: StoreData;
  private listeners: Set<() => void> = new Set();

  constructor() {
    this.data = this.loadFromStorage();
    this.purgeWaterTankData();
    this.checkExpiredOffers();
    setInterval(() => {
      this.checkExpiredOffers();
    }, 2000);
  }

  private loadFromStorage(): StoreData {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed: StoreData = JSON.parse(stored);
        if (parsed && Array.isArray(parsed.users) && Array.isArray(parsed.electricians)) {
          // Cleanse any water tank problem data as requested
          if (Array.isArray(parsed.serviceRequests)) {
            const removedReqs = parsed.serviceRequests.filter(isWaterTankProblem);
            const removedJobIds = new Set(
              removedReqs.map((r) => r.associatedJobId).filter(Boolean) as string[]
            );
            parsed.serviceRequests = parsed.serviceRequests.filter((r) => !isWaterTankProblem(r));
            if (Array.isArray(parsed.jobs)) {
              parsed.jobs = parsed.jobs.filter(
                (j) => !isWaterTankProblem(j) && !removedJobIds.has(j.id)
              );
            }
          }
          if (Array.isArray(parsed.notifications)) {
            parsed.notifications = parsed.notifications.filter(
              (n) => !n.title.toLowerCase().includes('tank') && !n.message.toLowerCase().includes('tank')
            );
          }

          // Ensure all seed users and electricians are present in users
          const existingEmails = new Set(parsed.users.map((u) => u.email.toLowerCase()));
          for (const su of SEED_USERS) {
            if (!existingEmails.has(su.email.toLowerCase())) {
              parsed.users.push(su);
              existingEmails.add(su.email.toLowerCase());
            }
          }
          for (const elec of SEED_ELECTRICIANS) {
            if (!existingEmails.has(elec.email.toLowerCase())) {
              parsed.users.push({
                id: elec.userId || `usr-${elec.id}`,
                name: elec.name,
                email: elec.email,
                role: 'technician',
                phone: elec.phone,
                avatar: elec.avatar,
                department: 'Mysuru Electrical Field Operations',
                employeeId: elec.employeeId,
                active: true,
                createdAt: '2025-01-20T08:00:00Z',
              });
              existingEmails.add(elec.email.toLowerCase());
            }
          }
          return parsed;
        }
      }
    } catch (e) {
      console.warn('Failed to parse localStorage data, initializing seed data', e);
    }
    return this.getInitialSeed();
  }

  private getInitialSeed(): StoreData {
    return {
      users: [...SEED_USERS],
      electricians: [...SEED_ELECTRICIANS],
      serviceRequests: [...SEED_SERVICE_REQUESTS],
      jobs: [...SEED_JOBS],
      approvals: [...SEED_APPROVALS],
      escalations: [...SEED_ESCALATIONS],
      disruptions: [...SEED_DISRUPTIONS],
      notifications: [...SEED_NOTIFICATIONS],
      auditLogs: [...SEED_AUDIT_LOGS],
      policies: { ...SEED_POLICIES },
    };
  }

  private save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data));
    } catch (e) {
      console.error('Failed to save to localStorage', e);
    }
    this.notify();
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify() {
    this.listeners.forEach((listener) => {
      try {
        listener();
      } catch (err) {
        console.error('Store listener error:', err);
      }
    });
  }

  public resetToDefault() {
    this.data = this.getInitialSeed();
    this.save();
  }

  // --- Audit Log Utility ---
  public logAudit(entry: Omit<AuditLogEntry, 'id' | 'timestamp'>) {
    const newEntry: AuditLogEntry = {
      ...entry,
      id: `AUD-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      timestamp: new Date().toISOString(),
    };
    this.data.auditLogs.unshift(newEntry);
  }

  // --- Notifications Utility ---
  public addNotification(item: Omit<NotificationItem, 'id' | 'timestamp' | 'isRead'>) {
    const newNotification: NotificationItem = {
      ...item,
      id: `NOTIF-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      timestamp: new Date().toISOString(),
      isRead: false,
    };
    this.data.notifications.unshift(newNotification);
  }

  // --- Users ---
  public getUsers(): User[] {
    return [...this.data.users];
  }

  public getUserById(id: string): User | undefined {
    return this.data.users.find((u) => u.id === id);
  }

  public findUserByQuery(query: string): User | undefined {
    const q = (query || '').trim().toLowerCase();
    if (!q) return undefined;

    // 1. Direct email match
    let matched = this.data.users.find((u) => u.email.toLowerCase() === q);
    if (matched) return matched;

    // 2. Direct ID or employee ID match in users
    matched = this.data.users.find(
      (u) =>
        u.id.toLowerCase() === q ||
        (u.employeeId && u.employeeId.toLowerCase() === q)
    );
    if (matched) return matched;

    // 3. Search in electricians by email, id, employeeId, or userId
    const matchedElec = this.data.electricians.find(
      (e) =>
        e.email.toLowerCase() === q ||
        e.id.toLowerCase() === q ||
        e.employeeId.toLowerCase() === q ||
        e.userId.toLowerCase() === q
    );
    if (matchedElec) {
      const existing = this.data.users.find(
        (u) => u.id === matchedElec.userId || u.email.toLowerCase() === matchedElec.email.toLowerCase()
      );
      if (existing) return existing;

      const newUser: User = {
        id: matchedElec.userId || `usr-${matchedElec.id}`,
        name: matchedElec.name,
        email: matchedElec.email,
        role: 'technician',
        phone: matchedElec.phone,
        avatar: matchedElec.avatar,
        department: 'Mysuru Electrical Field Operations',
        employeeId: matchedElec.employeeId,
        active: true,
        createdAt: '2025-01-20T08:00:00Z',
      };
      this.data.users.push(newUser);
      return newUser;
    }

    // 4. Handle number or ordinal queries (e.g. "18", "18th", "elec-18", "technician 18")
    const numMatch = q.match(/\b(\d+)(?:st|nd|rd|th)?\b/);
    if (numMatch) {
      const idx = parseInt(numMatch[1], 10);
      if (idx >= 1 && idx <= this.data.electricians.length) {
        const elec = this.data.electricians[idx - 1];
        if (elec) {
          return this.findUserByQuery(elec.email);
        }
      }
    }

    // 5. Match by name in users or electricians
    matched = this.data.users.find((u) => u.name.toLowerCase().includes(q));
    if (matched) return matched;

    const matchedElecByName = this.data.electricians.find((e) => e.name.toLowerCase().includes(q));
    if (matchedElecByName) {
      return this.findUserByQuery(matchedElecByName.email);
    }

    return undefined;
  }

  public authenticate(identifier: string, password?: string): User {
    if (!password || !password.trim()) {
      throw new Error('Password is required.');
    }

    const user = this.findUserByQuery(identifier);
    if (!user) {
      throw new Error(`No account found matching "${identifier}". Please check your email/badge or register.`);
    }

    // All demo accounts accept "electrogrid123" or legacy "dispatchgrid123"
    const expectedPassword = user.password || 'electrogrid123';
    const cleanPwd = password.trim();
    if (
      cleanPwd !== expectedPassword &&
      cleanPwd !== 'electrogrid123' &&
      cleanPwd !== 'dispatchgrid123'
    ) {
      throw new Error('Invalid password. For demo accounts, use password: electrogrid123 or dispatchgrid123');
    }

    return user;
  }

  public addUser(user: Omit<User, 'id' | 'createdAt'>): User {
    const newUser: User = {
      ...user,
      id: `usr-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    this.data.users.push(newUser);
    this.logAudit({
      userId: 'system',
      userName: 'Administrator',
      userRole: 'management',
      action: 'USER_CREATED',
      entityType: 'user',
      entityId: newUser.id,
      newValue: newUser.name,
      reason: `New user account created with role ${newUser.role}`,
    });
    this.save();
    return newUser;
  }

  public updateUser(id: string, updates: Partial<User>): User | undefined {
    const index = this.data.users.findIndex((u) => u.id === id);
    if (index === -1) return undefined;
    this.data.users[index] = { ...this.data.users[index], ...updates };
    this.save();
    return this.data.users[index];
  }

  // --- Electricians ---
  public getElectricians(): Electrician[] {
    return [...this.data.electricians];
  }

  public getElectricianById(id: string): Electrician | undefined {
    return this.data.electricians.find((e) => e.id === id);
  }

  public getElectricianByUserId(userId: string): Electrician | undefined {
    return this.data.electricians.find((e) => e.userId === userId);
  }

  public updateElectrician(id: string, updates: Partial<Electrician>): Electrician | undefined {
    const index = this.data.electricians.findIndex((e) => e.id === id);
    if (index === -1) return undefined;
    this.data.electricians[index] = { ...this.data.electricians[index], ...updates };
    this.save();
    return this.data.electricians[index];
  }

  public updateElectricianLocation(
    id: string,
    coords: { lat: number; lng: number; isSimulated: boolean }
  ): Electrician | undefined {
    const tech = this.getElectricianById(id);
    if (!tech) return undefined;
    tech.currentLocation = {
      ...coords,
      lastUpdated: new Date().toISOString(),
    };
    this.save();
    return tech;
  }

  // --- Service Requests ---
  public getServiceRequests(): ServiceRequest[] {
    return [...this.data.serviceRequests];
  }

  public getServiceRequestById(id: string): ServiceRequest | undefined {
    return this.data.serviceRequests.find((r) => r.id === id);
  }

  public purgeWaterTankData(): number {
    const beforeReqCount = this.data.serviceRequests.length;
    const removedReqs = this.data.serviceRequests.filter(isWaterTankProblem);
    const removedJobIds = new Set(
      removedReqs.map((r) => r.associatedJobId).filter(Boolean) as string[]
    );

    this.data.serviceRequests = this.data.serviceRequests.filter((r) => !isWaterTankProblem(r));
    this.data.jobs = this.data.jobs.filter(
      (j) => !isWaterTankProblem(j) && !removedJobIds.has(j.id)
    );
    this.data.notifications = this.data.notifications.filter(
      (n) => !n.title.toLowerCase().includes('tank') && !n.message.toLowerCase().includes('tank')
    );

    // Also sanitize any older storage keys if present in browser
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        ['dispatchgrid_store_mysuru_v4', 'dispatchgrid_store_mysuru_v3', 'dispatchgrid_store_mysuru_v2', 'dispatchgrid_store_mysuru'].forEach((k) => {
          const raw = window.localStorage.getItem(k);
          if (raw && (raw.toLowerCase().includes('tank') || raw.toLowerCase().includes('water'))) {
            try {
              const d = JSON.parse(raw);
              if (d && Array.isArray(d.serviceRequests)) {
                d.serviceRequests = d.serviceRequests.filter((r: any) => !isWaterTankProblem(r));
              }
              if (d && Array.isArray(d.jobs)) {
                d.jobs = d.jobs.filter((j: any) => !isWaterTankProblem(j));
              }
              window.localStorage.setItem(k, JSON.stringify(d));
            } catch {
              // ignore
            }
          }
        });
      }
    } catch {
      // ignore
    }

    const removedCount = beforeReqCount - this.data.serviceRequests.length;
    if (removedCount > 0) {
      this.save();
    }
    return removedCount;
  }

  public deleteServiceRequest(id: string): boolean {
    const req = this.getServiceRequestById(id);
    if (!req) return false;

    this.data.serviceRequests = this.data.serviceRequests.filter((r) => r.id !== id);
    if (req.associatedJobId) {
      this.data.jobs = this.data.jobs.filter((j) => j.id !== req.associatedJobId);
    } else {
      this.data.jobs = this.data.jobs.filter((j) => j.requestId !== id);
    }
    this.data.notifications = this.data.notifications.filter(
      (n) => !n.message.includes(id) && (!req.associatedJobId || !n.message.includes(req.associatedJobId))
    );
    this.save();
    return true;
  }

  public deleteJob(id: string): boolean {
    const job = this.getJobById(id);
    if (!job) return false;

    this.data.jobs = this.data.jobs.filter((j) => j.id !== id);
    if (job.requestId) {
      this.data.serviceRequests = this.data.serviceRequests.filter((r) => r.id !== job.requestId);
    }
    this.data.notifications = this.data.notifications.filter((n) => !n.message.includes(id));
    this.save();
    return true;
  }

  public createServiceRequest(
    data: Omit<ServiceRequest, 'id' | 'status' | 'submittedAt'>,
    currentUser: User
  ): ServiceRequest {
    const newId = `REQ-2026-${(1000 + this.data.serviceRequests.length + 1).toString()}`;
    const jobId = `JOB-2026-${(4000 + this.data.jobs.length + 1).toString()}`;

    // Determine required skills & equipment based on category
    const requiredSkills: string[] = [];
    if (data.category === 'power_outage') requiredSkills.push('High Voltage Systems', 'Panel & Breaker Upgrades');
    else if (data.category === 'equipment_failure') requiredSkills.push('Emergency Generators', 'Industrial Wiring');
    else if (data.category === 'wiring_fault') requiredSkills.push('Cable Fault Diagnostics', 'Thermal Imaging Inspection');
    else if (data.category === 'panel_breaker') requiredSkills.push('Panel & Breaker Upgrades');
    else requiredSkills.push('Residential Wiring', 'Commercial Lighting');

    const requiredEquipment: string[] = [];
    if (data.priority === 'emergency') requiredEquipment.push('Insulated Tool Set (1000V)');
    if (data.category === 'equipment_failure') requiredEquipment.push('Industrial Generator Diagnostic Kit');
    if (data.category === 'wiring_fault') requiredEquipment.push('Digital Cable Fault Locator');

    const newJob: Job = {
      id: jobId,
      requestId: newId,
      title: data.title,
      description: data.description,
      category: data.category,
      priority: data.priority,
      status: 'awaiting_approval',
      location: data.location,
      customerId: data.customerId,
      customerName: data.customerName,
      customerPhone: data.customerPhone,
      customerEmail: data.customerEmail,
      attachments: data.attachments || [],
      additionalInstructions: data.additionalInstructions || '',
      estimatedDurationHours: 2.0,
      requiredSkills,
      requiredEquipment,
      serviceDeadline: new Date(Date.now() + (data.priority === 'emergency' ? 7200000 : 86400000)).toISOString(),
      preferredTimeWindow: data.preferredTimeWindow,
      assignedElectricianId: null,
      assignedElectricianName: null,
      assignmentHistory: [],
      currentOffer: null,
      timeline: [
        {
          status: 'submitted',
          timestamp: new Date().toISOString(),
          updatedBy: data.customerName,
          role: 'customer',
          notes: 'Customer submitted complaint in Mysuru',
        },
        {
          status: 'validated',
          timestamp: new Date().toISOString(),
          updatedBy: 'Automated Assessment Engine',
          role: 'supervisor',
          notes: 'Automated intake validated electrical safety requirements',
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const newRequest: ServiceRequest = {
      ...data,
      id: newId,
      status: 'awaiting_approval',
      submittedAt: new Date().toISOString(),
      validatedAt: new Date().toISOString(),
      associatedJobId: jobId,
    };

    this.data.jobs.unshift(newJob);
    this.data.serviceRequests.unshift(newRequest);

    this.logAudit({
      userId: currentUser.id,
      userName: currentUser.name,
      userRole: currentUser.role,
      action: 'REQUEST_SUBMITTED_AND_AUTOMATED',
      entityType: 'service_request',
      entityId: newId,
      newValue: newRequest.title,
      reason: `Customer submitted new electrical complaint in ${data.location.address}. Automated 1-by-1 assignment initiated for ticket ${jobId}.`,
    });

    // Feature 1: Intelligent one-by-one automatic electrician assignment with 60-second acceptance timeout
    this.startAutomaticAssignment(newJob.id);

    this.save();
    return newRequest;
  }

  public validateRequest(
    requestId: string,
    notes: string,
    dispatcherUser: User
  ): { request: ServiceRequest; job: Job } | null {
    const request = this.getServiceRequestById(requestId);
    if (!request) return null;

    request.status = 'validated';
    request.validatedAt = new Date().toISOString();
    request.validationNotes = notes;

    // Create Operational Job Ticket
    const jobId = `JOB-2026-${(4000 + this.data.jobs.length + 1).toString()}`;
    request.associatedJobId = jobId;

    // Determine required skills & equipment
    const requiredSkills: string[] = [];
    if (request.category === 'power_outage') requiredSkills.push('High Voltage Systems', 'Panel & Breaker Upgrades');
    else if (request.category === 'equipment_failure') requiredSkills.push('Emergency Generators', 'Industrial Wiring');
    else if (request.category === 'wiring_fault') requiredSkills.push('Cable Fault Diagnostics', 'Thermal Imaging Inspection');
    else if (request.category === 'panel_breaker') requiredSkills.push('Panel & Breaker Upgrades');
    else requiredSkills.push('Residential Wiring', 'Commercial Lighting');

    const requiredEquipment: string[] = [];
    if (request.priority === 'emergency') requiredEquipment.push('Insulated Tool Set (1000V)');
    if (request.category === 'equipment_failure') requiredEquipment.push('Industrial Generator Diagnostic Kit');
    if (request.category === 'wiring_fault') requiredEquipment.push('Digital Cable Fault Locator');

    const newJob: Job = {
      id: jobId,
      requestId: request.id,
      title: request.title,
      description: request.description,
      category: request.category,
      priority: request.priority,
      status: 'validated',
      location: request.location,
      customerId: request.customerId,
      customerName: request.customerName,
      customerPhone: request.customerPhone,
      estimatedDurationHours: 2.0,
      requiredSkills,
      requiredEquipment,
      serviceDeadline: new Date(Date.now() + (request.priority === 'emergency' ? 7200000 : 86400000)).toISOString(),
      preferredTimeWindow: request.preferredTimeWindow,
      assignedElectricianId: null,
      assignedElectricianName: null,
      timeline: [
        {
          status: 'submitted',
          timestamp: request.submittedAt,
          updatedBy: request.customerName,
          role: 'customer',
          notes: 'Customer submitted complaint',
        },
        {
          status: 'validated',
          timestamp: new Date().toISOString(),
          updatedBy: dispatcherUser.name,
          role: 'dispatcher',
          notes: notes || 'Complaint validated and converted into active job',
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    this.data.jobs.unshift(newJob);

    this.logAudit({
      userId: dispatcherUser.id,
      userName: dispatcherUser.name,
      userRole: dispatcherUser.role,
      action: 'REQUEST_VALIDATED_JOB_CREATED',
      entityType: 'job',
      entityId: jobId,
      previousValue: 'submitted',
      newValue: 'validated',
      reason: notes || 'Request converted into operational job ticket',
    });

    this.addNotification({
      targetRole: 'customer',
      targetUserId: request.customerId,
      title: 'Service Request Validated',
      message: `Your request ${request.id} has been validated. Operational ticket ${jobId} is ready for scheduling.`,
      type: 'success',
      linkUrl: `/customer/requests`,
    });

    this.save();
    return { request, job: newJob };
  }

  public rejectRequest(
    requestId: string,
    reason: string,
    dispatcherUser: User
  ): ServiceRequest | null {
    const request = this.getServiceRequestById(requestId);
    if (!request) return null;

    request.status = 'cancelled';
    request.rejectionReason = reason;

    this.logAudit({
      userId: dispatcherUser.id,
      userName: dispatcherUser.name,
      userRole: dispatcherUser.role,
      action: 'REQUEST_REJECTED',
      entityType: 'service_request',
      entityId: requestId,
      previousValue: 'submitted',
      newValue: 'cancelled',
      reason: reason,
    });

    this.addNotification({
      targetRole: 'customer',
      targetUserId: request.customerId,
      title: 'Service Request Rejected',
      message: `Your request ${request.id} could not be scheduled: ${reason}`,
      type: 'alert',
      linkUrl: `/customer/requests`,
    });

    this.save();
    return request;
  }

  // --- Jobs ---
  public getJobs(): Job[] {
    this.checkExpiredOffers();
    return [...this.data.jobs];
  }

  public getJobById(id: string): Job | undefined {
    this.checkExpiredOffers();
    return this.data.jobs.find((j) => j.id === id);
  }

  public updateJob(id: string, updates: Partial<Job>): Job | undefined {
    const index = this.data.jobs.findIndex((j) => j.id === id);
    if (index === -1) return undefined;
    this.data.jobs[index] = {
      ...this.data.jobs[index],
      ...updates,
      updatedAt: new Date().toISOString(),
    };
    this.save();
    return this.data.jobs[index];
  }

  // =========================================================================
  // FEATURE 1: 1-BY-1 AUTOMATIC ELECTRICIAN ASSIGNMENT (60s TIMEOUT)
  // =========================================================================

  public startAutomaticAssignment(jobId: string): AssignmentOfferItem | null {
    const job = this.data.jobs.find((j) => j.id === jobId);
    if (!job) return null;

    // Guard: If job is already assigned or closed/completed, do nothing
    if (
      job.status === 'assigned' ||
      job.status === 'dispatched' ||
      job.status === 'acknowledged' ||
      job.status === 'en_route' ||
      job.status === 'in_progress' ||
      job.status === 'completed' ||
      job.status === 'closed'
    ) {
      return null;
    }

    // Set of technician IDs that have already declined or timed out on this job
    const priorDeclinedTechIds = new Set(
      (job.assignmentHistory || []).map((o) => o.technicianId)
    );

    // Filter candidate electricians based on availability, account status, and workload
    const eligibleTechs = this.data.electricians.filter((tech) => {
      // 1. Account status must be active (or undefined which defaults to active)
      if (tech.accountStatus === 'inactive' || tech.accountStatus === 'suspended') return false;
      // 2. Must be in available status
      if (tech.status !== 'available') return false;
      // 3. Must not be currently handling another job
      if (tech.currentJobId) return false;
      // 4. Must not have already received an offer for this complaint
      if (priorDeclinedTechIds.has(tech.id)) return false;
      return true;
    });

    if (eligibleTechs.length === 0) {
      // All candidate electricians exhausted!
      job.status = 'awaiting_assignment';
      job.currentOffer = null;
      job.timeline.push({
        status: 'awaiting_assignment',
        timestamp: new Date().toISOString(),
        updatedBy: 'Automated Assignment Engine',
        role: 'supervisor',
        notes: `No eligible electricians available (${priorDeclinedTechIds.size} prior candidate attempts failed/exhausted). Moved to Awaiting Assignment queue for supervisor manual intervention.`,
      });

      if (job.requestId) {
        const req = this.getServiceRequestById(job.requestId);
        if (req) req.status = 'awaiting_assignment';
      }

      this.addNotification({
        targetRole: 'supervisor',
        title: 'Assignment Exhausted: Manual Action Needed',
        message: `Complaint ${job.id} (${job.title}) has exhausted all eligible electricians. Please assign manually.`,
        type: 'warning',
        linkUrl: '/supervisor/overview',
      });

      this.save();
      return null;
    }

    // Sort eligible electricians by skill relevance and proximity
    eligibleTechs.sort((a, b) => {
      const aSkillsMatch = (job.requiredSkills || []).filter((s) =>
        a.skills.some((sk) => sk.toLowerCase().includes(s.toLowerCase()))
      ).length;
      const bSkillsMatch = (job.requiredSkills || []).filter((s) =>
        b.skills.some((sk) => sk.toLowerCase().includes(s.toLowerCase()))
      ).length;

      const locA = getTechnicianLocationCoords(a);
      const locB = getTechnicianLocationCoords(b);
      const distA = calculateDistanceKm(job.location.lat, job.location.lng, locA.lat, locA.lng);
      const distB = calculateDistanceKm(job.location.lat, job.location.lng, locB.lat, locB.lng);

      if (aSkillsMatch > 0 && bSkillsMatch === 0) return -1;
      if (bSkillsMatch > 0 && aSkillsMatch === 0) return 1;
      return distA - distB;
    });

    const chosenTech = eligibleTechs[0];
    const techLoc = getTechnicianLocationCoords(chosenTech);
    const distanceKm = calculateDistanceKm(job.location.lat, job.location.lng, techLoc.lat, techLoc.lng);

    const now = new Date();
    const expiresAt = new Date(now.getTime() + DEMO_ACCEPTANCE_TIMEOUT_SECONDS * 1000);
    const offerCode = `OFF-${Math.random().toString(36).substr(2, 6).toUpperCase()}`;

    const newOffer: AssignmentOfferItem = {
      offerId: offerCode,
      jobId: job.id,
      jobTitle: job.title,
      category: job.category,
      priority: job.priority,
      customerName: job.customerName,
      customerPhone: job.customerPhone,
      customerAddress: job.location.address,
      customerLocation: job.location,
      description: job.description,
      attachments: job.attachments,
      additionalInstructions: job.additionalInstructions,
      technicianId: chosenTech.id,
      technicianName: chosenTech.name,
      status: 'offered',
      offeredAt: now.toISOString(),
      expiresAt: expiresAt.toISOString(),
      attemptNumber: (job.assignmentHistory?.length || 0) + 1,
      estimatedDistanceKm: distanceKm,
    };

    job.currentOffer = newOffer;
    if (!job.assignmentHistory) job.assignmentHistory = [];
    job.assignmentHistory.push(newOffer);
    job.status = 'awaiting_approval';

    if (job.requestId) {
      const req = this.getServiceRequestById(job.requestId);
      if (req) req.status = 'awaiting_approval';
    }

    job.timeline.push({
      status: 'awaiting_approval',
      timestamp: now.toISOString(),
      updatedBy: 'Automated Assignment Engine',
      role: 'supervisor',
      notes: `Offer #${newOffer.attemptNumber} dispatched to nearest available electrician ${chosenTech.name} (~${distanceKm.toFixed(1)} km). 60s acceptance countdown active.`,
    });

    // Notify Technician
    this.addNotification({
      targetRole: 'technician',
      targetUserId: chosenTech.userId,
      title: 'Incoming Job Offer (60s to Accept)',
      message: `New electrical complaint ${job.id}: ${job.title} at ${job.location.address} (~${distanceKm.toFixed(1)} km). Click to view details and accept.`,
      type: 'warning',
      linkUrl: '/technician/jobs',
    });

    // Notify Customer
    this.addNotification({
      targetRole: 'customer',
      targetUserId: job.customerId,
      title: 'Finding Nearest Electrician',
      message: `Your complaint is being offered to ${chosenTech.name} (~${distanceKm.toFixed(1)} km away). Awaiting acceptance...`,
      type: 'info',
      linkUrl: '/customer/requests',
    });

    this.save();
    return newOffer;
  }

  public acceptAssignmentOffer(jobId: string, electricianId: string, actorUser: User): Job | null {
    const job = this.data.jobs.find((j) => j.id === jobId);
    if (!job) return null;

    const offer = job.currentOffer;
    if (!offer || offer.technicianId !== electricianId) {
      throw new Error('No active assignment offer found for this technician on this job.');
    }

    // Check server timestamp
    const nowMs = Date.now();
    const expiresMs = new Date(offer.expiresAt).getTime();
    if (nowMs > expiresMs || offer.status !== 'offered') {
      offer.status = 'timed_out';
      offer.respondedAt = new Date().toISOString();
      offer.responseReason = '60-second acceptance timeout expired';
      job.currentOffer = null;
      this.startAutomaticAssignment(job.id);
      throw new Error('This offer has expired after 60 seconds. A new technician is being contacted.');
    }

    const tech = this.getElectricianById(electricianId);
    if (!tech) return null;

    offer.status = 'accepted';
    offer.respondedAt = new Date().toISOString();

    job.assignedElectricianId = tech.id;
    job.assignedElectricianName = tech.name;
    job.status = 'assigned';
    job.dispatchType = 'automatic';
    job.scheduledStartTime = '10:00 AM IST';
    job.scheduledEndTime = '12:00 PM IST';
    job.currentOffer = null;

    tech.status = 'busy';
    tech.currentJobId = job.id;
    tech.currentWorkload = Number((tech.currentWorkload + (job.estimatedDurationHours || 2.0)).toFixed(1));
    tech.jobsCompletedTotal = tech.jobsCompletedTotal || 0;

    if (!tech.assignedJobHistory) tech.assignedJobHistory = [];
    if (!tech.assignedJobHistory.includes(job.id)) {
      tech.assignedJobHistory.push(job.id);
    }

    if (job.requestId) {
      const req = this.getServiceRequestById(job.requestId);
      if (req) req.status = 'assigned';
    }

    job.timeline.push({
      status: 'assigned',
      timestamp: new Date().toISOString(),
      updatedBy: actorUser.name,
      role: 'technician',
      notes: `Offer accepted by ${tech.name} within 60-second window. Job successfully assigned.`,
    });

    this.addNotification({
      targetRole: 'customer',
      targetUserId: job.customerId,
      title: 'Electrician Assigned & Confirmed!',
      message: `${tech.name} accepted your complaint ${job.id} and is preparing to attend your location.`,
      type: 'success',
      linkUrl: '/customer/requests',
    });

    this.addNotification({
      targetRole: 'supervisor',
      title: 'Job Assignment Accepted',
      message: `Job ${job.id} accepted by ${tech.name} (Offer #${offer.attemptNumber}).`,
      type: 'success',
      linkUrl: '/supervisor/overview',
    });

    this.logAudit({
      userId: actorUser.id,
      userName: actorUser.name,
      userRole: actorUser.role,
      action: 'OFFER_ACCEPTED',
      entityType: 'job',
      entityId: job.id,
      newValue: tech.name,
      reason: `Electrician accepted assignment offer within 60s deadline.`,
    });

    this.save();
    return job;
  }

  public rejectAssignmentOffer(jobId: string, electricianId: string, reason: string, actorUser: User): Job | null {
    const job = this.data.jobs.find((j) => j.id === jobId);
    if (!job) return null;

    const offer = job.currentOffer;
    if (offer && offer.technicianId === electricianId) {
      offer.status = 'rejected';
      offer.respondedAt = new Date().toISOString();
      offer.responseReason = reason || 'Technician declined request';
      job.currentOffer = null;

      job.timeline.push({
        status: 'awaiting_approval',
        timestamp: new Date().toISOString(),
        updatedBy: actorUser.name,
        role: 'technician',
        notes: `Offer #${offer.attemptNumber} rejected by ${offer.technicianName} ("${offer.responseReason}"). Searching for next nearest electrician...`,
      });

      this.logAudit({
        userId: actorUser.id,
        userName: actorUser.name,
        userRole: actorUser.role,
        action: 'OFFER_REJECTED',
        entityType: 'job',
        entityId: job.id,
        reason: `Electrician ${offer.technicianName} rejected offer: ${offer.responseReason}. Sequential retry initiated.`,
      });

      // Automatically offer to next nearest eligible electrician!
      this.startAutomaticAssignment(job.id);
    }

    this.save();
    return job;
  }

  public checkExpiredOffers(): void {
    const nowMs = Date.now();
    let hasChanges = false;

    for (const job of this.data.jobs) {
      if (job.currentOffer && job.currentOffer.status === 'offered') {
        const expiresMs = new Date(job.currentOffer.expiresAt).getTime();
        if (nowMs > expiresMs) {
          job.currentOffer.status = 'timed_out';
          job.currentOffer.respondedAt = new Date().toISOString();
          job.currentOffer.responseReason = '60-second acceptance timeout expired';
          const expiredTechName = job.currentOffer.technicianName;
          const attemptNum = job.currentOffer.attemptNumber;
          job.currentOffer = null;

          job.timeline.push({
            status: 'awaiting_approval',
            timestamp: new Date().toISOString(),
            updatedBy: 'Automated Assignment Engine',
            role: 'supervisor',
            notes: `Offer #${attemptNum} to ${expiredTechName} expired after 60s without response. Reassigning to next nearest electrician...`,
          });

          hasChanges = true;
          this.startAutomaticAssignment(job.id);
        }
      }
    }

    if (hasChanges) {
      this.save();
    }
  }

  // =========================================================================
  // FEATURE 3: SUPERVISOR ELECTRICIAN MANAGEMENT & HIRING
  // =========================================================================

  public addElectrician(
    data: {
      name: string;
      email: string;
      phone: string;
      registeredAddress: string;
      skills: string[];
      certifications?: string[];
      experienceYears?: number;
      emergencyContact?: string;
      shift?: string;
    },
    supervisorUser: User
  ): { electrician: Electrician; tempPassword: string } {
    const techCount = this.data.electricians.length;
    const employeeId = `MYS-TECH-${100 + techCount + 1}`;
    const newId = `elec-${Date.now()}`;
    const newUserId = `usr-tech-${Date.now()}`;
    const tempPassword = `ElectroTech@${Math.floor(1000 + Math.random() * 9000)}!`;

    const locMatch = MYSURU_LOCALITIES.find((l) =>
      data.registeredAddress.toLowerCase().includes(l.name.toLowerCase())
    ) || MYSURU_LOCALITIES[techCount % MYSURU_LOCALITIES.length];

    const newElectrician: Electrician = {
      id: newId,
      userId: newUserId,
      name: data.name,
      employeeId,
      phone: data.phone,
      email: data.email,
      avatar: `https://images.unsplash.com/photo-1544717305-2782549b5136?w=150`,
      skills: data.skills.length > 0 ? data.skills : ['Residential Wiring', 'Commercial Lighting'],
      certifications: data.certifications && data.certifications.length > 0
        ? data.certifications
        : ['Certified Electrical Safety Inspector', 'CHESCOM Certified Wireman'],
      equipment: ['Insulated Tool Set (1000V)', 'Digital Multimeter', 'Arc Flash Gloves'],
      shift: (data.shift as any) || 'morning',
      shiftHours: { start: '08:00', end: '16:30' },
      isAvailable: true,
      status: 'available',
      accountStatus: 'active',
      registeredAddress: data.registeredAddress,
      experienceYears: data.experienceYears || 3,
      emergencyContact: data.emergencyContact || '+91 98450 00000',
      isTemporaryPassword: true,
      temporaryPasswordPlain: tempPassword,
      currentJobId: null,
      currentWorkload: 0,
      maxDailyHours: 8.5,
      currentLocation: {
        lat: locMatch.lat,
        lng: locMatch.lng,
        lastUpdated: new Date().toISOString(),
        isSimulated: true,
      },
      rating: 5.0,
      jobsCompletedTotal: 0,
      assignedJobHistory: [],
    };

    const newUser: User = {
      id: newUserId,
      name: data.name,
      email: data.email,
      role: 'technician',
      phone: data.phone,
      employeeId,
      avatar: newElectrician.avatar,
      active: true,
      createdAt: new Date().toISOString(),
    };

    this.data.electricians.unshift(newElectrician);
    this.data.users.unshift(newUser);

    this.logAudit({
      userId: supervisorUser.id,
      userName: supervisorUser.name,
      userRole: supervisorUser.role,
      action: 'ELECTRICIAN_REGISTERED',
      entityType: 'electrician',
      entityId: newId,
      newValue: data.name,
      reason: `Supervisor registered new electrician ${data.name} (${employeeId}) with skills: ${newElectrician.skills.join(', ')}`,
    });

    this.addNotification({
      targetRole: 'supervisor',
      title: 'New Electrician Hired & Registered',
      message: `${data.name} (${employeeId}) successfully registered and available for automated dispatch.`,
      type: 'success',
      linkUrl: '/supervisor/workforce',
    });

    this.save();
    return { electrician: newElectrician, tempPassword };
  }

  public updateElectricianAccountStatus(
    id: string,
    status: 'active' | 'inactive' | 'suspended',
    supervisorUser: User,
    reason?: string
  ): Electrician | null {
    const tech = this.getElectricianById(id);
    if (!tech) return null;

    const prev = tech.accountStatus || 'active';
    tech.accountStatus = status;

    if (status === 'inactive' || status === 'suspended') {
      tech.isAvailable = false;
      tech.status = 'off_duty';
    } else if (status === 'active' && !tech.currentJobId) {
      tech.isAvailable = true;
      tech.status = 'available';
    }

    const u = this.data.users.find((user) => user.id === tech.userId);
    if (u) {
      u.active = status === 'active';
    }

    this.logAudit({
      userId: supervisorUser.id,
      userName: supervisorUser.name,
      userRole: supervisorUser.role,
      action: 'ELECTRICIAN_STATUS_CHANGED',
      entityType: 'electrician',
      entityId: id,
      previousValue: prev,
      newValue: status,
      reason: reason || `Supervisor updated electrician status to ${status}`,
    });

    this.save();
    return tech;
  }

  public resetElectricianPassword(id: string, supervisorUser: User): string {
    const tech = this.getElectricianById(id);
    if (!tech) throw new Error('Electrician not found');

    const newTempPassword = `ElectroTech@${Math.floor(1000 + Math.random() * 9000)}!`;
    tech.isTemporaryPassword = true;
    tech.temporaryPasswordPlain = newTempPassword;

    this.logAudit({
      userId: supervisorUser.id,
      userName: supervisorUser.name,
      userRole: supervisorUser.role,
      action: 'PASSWORD_RESET_GENERATED',
      entityType: 'electrician',
      entityId: id,
      reason: `Supervisor generated a new temporary password for ${tech.name}`,
    });

    this.save();
    return newTempPassword;
  }

  public updateElectricianProfile(
    id: string,
    updates: Partial<Electrician>,
    supervisorUser: User
  ): Electrician | null {
    const tech = this.getElectricianById(id);
    if (!tech) return null;

    Object.assign(tech, updates);

    const u = this.data.users.find((user) => user.id === tech.userId);
    if (u) {
      if (updates.name) u.name = updates.name;
      if (updates.phone) u.phone = updates.phone;
      if (updates.email) u.email = updates.email;
    }

    this.logAudit({
      userId: supervisorUser.id,
      userName: supervisorUser.name,
      userRole: supervisorUser.role,
      action: 'ELECTRICIAN_PROFILE_UPDATED',
      entityType: 'electrician',
      entityId: id,
      reason: `Supervisor updated profile details for ${tech.name}`,
    });

    this.save();
    return tech;
  }

  public assignAndDispatchJob(
    jobId: string,
    electricianId: string,
    scheduledStartTime: string,
    scheduledEndTime: string,
    dispatchType: 'automatic' | 'manual' | 'override',
    actorUser: User
  ): Job | null {
    const job = this.getJobById(jobId);
    const tech = this.getElectricianById(electricianId);
    if (!job || !tech) return null;

    const previousTechName = job.assignedElectricianName || 'Unassigned';
    job.assignedElectricianId = tech.id;
    job.assignedElectricianName = tech.name;
    job.scheduledStartTime = scheduledStartTime;
    job.scheduledEndTime = scheduledEndTime;
    job.status = 'dispatched';
    job.dispatchType = dispatchType;
    job.updatedAt = new Date().toISOString();

    job.timeline.push({
      status: 'dispatched',
      timestamp: new Date().toISOString(),
      updatedBy: actorUser.name,
      role: actorUser.role,
      notes: `Dispatched to ${tech.name} (${dispatchType} dispatch). Schedule: ${scheduledStartTime} - ${scheduledEndTime}`,
    });

    // Update technician workload
    tech.currentWorkload = Number((tech.currentWorkload + job.estimatedDurationHours).toFixed(1));
    tech.status = 'busy';
    tech.currentJobId = job.id;

    // Also update associated service request if any
    if (job.requestId) {
      const req = this.getServiceRequestById(job.requestId);
      if (req) {
        req.status = 'dispatched';
      }
    }

    this.logAudit({
      userId: actorUser.id,
      userName: actorUser.name,
      userRole: actorUser.role,
      action: 'JOB_DISPATCHED',
      entityType: 'job',
      entityId: job.id,
      previousValue: previousTechName,
      newValue: tech.name,
      reason: `Dispatched via ${dispatchType} schedule engine. Window: ${scheduledStartTime}-${scheduledEndTime}`,
    });

    // Notify technician
    this.addNotification({
      targetRole: 'electrician',
      targetUserId: tech.userId,
      title: 'New Dispatched Job',
      message: `You have been dispatched to ${job.id} (${job.title}). Start: ${scheduledStartTime}`,
      type: 'info',
      linkUrl: `/electrician/jobs`,
    });

    // Notify customer
    this.addNotification({
      targetRole: 'customer',
      targetUserId: job.customerId,
      title: 'Electrician Assigned & Dispatched',
      message: `Electrician ${tech.name} has been scheduled for your job ${job.id} at ${scheduledStartTime}.`,
      type: 'success',
      linkUrl: `/customer/requests`,
    });

    this.save();
    return job;
  }

  public updateJobStatus(
    jobId: string,
    newStatus: JobStatus,
    actorUser: User,
    notes?: string,
    completionData?: Job['completionReport']
  ): Job | null {
    const job = this.getJobById(jobId);
    if (!job) return null;

    const previousStatus = job.status;
    job.status = newStatus;
    job.updatedAt = new Date().toISOString();

    if (completionData) {
      job.completionReport = completionData;
      if (completionData.damagedComponents) {
        job.damagedComponents = completionData.damagedComponents;
      }
    }

    if (newStatus === 'in_progress' && !job.actualStartTime) {
      job.actualStartTime = new Date().toISOString();
    }

    if (newStatus === 'completed' || newStatus === 'closed') {
      if (!job.actualStartTime) {
        // Fallback demo actual start time: 75 minutes prior
        job.actualStartTime = new Date(Date.now() - 75 * 60 * 1000).toISOString();
      }
      if (!job.actualCompletionTime) {
        job.actualCompletionTime = new Date().toISOString();
      }

      const startMs = new Date(job.actualStartTime).getTime();
      const endMs = new Date(job.actualCompletionTime).getTime();
      const diffMins = Math.max(1, Math.ceil((endMs - startMs) / 60000));
      job.actualDurationMinutes = diffMins;

      const billing = calculateTimeBilling(diffMins);

      // Create PENDING payment record if not yet created or still pending
      if (!job.payment || job.payment.status === 'pending') {
        const paymentCode = `PAY-${Math.random().toString(36).substr(2, 6).toUpperCase()}`;
        job.payment = {
          paymentId: paymentCode,
          paymentReference: paymentCode,
          amountPaise: billing.labourTotalPaise,
          amountInr: billing.labourTotalInr,
          currency: 'INR',
          status: 'pending',
          method: 'CASH',
          workStartedAt: job.actualStartTime,
          workCompletedAt: job.actualCompletionTime,
          durationMinutes: billing.durationMinutes,
          durationFormatted: billing.durationFormatted,
          baseAmountInr: billing.baseAmountInr,
          additionalBlocks: billing.additionalBlocks,
          additionalAmountInr: billing.additionalAmountInr,
          labourTotalInr: billing.labourTotalInr,
        };
      }
    }

    job.timeline.push({
      status: newStatus,
      timestamp: new Date().toISOString(),
      updatedBy: actorUser.name,
      role: actorUser.role,
      notes: notes || `Status updated from ${previousStatus} to ${newStatus}`,
    });

    // Synchronize associated service request
    if (job.requestId) {
      const req = this.getServiceRequestById(job.requestId);
      if (req) {
        req.status = newStatus;
      }
    }

    // If completed or closed, update electrician status & completed count
    if (newStatus === 'completed' || newStatus === 'closed') {
      if (job.assignedElectricianId) {
        const tech = this.getElectricianById(job.assignedElectricianId);
        if (tech) {
          tech.status = 'available';
          tech.currentJobId = null;
          tech.jobsCompletedTotal += 1;
          tech.currentWorkload = Math.max(0, Number((tech.currentWorkload - job.estimatedDurationHours).toFixed(1)));
        }
      }

      // Notify customer that job is completed
      this.addNotification({
        targetRole: 'customer',
        targetUserId: job.customerId,
        title: 'Electrical Service Completed',
        message: `Work on ${job.id} has been completed by ${job.assignedElectricianName}. Please review and rate your service.`,
        type: 'success',
        linkUrl: `/customer/requests`,
      });

      // Notify dispatcher & operations
      this.addNotification({
        targetRole: 'operations',
        title: 'Job Completed',
        message: `${job.id} completed by ${job.assignedElectricianName}. Report logged.`,
        type: 'info',
        linkUrl: `/operations/monitoring`,
      });
    }

    this.logAudit({
      userId: actorUser.id,
      userName: actorUser.name,
      userRole: actorUser.role,
      action: 'JOB_STATUS_CHANGE',
      entityType: 'job',
      entityId: job.id,
      previousValue: previousStatus,
      newValue: newStatus,
      reason: notes || `Operational status transition to ${newStatus}`,
    });

    this.save();
    return job;
  }

  public updateJobPayment(
    jobId: string,
    payment: JobPaymentRecord,
    actorUser: User
  ): Job | null {
    const job = this.getJobById(jobId);
    if (!job) return null;

    job.payment = payment;
    job.updatedAt = new Date().toISOString();

    if (payment.status === 'completed') {
      const prevStatus = job.status;
      job.status = 'closed';
      const invoiceNumber = `EG-2026-${Math.floor(100000 + Math.random() * 900000)}`;
      payment.receiptNumber = invoiceNumber;

      // Auto-generate invoice
      job.invoice = {
        id: `inv-${Date.now()}`,
        invoiceNumber,
        paymentId: payment.paymentId,
        jobId: job.id,
        customerName: job.customerName,
        technicianName: job.assignedElectricianName || 'Field Technician',
        serviceDescription: job.description,
        invoiceDate: new Date().toISOString(),
        durationMinutes: payment.durationMinutes || 75,
        durationFormatted: payment.durationFormatted || '1 hour 15 minutes',
        labourAmountInr: payment.baseAmountInr || 500,
        additionalBlocks: payment.additionalBlocks || 1,
        additionalAmountInr: payment.additionalAmountInr || 100,
        partsStatus: 'Price to be confirmed',
        partsAmountInr: null,
        totalPaidInr: payment.amountInr,
        totalPaidPaise: payment.amountPaise,
        paymentMethod: 'UPI',
        paymentStatus: 'PAID',
        paymentReference: payment.paymentReference || payment.paymentId,
        pdfUrl: `/api/v1/payments/invoices/${invoiceNumber}/pdf`,
        damagedComponents: job.damagedComponents,
      };

      job.timeline.push({
        status: 'closed',
        timestamp: new Date().toISOString(),
        updatedBy: actorUser.name,
        role: actorUser.role,
        notes: `Paid ₹${payment.amountInr.toLocaleString('en-IN')} via Razorpay UPI (${payment.paymentId}). Receipt: ${invoiceNumber}. Ticket Closed.`,
      });

      if (job.requestId) {
        const req = this.getServiceRequestById(job.requestId);
        if (req) {
          req.status = 'closed';
        }
      }

      this.addNotification({
        targetRole: 'customer',
        targetUserId: job.customerId,
        title: 'Payment Successful (Razorpay Test Mode)',
        message: `Your payment of ₹${payment.amountInr.toLocaleString('en-IN')} for ${job.id} has been verified and settled. Official receipt ${invoiceNumber} is now available.`,
        type: 'success',
        linkUrl: `/customer/requests`,
      });

      this.addNotification({
        targetRole: 'operations',
        title: 'Customer Payment Confirmed',
        message: `Customer ${actorUser.name} settled ₹${payment.amountInr.toLocaleString('en-IN')} for ${job.id}.`,
        type: 'info',
        linkUrl: `/operations/monitoring`,
      });

      this.logAudit({
        userId: actorUser.id,
        userName: actorUser.name,
        userRole: actorUser.role,
        action: 'PAYMENT_COMPLETED',
        entityType: 'job',
        entityId: job.id,
        previousValue: prevStatus,
        newValue: 'closed',
        reason: `Razorpay payment verified. Payment ID: ${payment.paymentId}, Order ID: ${payment.orderId || 'N/A'}. Receipt: ${invoiceNumber}`,
      });
    }

    this.save();
    return job;
  }

  public confirmCashPayment(jobId: string, actorUser: User): Job | null {
    if (actorUser.role === 'customer') {
      throw new Error('Customers cannot confirm their own cash payments. Only authorized technicians or supervisors can confirm.');
    }

    const job = this.getJobById(jobId);
    if (!job) return null;

    const invoiceNumber = `EG-2026-${Math.floor(100000 + Math.random() * 900000)}`;
    const nowIso = new Date().toISOString();
    const labourInr = job.payment?.labourTotalInr || 600;
    const durationMins = job.payment?.durationMinutes || 75;
    const durationFmt = job.payment?.durationFormatted || '1 hour 15 minutes';

    job.payment = {
      ...(job.payment || {
        paymentId: `PAY-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
        paymentReference: `PAY-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
        amountPaise: labourInr * 100,
        amountInr: labourInr,
        currency: 'INR',
      }),
      status: 'completed',
      method: 'CASH',
      paidAt: nowIso,
      receiptNumber: invoiceNumber,
      confirmedBy: actorUser.name,
      confirmedAt: nowIso,
      isVerified: true,
    };

    job.invoice = {
      id: `inv-${Date.now()}`,
      invoiceNumber,
      paymentId: job.payment.paymentId,
      jobId: job.id,
      customerName: job.customerName,
      technicianName: actorUser.name,
      serviceDescription: job.description,
      invoiceDate: nowIso,
      durationMinutes: durationMins,
      durationFormatted: durationFmt,
      labourAmountInr: job.payment.baseAmountInr || 500,
      additionalBlocks: job.payment.additionalBlocks || 1,
      additionalAmountInr: job.payment.additionalAmountInr || 100,
      partsStatus: 'Price to be confirmed',
      partsAmountInr: null,
      totalPaidInr: labourInr,
      totalPaidPaise: labourInr * 100,
      paymentMethod: 'CASH',
      paymentStatus: 'PAID',
      paymentReference: job.payment.paymentReference || job.payment.paymentId,
      pdfUrl: `/api/v1/payments/invoices/${invoiceNumber}/pdf`,
      damagedComponents: job.damagedComponents,
    };

    job.status = 'closed';
    job.timeline.push({
      status: 'closed',
      timestamp: nowIso,
      updatedBy: actorUser.name,
      role: actorUser.role,
      notes: `Cash payment of ₹${labourInr.toLocaleString('en-IN')} confirmed by ${actorUser.name}. Receipt: ${invoiceNumber}. Ticket closed.`,
    });

    if (job.requestId) {
      const req = this.getServiceRequestById(job.requestId);
      if (req) {
        req.status = 'closed';
      }
    }

    this.addNotification({
      targetRole: 'customer',
      targetUserId: job.customerId,
      title: 'Cash Payment Confirmed & Receipt Ready',
      message: `Your technician ${actorUser.name} confirmed receipt of ₹${labourInr.toLocaleString('en-IN')}. Official receipt ${invoiceNumber} is available for download.`,
      type: 'success',
      linkUrl: `/customer/requests`,
    });

    this.logAudit({
      userId: actorUser.id,
      userName: actorUser.name,
      userRole: actorUser.role,
      action: 'CASH_PAYMENT_CONFIRMED',
      entityType: 'job',
      entityId: job.id,
      newValue: 'closed',
      reason: `Cash payment of ₹${labourInr} authenticated by ${actorUser.name}. Receipt: ${invoiceNumber}`,
    });

    this.save();
    return job;
  }

  public submitCustomerFeedback(jobId: string, rating: number, comments: string, user: User): Job | null {
    const job = this.getJobById(jobId);
    if (!job) return null;

    job.feedback = {
      rating,
      comments,
      submittedAt: new Date().toISOString(),
    };
    job.status = 'customer_confirmed';
    job.updatedAt = new Date().toISOString();

    job.timeline.push({
      status: 'customer_confirmed',
      timestamp: new Date().toISOString(),
      updatedBy: user.name,
      role: 'customer',
      notes: `Customer submitted feedback: ${rating} Stars. "${comments}"`,
    });

    if (job.requestId) {
      const req = this.getServiceRequestById(job.requestId);
      if (req) req.status = 'customer_confirmed';
    }

    this.logAudit({
      userId: user.id,
      userName: user.name,
      userRole: 'customer',
      action: 'CUSTOMER_FEEDBACK_SUBMITTED',
      entityType: 'job',
      entityId: job.id,
      newValue: `${rating} Stars`,
      reason: comments,
    });

    this.save();
    return job;
  }

  // --- Approvals ---
  public getApprovals(): ApprovalRequest[] {
    return [...this.data.approvals];
  }

  public createApprovalRequest(
    data: Omit<ApprovalRequest, 'id' | 'currentStatus' | 'submittedAt'>,
    user: User
  ): ApprovalRequest {
    const newApproval: ApprovalRequest = {
      ...data,
      id: `APP-2026-${(this.data.approvals.length + 1).toString().padStart(3, '0')}`,
      currentStatus: 'pending',
      submittedAt: new Date().toISOString(),
    };
    this.data.approvals.unshift(newApproval);

    this.logAudit({
      userId: user.id,
      userName: user.name,
      userRole: user.role,
      action: 'APPROVAL_REQUESTED',
      entityType: 'approval',
      entityId: newApproval.id,
      newValue: newApproval.title,
      reason: newApproval.details,
    });

    this.addNotification({
      targetRole: 'management',
      title: 'Action Required: Approval Request',
      message: `${newApproval.id}: ${newApproval.title}`,
      type: 'alert',
      linkUrl: `/management/approvals`,
    });

    this.save();
    return newApproval;
  }

  public resolveApproval(
    id: string,
    decision: 'approved' | 'rejected' | 'clarification_requested',
    notes: string,
    user: User
  ): ApprovalRequest | null {
    const item = this.data.approvals.find((a) => a.id === id);
    if (!item) return null;

    const prev = item.currentStatus;
    item.currentStatus = decision;
    item.reviewedBy = user.name;
    item.reviewedAt = new Date().toISOString();
    item.reviewNotes = notes;

    this.logAudit({
      userId: user.id,
      userName: user.name,
      userRole: user.role,
      action: `APPROVAL_${decision.toUpperCase()}`,
      entityType: 'approval',
      entityId: item.id,
      previousValue: prev,
      newValue: decision,
      reason: notes,
    });

    // Notify requester
    this.addNotification({
      targetRole: item.requesterRole,
      title: `Approval Request ${decision.toUpperCase()}`,
      message: `Management ${decision} request ${item.id}: ${notes}`,
      type: decision === 'approved' ? 'success' : 'alert',
    });

    this.save();
    return item;
  }

  // --- Escalations ---
  public getEscalations(): EscalationAlert[] {
    return [...this.data.escalations];
  }

  public getDisruptions(): DisruptionRecord[] {
    return [...(this.data.disruptions || [])];
  }

  public addDisruption(disruption: DisruptionRecord): DisruptionRecord {
    if (!this.data.disruptions) {
      this.data.disruptions = [];
    }
    this.data.disruptions.unshift(disruption);
    this.save();
    return disruption;
  }

  public updateDisruption(disruption: DisruptionRecord): DisruptionRecord {
    if (!this.data.disruptions) {
      this.data.disruptions = [];
    }
    const idx = this.data.disruptions.findIndex((d) => d.id === disruption.id);
    if (idx !== -1) {
      this.data.disruptions[idx] = disruption;
    } else {
      this.data.disruptions.unshift(disruption);
    }
    this.save();
    return disruption;
  }

  public createEscalation(
    data: Omit<EscalationAlert, 'id' | 'status' | 'createdAt'>,
    user: User
  ): EscalationAlert {
    const newEsc: EscalationAlert = {
      ...data,
      id: `ESC-2026-${(100 + this.data.escalations.length + 1).toString()}`,
      status: 'open',
      createdAt: new Date().toISOString(),
    };
    this.data.escalations.unshift(newEsc);

    this.logAudit({
      userId: user.id,
      userName: user.name,
      userRole: user.role,
      action: 'ESCALATION_RAISED',
      entityType: 'job',
      entityId: newEsc.jobId || newEsc.id,
      newValue: newEsc.title,
      reason: newEsc.description,
    });

    this.addNotification({
      targetRole: newEsc.assignedToRole,
      title: `New Escalation: ${newEsc.title}`,
      message: newEsc.description,
      type: 'alert',
      linkUrl: newEsc.assignedToRole === 'management' ? '/management/approvals' : '/operations/alerts',
    });

    this.save();
    return newEsc;
  }

  // --- Notifications ---
  public getNotifications(userRole?: string, userId?: string): NotificationItem[] {
    return this.data.notifications.filter((n) => {
      if (n.targetUserId && userId && n.targetUserId === userId) return true;
      if (n.targetRole && userRole) {
        if (n.targetRole === userRole) return true;
        if (userRole === 'supervisor' && (n.targetRole === 'operations' || n.targetRole === 'dispatcher' || n.targetRole === 'management')) return true;
        if (userRole === 'technician' && n.targetRole === 'electrician') return true;
      }
      if (!n.targetRole && !n.targetUserId) return true;
      return false;
    });
  }

  public markNotificationAsRead(id: string) {
    const item = this.data.notifications.find((n) => n.id === id);
    if (item) {
      item.isRead = true;
      this.save();
    }
  }

  public markAllNotificationsAsRead(userRole?: string, userId?: string) {
    this.data.notifications.forEach((n) => {
      if (
        (!n.targetRole && !n.targetUserId) ||
        (n.targetRole && n.targetRole === userRole) ||
        (n.targetUserId && n.targetUserId === userId)
      ) {
        n.isRead = true;
      }
    });
    this.save();
  }

  // --- Audit Logs ---
  public getAuditLogs(): AuditLogEntry[] {
    return [...this.data.auditLogs];
  }

  // --- Policies ---
  public getPolicies(): PolicySettings {
    return { ...this.data.policies };
  }

  public updatePolicies(newPolicies: Partial<PolicySettings>, user: User): PolicySettings {
    this.data.policies = { ...this.data.policies, ...newPolicies };
    this.logAudit({
      userId: user.id,
      userName: user.name,
      userRole: user.role,
      action: 'POLICIES_UPDATED',
      entityType: 'policy',
      entityId: 'SYSTEM_POLICIES',
      newValue: JSON.stringify(newPolicies),
      reason: 'Management modified organization operational thresholds or weights',
    });
    this.save();
    return this.data.policies;
  }
}

export const mockStore = new MockStore();

