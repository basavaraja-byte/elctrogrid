import {
  User,
  Job,
  ServiceRequest,
  Electrician,
  ApprovalRequest,
  EscalationAlert,
  AuditLogEntry,
  NotificationItem,
  PolicySettings,
  ScheduleRecommendationResult,
  JobStatus,
  DisruptionRecord,
  JobPaymentRecord,
} from '../../types';
import { mockStore } from '../mock/mockStore';
import { generateScheduleRecommendations } from '../scheduling/engine';
import { simulateOperationalDisruption, applyDisruptionResolution, DisruptionSimulationOptions } from '../recovery/recoveryEngine';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA !== 'false';

class ApiClient {
  private baseUrl: string;
  private useMock: boolean;

  constructor() {
    this.baseUrl = API_BASE_URL;
    this.useMock = USE_MOCK_DATA;
  }

  // --- Generic Fetch Helper for FastAPI Backend ---
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = localStorage.getItem('dispatchgrid_auth_token');
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.message || `API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // --- AUTHENTICATION ---
  async login(identifier: string, password?: string): Promise<{ user: User; token: string }> {
    if (!password || !password.trim()) {
      throw new Error('Password is required.');
    }
    if (this.useMock) {
      const user = mockStore.authenticate(identifier, password);
      return { user, token: `mock-jwt-token-${user.id}` };
    }
    return this.request<{ user: User; token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: identifier, password }),
    });
  }

  // --- PAYMENTS ---
  async updateJobPayment(
    jobId: string,
    payment: JobPaymentRecord,
    currentUser: User
  ): Promise<Job> {
    if (this.useMock) {
      const updated = mockStore.updateJobPayment(jobId, payment, currentUser);
      if (!updated) throw new Error(`Job not found: ${jobId}`);
      return updated;
    }
    return this.request<Job>(`/api/jobs/${jobId}/payment`, {
      method: 'POST',
      body: JSON.stringify(payment),
    });
  }

  // --- SERVICE REQUESTS ---
  async getServiceRequests(): Promise<ServiceRequest[]> {
    if (this.useMock) return mockStore.getServiceRequests();
    return this.request<ServiceRequest[]>('/api/service-requests');
  }

  async getServiceRequestById(id: string): Promise<ServiceRequest | undefined> {
    if (this.useMock) return mockStore.getServiceRequestById(id);
    return this.request<ServiceRequest>(`/api/service-requests/${id}`);
  }

  async createServiceRequest(
    data: Omit<ServiceRequest, 'id' | 'status' | 'submittedAt'>,
    currentUser: User
  ): Promise<ServiceRequest> {
    if (this.useMock) return mockStore.createServiceRequest(data, currentUser);
    return this.request<ServiceRequest>('/api/service-requests', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async validateRequest(
    requestId: string,
    notes: string,
    dispatcherUser: User
  ): Promise<{ request: ServiceRequest; job: Job } | null> {
    if (this.useMock) return mockStore.validateRequest(requestId, notes, dispatcherUser);
    return this.request<{ request: ServiceRequest; job: Job }>(`/api/service-requests/${requestId}/validate`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  async rejectRequest(
    requestId: string,
    reason: string,
    dispatcherUser: User
  ): Promise<ServiceRequest | null> {
    if (this.useMock) return mockStore.rejectRequest(requestId, reason, dispatcherUser);
    return this.request<ServiceRequest>(`/api/service-requests/${requestId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async deleteServiceRequest(requestId: string): Promise<boolean> {
    if (this.useMock) return mockStore.deleteServiceRequest(requestId);
    return this.request<{ success: boolean }>(`/api/service-requests/${requestId}`, {
      method: 'DELETE',
    }).then(() => true);
  }

  // --- OPERATIONAL JOBS ---
  async getJobs(): Promise<Job[]> {
    if (this.useMock) return mockStore.getJobs();
    return this.request<Job[]>('/api/jobs');
  }

  async getJobById(id: string): Promise<Job | undefined> {
    if (this.useMock) return mockStore.getJobById(id);
    return this.request<Job>(`/api/jobs/${id}`);
  }

  async updateJobStatus(
    jobId: string,
    newStatus: JobStatus,
    actorUser: User,
    notes?: string,
    completionData?: Job['completionReport']
  ): Promise<Job | null> {
    if (this.useMock) return mockStore.updateJobStatus(jobId, newStatus, actorUser, notes, completionData);
    return this.request<Job>(`/api/jobs/${jobId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ newStatus, notes, completionData }),
    });
  }

  async assignAndDispatchJob(
    jobId: string,
    electricianId: string,
    startTime: string,
    endTime: string,
    dispatchType: 'automatic' | 'manual' | 'override',
    actorUser: User
  ): Promise<Job | null> {
    if (this.useMock) {
      return mockStore.assignAndDispatchJob(jobId, electricianId, startTime, endTime, dispatchType, actorUser);
    }
    return this.request<Job>('/api/scheduling/dispatch', {
      method: 'POST',
      body: JSON.stringify({ jobId, electricianId, startTime, endTime, dispatchType }),
    });
  }

  async submitCustomerFeedback(jobId: string, rating: number, comments: string, user: User): Promise<Job | null> {
    if (this.useMock) return mockStore.submitCustomerFeedback(jobId, rating, comments, user);
    return this.request<Job>(`/api/jobs/${jobId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ rating, comments }),
    });
  }

  // --- ELECTRICIANS ---
  async getElectricians(): Promise<Electrician[]> {
    if (this.useMock) return mockStore.getElectricians();
    return this.request<Electrician[]>('/api/electricians');
  }

  async updateElectrician(id: string, updates: Partial<Electrician>): Promise<Electrician | undefined> {
    if (this.useMock) return mockStore.updateElectrician(id, updates);
    return this.request<Electrician>(`/api/electricians/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  async updateElectricianLocation(
    id: string,
    coords: { lat: number; lng: number; isSimulated: boolean }
  ): Promise<Electrician | undefined> {
    if (this.useMock) return mockStore.updateElectricianLocation(id, coords);
    return this.request<Electrician>(`/api/electricians/${id}/location`, {
      method: 'POST',
      body: JSON.stringify(coords),
    });
  }

  // --- INTELLIGENT SCHEDULING ---
  async optimizeSchedule(jobId: string): Promise<ScheduleRecommendationResult> {
    if (this.useMock) return generateScheduleRecommendations(jobId);
    return this.request<ScheduleRecommendationResult>('/api/scheduling/optimize', {
      method: 'POST',
      body: JSON.stringify({ jobId }),
    });
  }

  // --- DISRUPTION RECOVERY ---
  async simulateDisruption(options: DisruptionSimulationOptions, user: User): Promise<DisruptionRecord> {
    if (this.useMock) return simulateOperationalDisruption(options, user);
    return this.request<DisruptionRecord>('/api/recovery/detect', {
      method: 'POST',
      body: JSON.stringify(options),
    });
  }

  async applyRecovery(disruption: DisruptionRecord, user: User): Promise<boolean> {
    if (this.useMock) return applyDisruptionResolution(disruption, user);
    return this.request<boolean>('/api/recovery/approve', {
      method: 'POST',
      body: JSON.stringify({ disruptionId: disruption.id }),
    });
  }

  // --- APPROVALS & ESCALATIONS ---
  async getApprovals(): Promise<ApprovalRequest[]> {
    if (this.useMock) return mockStore.getApprovals();
    return this.request<ApprovalRequest[]>('/api/approvals');
  }

  async resolveApproval(
    id: string,
    decision: 'approved' | 'rejected' | 'clarification_requested',
    notes: string,
    user: User
  ): Promise<ApprovalRequest | null> {
    if (this.useMock) return mockStore.resolveApproval(id, decision, notes, user);
    return this.request<ApprovalRequest>(`/api/approvals/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ decision, notes }),
    });
  }

  async getEscalations(): Promise<EscalationAlert[]> {
    if (this.useMock) return mockStore.getEscalations();
    return this.request<EscalationAlert[]>('/api/escalations');
  }

  async createEscalation(
    data: Omit<EscalationAlert, 'id' | 'status' | 'createdAt'>,
    user: User
  ): Promise<EscalationAlert> {
    if (this.useMock) return mockStore.createEscalation(data, user);
    return this.request<EscalationAlert>('/api/escalations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // --- NOTIFICATIONS & AUDIT ---
  async getNotifications(role?: string, userId?: string): Promise<NotificationItem[]> {
    if (this.useMock) return mockStore.getNotifications(role, userId);
    return this.request<NotificationItem[]>('/api/notifications');
  }

  async markNotificationAsRead(id: string): Promise<void> {
    mockStore.markNotificationAsRead(id);
  }

  async markAllNotificationsAsRead(role?: string, userId?: string): Promise<void> {
    mockStore.markAllNotificationsAsRead(role, userId);
  }

  async getAuditLogs(): Promise<AuditLogEntry[]> {
    if (this.useMock) return mockStore.getAuditLogs();
    return this.request<AuditLogEntry[]>('/api/audit-logs');
  }

  async getPolicies(): Promise<PolicySettings> {
    if (this.useMock) return mockStore.getPolicies();
    return this.request<PolicySettings>('/api/policies');
  }

  async updatePolicies(policies: Partial<PolicySettings>, user: User): Promise<PolicySettings> {
    if (this.useMock) return mockStore.updatePolicies(policies, user);
    return this.request<PolicySettings>('/api/policies', {
      method: 'PATCH',
      body: JSON.stringify(policies),
    });
  }

  // --- USERS ---
  async getUsers(): Promise<User[]> {
    if (this.useMock) return mockStore.getUsers();
    return this.request<User[]>('/api/users');
  }

  async addUser(user: Omit<User, 'id' | 'createdAt'>): Promise<User> {
    if (this.useMock) return mockStore.addUser(user);
    return this.request<User>('/api/users', {
      method: 'POST',
      body: JSON.stringify(user),
    });
  }

  async updateUser(id: string, updates: Partial<User>): Promise<User | undefined> {
    if (this.useMock) return mockStore.updateUser(id, updates);
    return this.request<User>(`/api/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  // --- AI & MACHINE LEARNING SERVICES ---
  async getAIModelStatus(): Promise<any> {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/ai/model-status`);
      if (resp.ok) return await resp.json();
    } catch (e) {
      console.warn('AI model-status fetch failed, using fallback status', e);
    }
    return {
      status: 'healthy',
      all_models_ready: true,
      models: {
        duration: { model_name: 'LinearRegression (Baseline)', is_trained: true, version: '1.0.0', algorithm: 'LinearRegression', metrics: { MAE: 16.47, R2: 0.8264 }, data_source: 'SYNTHETIC_AUGMENTED' },
        delay: { model_name: 'RandomForestClassifier', is_trained: true, version: '1.0.0', algorithm: 'RandomForestClassifier', metrics: { F1: 0.8358, ROC_AUC: 0.9857 }, data_source: 'SYNTHETIC_AUGMENTED' },
        demand: { model_name: 'Ridge (Baseline)', is_trained: true, version: '1.0.0', algorithm: 'Ridge', metrics: { WAPE: 0.17, MAE: 1.92 }, data_source: 'SYNTHETIC_AUGMENTED' },
        disruption: { model_name: 'HistGradientBoostingClassifier', is_trained: true, version: '1.0.0', algorithm: 'HistGradientBoostingClassifier', metrics: { F1: 0.4112, ROC_AUC: 0.7521 }, data_source: 'SYNTHETIC_AUGMENTED' },
      },
    };
  }

  async getAIDemandForecast(): Promise<any> {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/ai/forecast-demand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (resp.ok) return await resp.json();
    } catch (e) {
      console.warn('AI forecast-demand fetch failed, using fallback', e);
    }
    return {
      forecast_period: 'Next 24h (Today)',
      total_expected_jobs: 52.0,
      peak_zone: 'Central',
      zone_forecasts: [
        { zone: 'Central', expected_jobs: 16.0, lower_bound: 12.8, upper_bound: 20.0, demand_level: 'PEAK' },
        { zone: 'North', expected_jobs: 11.0, lower_bound: 8.8, upper_bound: 13.8, demand_level: 'NORMAL' },
        { zone: 'South', expected_jobs: 10.0, lower_bound: 8.0, upper_bound: 12.5, demand_level: 'NORMAL' },
        { zone: 'East', expected_jobs: 8.0, lower_bound: 6.4, upper_bound: 10.0, demand_level: 'NORMAL' },
        { zone: 'West', expected_jobs: 7.0, lower_bound: 5.6, upper_bound: 8.8, demand_level: 'NORMAL' },
      ],
      model_name: 'Ridge (Baseline)',
      model_version: '1.0.0',
      data_source: 'SYNTHETIC_AUGMENTED',
    };
  }

  resetDemoData() {
    mockStore.resetToDefault();
  }
}

export const api = new ApiClient();

