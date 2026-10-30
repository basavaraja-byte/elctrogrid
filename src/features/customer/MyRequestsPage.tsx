import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { DataTable, Column } from '../../components/common/DataTable';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { ServiceRequest } from '../../types';
import { api } from '../../services/api/apiClient';
import { CreateRequestModal } from './CreateRequestModal';
import { RequestDetailPage } from './RequestDetailPage';
import { formatDateIST } from '../../utils/formatters';
import { Plus, MapPin, Calendar, Clock, ChevronRight, Trash2 } from 'lucide-react';

export const MyRequestsPage: React.FC = () => {
  const { user } = useAuth();
  const { serviceRequests, refreshData } = useApp();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);

  const customerRequests = serviceRequests.filter(
    (r) => r.customerId === user?.id || (user?.id === 'usr-cust-ind-1' && r.customerId.includes('ind-1'))
  );

  const columns: Column<ServiceRequest>[] = [
    {
      header: 'Request ID',
      accessorKey: 'id',
      className: 'font-mono font-bold text-blue-600',
    },
    {
      header: 'Problem Title & Details',
      cell: (r) => (
        <div>
          <span className="font-bold text-slate-900 block">{r.title}</span>
          <span className="text-xs text-slate-500 capitalize">{r.category.replace(/_/g, ' ')}</span>
        </div>
      ),
    },
    {
      header: 'Service Location',
      cell: (r) => (
        <div className="flex items-center gap-1.5 text-xs text-slate-600 max-w-[200px] truncate">
          <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
          <span className="truncate">{r.location.address}</span>
        </div>
      ),
    },
    {
      header: 'Submitted',
      cell: (r) => (
        <span className="text-xs text-slate-500 font-medium">
          {formatDateIST(r.submittedAt)}
        </span>
      ),
    },
    {
      header: 'Priority',
      cell: (r) => <PriorityBadge priority={r.priority} />,
    },
    {
      header: 'Status',
      cell: (r) => <StatusBadge status={r.status} />,
    },
    {
      header: 'Actions',
      cell: (r) => (
        <div className="flex items-center gap-1">
          <button
            onClick={async (e) => {
              e.stopPropagation();
              if (window.confirm(`Are you sure you want to delete request ${r.id} (${r.title})?`)) {
                await api.deleteServiceRequest(r.id);
                refreshData();
              }
            }}
            title="Delete Request"
            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition cursor-pointer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSelectedRequestId(r.id);
            }}
            title="View Details"
            className="p-1 text-slate-400 hover:text-blue-600 rounded-lg transition cursor-pointer"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            My Service Requests
          </h1>
          <p className="text-sm text-slate-500">
            Track real-time dispatch status, technician appointments, and completion reports
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 transition self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>New Service Request</span>
        </button>
      </div>

      {/* Requests Table */}
      <DataTable
        columns={columns}
        data={customerRequests}
        searchPlaceholder="Search complaints, categories or addresses..."
        searchFilter={(item, query) =>
          item.title.toLowerCase().includes(query) ||
          item.id.toLowerCase().includes(query) ||
          item.category.toLowerCase().includes(query) ||
          item.location.address.toLowerCase().includes(query)
        }
        filterOptions={[
          {
            label: 'Status',
            key: 'status',
            options: [
              { label: 'Submitted', value: 'submitted' },
              { label: 'Validated', value: 'validated' },
              { label: 'Assigned', value: 'assigned' },
              { label: 'En Route', value: 'en_route' },
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
        onRowClick={(row) => setSelectedRequestId(row.id)}
      />

      {/* Modals */}
      <CreateRequestModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={(id) => setSelectedRequestId(id)}
      />

      {selectedRequestId && (
        <RequestDetailPage
          requestId={selectedRequestId}
          onClose={() => setSelectedRequestId(null)}
        />
      )}
    </div>
  );
};

