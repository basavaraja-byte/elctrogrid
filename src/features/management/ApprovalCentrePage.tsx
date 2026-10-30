import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { ApprovalRequest } from '../../types';
import { Modal } from '../../components/common/Modal';
import {
  CheckSquare,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  Clock,
  ShieldCheck,
  User,
  ArrowRight,
} from 'lucide-react';

export const ApprovalCentrePage: React.FC = () => {
  const { user } = useAuth();
  const { approvals, refreshData } = useApp();

  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [decisionType, setDecisionType] = useState<'approved' | 'rejected' | 'clarification_requested' | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const filteredApprovals = approvals.filter((a) => {
    if (filterStatus !== 'all' && a.currentStatus !== filterStatus) return false;
    return true;
  });

  const handleDecision = async () => {
    if (!selectedApproval || !decisionType || !user) return;
    setIsProcessing(true);

    try {
      await api.resolveApproval(
        selectedApproval.id,
        decisionType,
        reviewNotes || `Executive decision: ${decisionType}`,
        user
      );
      refreshData();
      setSelectedApproval(null);
      setDecisionType(null);
      setReviewNotes('');
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const getImpactBadge = (level: string) => {
    switch (level) {
      case 'critical':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-100 text-red-800 border border-red-200">Critical Impact</span>;
      case 'high':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-orange-100 text-orange-800 border border-orange-200">High Impact</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-100 text-blue-800 border border-blue-200">Standard Exception</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Executive Approval Centre
          </h1>
          <p className="text-sm text-slate-500">
            Authorize major schedule overrides, SLA exemptions, overtime policies, and operational exceptions
          </p>
        </div>

        {/* Status filter tabs */}
        <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-xl p-1 shadow-xs">
          {['all', 'pending', 'approved', 'rejected'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg capitalize transition ${
                filterStatus === st
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Approvals Cards */}
      <div className="space-y-4">
        {filteredApprovals.map((req) => (
          <div
            key={req.id}
            className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition space-y-3"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-slate-500">{req.id}</span>
                {getImpactBadge(req.impactLevel)}
                <span className="text-xs font-bold uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                  {req.category.replace(/_/g, ' ')}
                </span>
                <span
                  className={`text-xs font-bold uppercase px-2 py-0.5 rounded ${
                    req.currentStatus === 'approved'
                      ? 'bg-emerald-100 text-emerald-800'
                      : req.currentStatus === 'rejected'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {req.currentStatus}
                </span>
              </div>

              <span className="text-xs text-slate-400">
                Submitted: {new Date(req.submittedAt).toLocaleString()}
              </span>
            </div>

            <h3 className="text-base font-bold text-slate-900">{req.title}</h3>
            <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-200/80">
              {req.details}
            </p>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-100 text-xs">
              <div className="flex items-center gap-3 text-slate-500">
                <span>
                  Requested by: <b className="text-slate-800">{req.requestedBy}</b> ({req.requesterRole})
                </span>
                {req.reviewedBy && (
                  <span>
                    Reviewed by: <b className="text-emerald-700">{req.reviewedBy}</b>
                  </span>
                )}
              </div>

              {req.currentStatus === 'pending' ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setSelectedApproval(req);
                      setDecisionType('clarification_requested');
                    }}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold text-xs transition"
                  >
                    Ask Clarification
                  </button>
                  <button
                    onClick={() => {
                      setSelectedApproval(req);
                      setDecisionType('rejected');
                    }}
                    className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg font-bold text-xs border border-rose-200 transition"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => {
                      setSelectedApproval(req);
                      setDecisionType('approved');
                    }}
                    className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs shadow-sm flex items-center gap-1 transition"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Approve Exception
                  </button>
                </div>
              ) : (
                <div className="text-slate-600 text-xs italic">
                  Decision note: "{req.reviewNotes || 'Approved per policy criteria'}"
                </div>
              )}
            </div>
          </div>
        ))}

        {filteredApprovals.length === 0 && (
          <div className="bg-white p-12 text-center text-xs text-slate-400 rounded-2xl border border-slate-200">
            No approval requests found for this status filter.
          </div>
        )}
      </div>

      {/* Decision Confirmation Modal */}
      {selectedApproval && decisionType && (
        <Modal
          isOpen={true}
          onClose={() => {
            setSelectedApproval(null);
            setDecisionType(null);
          }}
          title={`Confirm Management Decision: ${decisionType.toUpperCase()}`}
          subtitle={`Request ${selectedApproval.id}`}
          maxWidth="md"
          footer={
            <div className="flex justify-end gap-2 w-full">
              <button
                type="button"
                onClick={() => {
                  setSelectedApproval(null);
                  setDecisionType(null);
                }}
                className="px-4 py-2 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={handleDecision}
                className={`px-4 py-2 text-xs font-bold text-white rounded-lg shadow-sm flex items-center gap-1.5 ${
                  decisionType === 'approved'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : decisionType === 'rejected'
                    ? 'bg-rose-600 hover:bg-rose-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                {isProcessing ? 'Recording...' : `Execute ${decisionType.toUpperCase()}`}
              </button>
            </div>
          }
        >
          <div className="space-y-3 text-xs">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="font-bold text-slate-900 block">{selectedApproval.title}</span>
              <p className="text-slate-600 mt-1">{selectedApproval.details}</p>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Executive Authorization Notes / Audit Reason *
              </label>
              <textarea
                rows={3}
                required
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Enter formal justification for audit record..."
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

