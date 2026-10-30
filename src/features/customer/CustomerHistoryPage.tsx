import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { StatusBadge } from '../../components/common/StatusBadge';
import { RequestDetailPage } from './RequestDetailPage';
import {
  History,
  CheckCircle2,
  Star,
  FileText,
  Calendar,
  HardHat,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';

export const CustomerHistoryPage: React.FC = () => {
  const { user } = useAuth();
  const { jobs, serviceRequests } = useApp();

  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);

  // Filter completed and closed jobs
  const completedCustomerJobs = jobs.filter(
    (j) =>
      (j.customerId === user?.id || (user?.id === 'usr-cust-ind-1' && j.customerId.includes('ind-1'))) &&
      (j.status === 'completed' || j.status === 'customer_confirmed' || j.status === 'closed')
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Service History & Feedback
        </h1>
        <p className="text-sm text-slate-500">
          Archive of completed repairs, signed safety reports, and satisfaction scores
        </p>
      </div>

      {/* Grid of completed jobs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {completedCustomerJobs.map((job) => {
          return (
            <div
              key={job.id}
              onClick={() => setSelectedRequestId(job.requestId)}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-blue-300 transition-all cursor-pointer flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-500">{job.id}</span>
                    <StatusBadge status={job.status} size="sm" />
                  </div>
                  <span className="text-[11px] text-slate-400">
                    {new Date(job.createdAt).toLocaleDateString()}
                  </span>
                </div>

                <h3 className="text-sm font-bold text-slate-900">{job.title}</h3>
                <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed">
                  {job.completionReport?.workPerformed || job.description}
                </p>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <div className="flex items-center gap-1.5">
                    <HardHat className="w-3.5 h-3.5 text-blue-600" />
                    <span className="font-semibold text-slate-700">
                      {job.assignedElectricianName || 'Certified Electrician'}
                    </span>
                  </div>

                  {job.feedback ? (
                    <div className="flex items-center gap-1 text-amber-500 font-bold">
                      <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                      <span>{job.feedback.rating} / 5</span>
                    </div>
                  ) : (
                    <span className="text-[11px] font-semibold text-blue-600">
                      Rate this service →
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-3 bg-slate-50 p-2.5 rounded-lg flex items-center justify-between text-xs text-slate-600">
                <span className="flex items-center gap-1 text-[11px] text-emerald-700 font-semibold">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Compliance Signed
                </span>
                <span className="text-blue-600 font-bold flex items-center gap-0.5">
                  View Report
                  <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          );
        })}

        {completedCustomerJobs.length === 0 && (
          <div className="col-span-full bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400">
            <History className="w-10 h-10 mx-auto mb-2 text-slate-300" />
            <p className="text-sm font-medium">No completed service history yet.</p>
            <p className="text-xs text-slate-500 mt-1">
              Active repairs will move here once marked completed by the field electrician.
            </p>
          </div>
        )}
      </div>

      {selectedRequestId && (
        <RequestDetailPage
          requestId={selectedRequestId}
          onClose={() => setSelectedRequestId(null)}
        />
      )}
    </div>
  );
};

