import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { Job, CompletionReport } from '../../types';
import { Modal } from '../../components/common/Modal';
import {
  FileCheck,
  Upload,
  CheckCircle2,
  Trash2,
  AlertTriangle,
  Send,
} from 'lucide-react';

interface CompletionReportModalProps {
  job: Job | null;
  isOpen: boolean;
  onClose: () => void;
  onCompleted?: () => void;
}

export const CompletionReportModal: React.FC<CompletionReportModalProps> = ({
  job,
  isOpen,
  onClose,
  onCompleted,
}) => {
  const { user } = useAuth();
  const { refreshData } = useApp();

  const [faultIdentified, setFaultIdentified] = useState(
    'Thermal degradation at breaker terminal lug causing high impedance arcing.'
  );
  const [workPerformed, setWorkPerformed] = useState(
    'De-energized panel, replaced faulty 60A dual-pole breaker with OEM spec unit, torqued terminal screws to 45 in-lbs, tested voltage drop under 50% load.'
  );
  const [materialsUsed, setMaterialsUsed] = useState(
    '60A Dual-Pole Breaker, Antioxidant Paste, Heat-shrink wrap (4 AWG)'
  );
  const [notes, setNotes] = useState(
    'Conducted infrared thermographic post-repair scan. Steady state thermal temperature 28°C. No residual harmonic distortion.'
  );
  const [beforePhotos, setBeforePhotos] = useState<string[]>([
    'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600',
  ]);
  const [afterPhotos, setAfterPhotos] = useState<string[]>([
    'https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=600',
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!job) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!faultIdentified.trim() || !workPerformed.trim()) {
      setError('Both fault identification and work performed details are required for sign-off.');
      return;
    }

    if (!user) return;
    setIsSubmitting(true);
    setError('');

    try {
      const report: CompletionReport = {
        workPerformed,
        faultIdentified,
        materialsUsed: materialsUsed.split(',').map((m) => m.trim()),
        notes,
        beforePhotos,
        afterPhotos,
        completionTimestamp: new Date().toISOString(),
        signedOffByElectrician: user.name,
      };

      await api.updateJobStatus(
        job.id,
        'completed',
        user,
        'Job marked completed with official field sign-off report',
        report
      );

      refreshData();
      if (onCompleted) onCompleted();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit completion report');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Field Work Completion Report"
      subtitle={`Mandatory compliance sign-off for ${job.id}`}
      maxWidth="2xl"
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 text-xs">
        {/* Job Summary Banner */}
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
          <span className="font-mono font-bold text-blue-600 block">{job.id}</span>
          <h4 className="font-bold text-slate-900 text-sm mt-0.5">{job.title}</h4>
          <p className="text-slate-500 mt-1">Customer: {job.customerName} • {job.location.address}</p>
        </div>

        <div>
          <label className="block font-semibold text-slate-700 mb-1">
            Root Cause / Fault Identified *
          </label>
          <input
            type="text"
            required
            value={faultIdentified}
            onChange={(e) => setFaultIdentified(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
        </div>

        <div>
          <label className="block font-semibold text-slate-700 mb-1">
            Work Performed & Safety Verification *
          </label>
          <textarea
            required
            rows={3}
            value={workPerformed}
            onChange={(e) => setWorkPerformed(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
        </div>

        <div>
          <label className="block font-semibold text-slate-700 mb-1">
            Materials & Replacement Equipment Used (comma separated)
          </label>
          <input
            type="text"
            value={materialsUsed}
            onChange={(e) => setMaterialsUsed(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg"
          />
        </div>

        <div>
          <label className="block font-semibold text-slate-700 mb-1">
            Compliance & Customer Follow-Up Notes
          </label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg"
          />
        </div>

        {/* Verification Photos */}
        <div>
          <label className="block font-semibold text-slate-700 mb-2">
            Verification Photos (Before & After Repairs)
          </label>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-bold text-slate-600 block mb-2">Before Repair Photo</span>
              <img
                src={beforePhotos[0]}
                alt="Before"
                className="w-full h-24 object-cover rounded-lg border border-slate-200"
              />
            </div>
            <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
              <span className="font-bold text-emerald-800 block mb-2">After Sign-Off Photo</span>
              <img
                src={afterPhotos[0]}
                alt="After"
                className="w-full h-24 object-cover rounded-lg border border-emerald-300"
              />
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
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
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl flex items-center gap-2 shadow-md shadow-emerald-600/20 transition disabled:opacity-50"
          >
            <CheckCircle2 className="w-4 h-4" />
            {isSubmitting ? 'Submitting Report...' : 'Sign Off & Complete Job'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

