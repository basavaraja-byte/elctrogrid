import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { Modal } from '../../components/common/Modal';
import { AlertSeverity } from '../../types';
import { ShieldAlert, AlertTriangle } from 'lucide-react';

interface EscalateModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId?: string;
  defaultTitle?: string;
}

export const EscalateModal: React.FC<EscalateModalProps> = ({
  isOpen,
  onClose,
  jobId,
  defaultTitle = '',
}) => {
  const { user } = useAuth();
  const { refreshData } = useApp();

  const [title, setTitle] = useState(defaultTitle || 'Critical Feeder SLA Exception');
  const [description, setDescription] = useState(
    'Downtown electrical feeder delay exceeds standard operational threshold. Requesting emergency management schedule override.'
  );
  const [severity, setSeverity] = useState<AlertSeverity>('critical');
  const [targetRole, setTargetRole] = useState<'dispatcher' | 'management'>('management');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setIsSubmitting(true);

    try {
      await api.createEscalation(
        {
          jobId,
          title,
          description,
          severity,
          sourceRole: 'operations',
          raisedBy: user.name,
          assignedToRole: targetRole,
        },
        user
      );

      // Also create formal approval request if targeted to management
      if (targetRole === 'management') {
        await mockStoreEscalationApproval(title, description, jobId, user);
      }

      refreshData();
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  async function mockStoreEscalationApproval(t: string, d: string, jId: string | undefined, u: any) {
    // If escalated to management, create ApprovalRequest entry
    api.simulateDisruption({
      type: 'emergency_job_injection',
      targetJobId: jId,
      notes: d,
    }, u);
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Escalate Operational Exception"
      subtitle="Route critical field matters for priority action or management approval"
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4 text-xs">
        <div>
          <label className="block font-semibold text-slate-700 mb-1">
            Escalation Title *
          </label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Severity Level
            </label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as AlertSeverity)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg"
            >
              <option value="critical">🔴 Critical (Immediate)</option>
              <option value="high">🟠 High (1 Hour)</option>
              <option value="medium">🟡 Medium</option>
              <option value="low">⚪ Low</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Route To
            </label>
            <select
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value as any)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg"
            >
              <option value="management">Executive Management (Approval)</option>
              <option value="dispatcher">Central Dispatcher (Action)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block font-semibold text-slate-700 mb-1">
            Operational Justification & Field Notes *
          </label>
          <textarea
            required
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg"
          />
        </div>

        <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-bold flex items-center gap-1.5 shadow-sm"
          >
            <ShieldAlert className="w-4 h-4" />
            {isSubmitting ? 'Routing...' : 'Transmit Escalation'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

