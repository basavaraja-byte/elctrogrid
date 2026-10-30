import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { Job, CompletionReport, DamagedComponent } from '../../types';
import { Modal } from '../../components/common/Modal';
import {
  FileCheck,
  Upload,
  CheckCircle2,
  Trash2,
  AlertTriangle,
  Send,
  Plus,
  PackageX,
  Info,
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

  // Module 3: Damaged Components / Replacement Parts
  const [damagedComponents, setDamagedComponents] = useState<DamagedComponent[]>([
    {
      componentName: '60A Dual-Pole Circuit Breaker',
      damageDescription: 'Thermal carbon arc degradation at load terminal',
      quantity: 1,
      priceStatus: 'Price to be confirmed',
      remarks: 'Requires replacement by OEM equivalent',
    },
  ]);

  const [newPartName, setNewPartName] = useState('');
  const [newPartDesc, setNewPartDesc] = useState('');
  const [newPartQty, setNewPartQty] = useState(1);
  const [newPartRemarks, setNewPartRemarks] = useState('');

  const handleAddDamagedPart = () => {
    if (!newPartName.trim()) return;
    setDamagedComponents([
      ...damagedComponents,
      {
        componentName: newPartName.trim(),
        damageDescription: newPartDesc.trim() || 'Physical or electrical damage requiring replacement',
        quantity: newPartQty,
        priceStatus: 'Price to be confirmed',
        remarks: newPartRemarks.trim(),
      },
    ]);
    setNewPartName('');
    setNewPartDesc('');
    setNewPartQty(1);
    setNewPartRemarks('');
  };

  const handleRemoveDamagedPart = (idx: number) => {
    setDamagedComponents(damagedComponents.filter((_, i) => i !== idx));
  };

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
        damagedComponents,
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

        {/* Module 3: Damaged Components / Replacement Parts */}
        <div className="bg-amber-50/60 border border-amber-200/80 rounded-xl p-3.5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-amber-900 font-bold">
              <PackageX className="w-4 h-4 text-amber-600" />
              <span>Damaged Components / Replacement Parts</span>
            </div>
            <span className="text-[10px] bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded-full border border-amber-200">
              Customer Billed Separately
            </span>
          </div>

          <div className="text-[11px] text-amber-800 bg-amber-100/50 p-2 rounded-lg flex items-start gap-1.5">
            <Info className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
            <span>
              <b>Policy Note:</b> Customer is responsible for replacement part costs. Electrician labour charges are based strictly on working duration. Component prices remain <i>"Price to be confirmed"</i> until procurement verification.
            </span>
          </div>

          {/* List of reported damaged parts */}
          {damagedComponents.length > 0 && (
            <div className="space-y-2">
              {damagedComponents.map((comp, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-amber-200 p-2.5 rounded-lg flex items-center justify-between gap-2 shadow-xs"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-800">{comp.componentName}</span>
                      <span className="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono">
                        Qty: {comp.quantity}
                      </span>
                      <span className="text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded font-semibold border border-amber-200">
                        {comp.priceStatus}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">{comp.damageDescription}</p>
                    {comp.remarks && (
                      <p className="text-[10px] text-indigo-600 italic">Note: {comp.remarks}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveDamagedPart(idx)}
                    className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition cursor-pointer"
                    title="Remove item"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add Part Form */}
          <div className="pt-2 border-t border-amber-200/60 grid grid-cols-1 sm:grid-cols-12 gap-2 items-end">
            <div className="sm:col-span-4">
              <label className="block text-[10px] font-semibold text-slate-600 mb-0.5">Component Name</label>
              <input
                type="text"
                placeholder="e.g. 60A Breaker / Contactor"
                value={newPartName}
                onChange={(e) => setNewPartName(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg"
              />
            </div>
            <div className="sm:col-span-5">
              <label className="block text-[10px] font-semibold text-slate-600 mb-0.5">Damage Description</label>
              <input
                type="text"
                placeholder="e.g. Burn marks, arc pitting, loose lug"
                value={newPartDesc}
                onChange={(e) => setNewPartDesc(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-200 rounded-lg"
              />
            </div>
            <div className="sm:col-span-1">
              <label className="block text-[10px] font-semibold text-slate-600 mb-0.5">Qty</label>
              <input
                type="number"
                min={1}
                value={newPartQty}
                onChange={(e) => setNewPartQty(parseInt(e.target.value) || 1)}
                className="w-full px-2 py-1.5 text-xs bg-white border border-slate-200 rounded-lg text-center"
              />
            </div>
            <div className="sm:col-span-2">
              <button
                type="button"
                onClick={handleAddDamagedPart}
                className="w-full py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-lg flex items-center justify-center gap-1 shadow-xs transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Part
              </button>
            </div>
          </div>
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

