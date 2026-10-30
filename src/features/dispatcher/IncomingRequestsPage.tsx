import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { DataTable, Column } from '../../components/common/DataTable';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { ServiceRequest } from '../../types';
import { Modal } from '../../components/common/Modal';
import {
  Inbox,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Eye,
  FileCheck,
  Send,
  Sparkles,
} from 'lucide-react';

export const IncomingRequestsPage: React.FC = () => {
  const { user } = useAuth();
  const { serviceRequests, refreshData } = useApp();

  const [selectedRequest, setSelectedRequest] = useState<ServiceRequest | null>(null);
  const [actionType, setActionType] = useState<'validate' | 'reject' | 'view' | null>(null);
  const [validationNotes, setValidationNotes] = useState('Safety hazards assessed. Converted into active operational ticket.');
  const [rejectionReason, setRejectionReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  // We can filter for submitted and under review or all
  const incomingRequests = serviceRequests;

  const handleValidate = async () => {
    if (!selectedRequest || !user) return;
    setIsProcessing(true);
    try {
      await api.validateRequest(selectedRequest.id, validationNotes, user);
      refreshData();
      setActionType(null);
      setSelectedRequest(null);
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!selectedRequest || !user || !rejectionReason.trim()) return;
    setIsProcessing(true);
    try {
      await api.rejectRequest(selectedRequest.id, rejectionReason, user);
      refreshData();
      setActionType(null);
      setSelectedRequest(null);
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const columns: Column<ServiceRequest>[] = [
    {
      header: 'Request ID',
      accessorKey: 'id',
      className: 'font-mono font-bold text-blue-600',
    },
    {
      header: 'Customer',
      cell: (r) => (
        <div>
          <span className="font-bold text-slate-900 block">{r.customerName}</span>
          <span className="text-[11px] text-slate-500 capitalize">{r.customerType} • {r.customerPhone}</span>
        </div>
      ),
    },
    {
      header: 'Problem Title & Category',
      cell: (r) => (
        <div>
          <span className="font-bold text-slate-900 block truncate max-w-xs">{r.title}</span>
          <span className="text-xs text-slate-500 capitalize">{r.category.replace(/_/g, ' ')}</span>
        </div>
      ),
    },
    {
      header: 'Priority',
      cell: (r) => <PriorityBadge priority={r.priority} />,
    },
    {
      header: 'Submitted',
      cell: (r) => (
        <span className="text-xs text-slate-500">
          {new Date(r.submittedAt).toLocaleDateString([], {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      ),
    },
    {
      header: 'Status',
      cell: (r) => <StatusBadge status={r.status} />,
    },
    {
      header: 'Actions',
      cell: (r) => (
        <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
          {r.status === 'submitted' || r.status === 'under_review' ? (
            <>
              <button
                onClick={() => {
                  setSelectedRequest(r);
                  setActionType('validate');
                }}
                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-bold flex items-center gap-1 transition"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                Validate
              </button>
              <button
                onClick={() => {
                  setSelectedRequest(r);
                  setActionType('reject');
                }}
                className="px-2 py-1 bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-600 rounded text-xs font-semibold transition"
              >
                Reject
              </button>
            </>
          ) : (
            <button
              onClick={() => {
                setSelectedRequest(r);
                setActionType('view');
              }}
              className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-medium flex items-center gap-1"
            >
              <Eye className="w-3.5 h-3.5" />
              Inspect
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Incoming Customer Requests
          </h1>
          <p className="text-sm text-slate-500">
            Validate complaints, verify safety criteria, and convert into operational jobs
          </p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={incomingRequests}
        searchPlaceholder="Search request ID, customer name, title or category..."
        searchFilter={(item, query) =>
          item.id.toLowerCase().includes(query) ||
          item.customerName.toLowerCase().includes(query) ||
          item.title.toLowerCase().includes(query) ||
          item.category.toLowerCase().includes(query)
        }
        filterOptions={[
          {
            label: 'Lifecycle Status',
            key: 'status',
            options: [
              { label: 'Submitted (New)', value: 'submitted' },
              { label: 'Validated', value: 'validated' },
              { label: 'Assigned', value: 'assigned' },
              { label: 'In Progress', value: 'in_progress' },
              { label: 'Completed', value: 'completed' },
            ],
            filterFn: (item, val) => item.status === val,
          },
          {
            label: 'Priority',
            key: 'priority',
            options: [
              { label: 'Emergency', value: 'emergency' },
              { label: 'High', value: 'high' },
              { label: 'Medium', value: 'medium' },
              { label: 'Low', value: 'low' },
            ],
            filterFn: (item, val) => item.priority === val,
          },
        ]}
        onRowClick={(r) => {
          setSelectedRequest(r);
          setActionType('view');
        }}
      />

      {/* Validation Dialog */}
      {selectedRequest && actionType === 'validate' && (
        <Modal
          isOpen={true}
          onClose={() => setActionType(null)}
          title="Validate & Convert to Operational Job"
          subtitle={`Request ${selectedRequest.id}`}
          maxWidth="lg"
          footer={
            <div className="flex items-center justify-end gap-2 w-full">
              <button
                type="button"
                onClick={() => setActionType(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isProcessing}
                onClick={handleValidate}
                className="px-4 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg flex items-center gap-1.5 shadow-sm"
              >
                <FileCheck className="w-4 h-4" />
                {isProcessing ? 'Converting...' : 'Confirm & Create Job Ticket'}
              </button>
            </div>
          }
        >
          <div className="space-y-4">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
              <p><b>Customer:</b> {selectedRequest.customerName} ({selectedRequest.customerPhone})</p>
              <p className="mt-1"><b>Complaint:</b> {selectedRequest.title}</p>
              <p className="mt-1"><b>Address:</b> {selectedRequest.location.address}</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Dispatcher Triage & Validation Notes
              </label>
              <textarea
                rows={3}
                value={validationNotes}
                onChange={(e) => setValidationNotes(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>
          </div>
        </Modal>
      )}

      {/* Rejection Dialog */}
      {selectedRequest && actionType === 'reject' && (
        <Modal
          isOpen={true}
          onClose={() => setActionType(null)}
          title="Reject Service Request"
          subtitle={`Request ${selectedRequest.id}`}
          maxWidth="md"
          footer={
            <div className="flex items-center justify-end gap-2 w-full">
              <button
                type="button"
                onClick={() => setActionType(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isProcessing || !rejectionReason.trim()}
                onClick={handleReject}
                className="px-4 py-2 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm"
              >
                {isProcessing ? 'Rejecting...' : 'Confirm Rejection'}
              </button>
            </div>
          }
        >
          <div className="space-y-3">
            <p className="text-xs text-slate-600">
              Please specify the operational reason for rejecting this customer request:
            </p>
            <textarea
              rows={3}
              required
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="e.g. Beyond jurisdictional service boundary / Duplicate complaint"
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500/20"
            />
          </div>
        </Modal>
      )}

      {/* Detail View Dialog */}
      {selectedRequest && actionType === 'view' && (
        <Modal
          isOpen={true}
          onClose={() => setActionType(null)}
          title={`Request Overview • ${selectedRequest.id}`}
          maxWidth="lg"
        >
          <div className="space-y-3 text-xs">
            <div className="flex items-center gap-2">
              <PriorityBadge priority={selectedRequest.priority} />
              <StatusBadge status={selectedRequest.status} />
            </div>
            <h4 className="text-sm font-bold text-slate-900">{selectedRequest.title}</h4>
            <p className="text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200">
              {selectedRequest.description}
            </p>
            <div className="grid grid-cols-2 gap-2 pt-2 text-slate-600">
              <div><b>Customer:</b> {selectedRequest.customerName}</div>
              <div><b>Phone:</b> {selectedRequest.customerPhone}</div>
              <div><b>Location:</b> {selectedRequest.location.address}</div>
              <div><b>Time Window:</b> {selectedRequest.preferredTimeWindow}</div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

