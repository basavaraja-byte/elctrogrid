import React, { useState, useEffect } from 'react';
import { Job, Electrician } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { PriorityBadge } from '../../components/common/StatusBadge';
import { isJobAssignedToElectrician } from '../../utils/technicianUtils';
import {
  Clock,
  MapPin,
  Check,
  X,
  AlertTriangle,
  Zap,
  Navigation,
  FileText,
  User,
  Phone,
  Timer,
  ChevronRight,
} from 'lucide-react';

interface IncomingJobOfferBannerProps {
  currentTech: Electrician;
  onViewReport?: (job: Job) => void;
}

export const IncomingJobOfferBanner: React.FC<IncomingJobOfferBannerProps> = ({
  currentTech,
  onViewReport,
}) => {
  const { user } = useAuth();
  const { jobs, refreshData } = useApp();

  const [rejectingJobId, setRejectingJobId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('Too far from current location');
  const [customReason, setCustomReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(60);

  // Find active offer targeting this technician
  const offeredJob = jobs.find(
    (j) =>
      j.currentOffer &&
      j.currentOffer.status === 'offered' &&
      isJobAssignedToElectrician(j, currentTech, user)
  );

  const offer = offeredJob?.currentOffer;

  // Live countdown timer driven by server-side expiresAt timestamp
  useEffect(() => {
    if (!offer) return;

    const updateCountdown = () => {
      const nowMs = Date.now();
      const expiresMs = new Date(offer.expiresAt).getTime();
      const diffSec = Math.max(0, Math.ceil((expiresMs - nowMs) / 1000));
      setSecondsRemaining(diffSec);

      if (diffSec <= 0) {
        // Trigger refresh to let the store sweep to next electrician
        refreshData();
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [offer, refreshData]);

  if (!offeredJob || !offer) {
    return null;
  }

  const isUrgent = secondsRemaining <= 15;
  const progressPct = Math.max(0, Math.min(100, (secondsRemaining / 60) * 100));

  const handleAccept = async () => {
    if (!user) return;
    setIsSubmitting(true);
    try {
      await api.acceptAssignmentOffer(offeredJob.id, currentTech.id, user);
      refreshData();
    } catch (err: any) {
      alert(err.message || 'Failed to accept job offer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectConfirm = async () => {
    if (!user) return;
    setIsSubmitting(true);
    try {
      const finalReason = rejectReason === 'Other' ? customReason || 'Technician unavailable' : rejectReason;
      await api.rejectAssignmentOffer(offeredJob.id, currentTech.id, finalReason, user);
      setRejectingJobId(null);
      refreshData();
    } catch (err: any) {
      alert(err.message || 'Failed to decline job offer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative overflow-hidden rounded-2xl border-2 border-amber-400 bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/5 p-5 sm:p-6 shadow-xl backdrop-blur-xs transition-all animate-fade-in">
      {/* Background glowing alert effect */}
      <div className={`absolute top-0 right-0 h-32 w-32 rounded-full blur-2xl pointer-events-none transition-opacity ${isUrgent ? 'bg-rose-500/25 animate-pulse' : 'bg-amber-400/20'}`} />

      {/* Top Banner Ribbon */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-amber-200">
        <div className="flex items-center gap-2.5">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white shadow-md transition-colors ${isUrgent ? 'bg-rose-600 animate-bounce' : 'bg-amber-500'}`}>
            <Zap className="w-5 h-5 fill-current" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-black uppercase tracking-wider text-amber-900">
                Incoming Field Job Request
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-200 text-amber-900">
                Attempt #{offer.attemptNumber}
              </span>
            </div>
            <h2 className="text-base font-extrabold text-slate-900 leading-tight">
              {offeredJob.title}
            </h2>
          </div>
        </div>

        {/* 60s Acceptance Countdown Timer */}
        <div className="flex items-center gap-3 bg-white px-3.5 py-2 rounded-xl border border-amber-200 shadow-xs self-start sm:self-auto">
          <div className="relative w-8 h-8 flex items-center justify-center">
            <svg className="w-8 h-8 transform -rotate-90">
              <circle
                cx="16"
                cy="16"
                r="13"
                stroke="currentColor"
                strokeWidth="3"
                className="text-slate-100"
                fill="transparent"
              />
              <circle
                cx="16"
                cy="16"
                r="13"
                stroke="currentColor"
                strokeWidth="3"
                className={`${isUrgent ? 'text-rose-600' : 'text-amber-500'} transition-all duration-1000`}
                strokeDasharray={81.68}
                strokeDashoffset={81.68 - (81.68 * progressPct) / 100}
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <Timer className={`w-3.5 h-3.5 absolute ${isUrgent ? 'text-rose-600' : 'text-amber-600'}`} />
          </div>
          <div>
            <div className="flex items-baseline gap-1">
              <span className={`text-xl font-black font-mono leading-none ${isUrgent ? 'text-rose-600 animate-pulse' : 'text-slate-900'}`}>
                {secondsRemaining}s
              </span>
              <span className="text-[10px] font-bold text-slate-400 uppercase">remaining</span>
            </div>
            <span className="text-[10px] text-slate-500 block">Auto-reassigns at 0s</span>
          </div>
        </div>
      </div>

      {/* Complaint Brief Details */}
      <div className="my-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div className="bg-white/80 p-3 rounded-xl border border-amber-200/60 shadow-2xs space-y-1">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Customer & Contact</span>
          <div className="font-bold text-slate-900 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-blue-600" />
            <span>{offeredJob.customerName}</span>
          </div>
          <div className="text-slate-500 text-[11px] flex items-center gap-1">
            <Phone className="w-3 h-3" />
            <a href={`tel:${offeredJob.customerPhone}`} className="hover:underline">{offeredJob.customerPhone}</a>
          </div>
        </div>

        <div className="bg-white/80 p-3 rounded-xl border border-amber-200/60 shadow-2xs space-y-1">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Service Location & Distance</span>
          <div className="font-bold text-slate-900 flex items-center gap-1.5 truncate">
            <MapPin className="w-3.5 h-3.5 text-rose-600 flex-shrink-0" />
            <span className="truncate">{offeredJob.location.address}</span>
          </div>
          <div className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1">
            <Navigation className="w-3 h-3" />
            <span>~{offer.estimatedDistanceKm?.toFixed(1) || '1.8'} km from your location</span>
          </div>
        </div>

        <div className="bg-white/80 p-3 rounded-xl border border-amber-200/60 shadow-2xs space-y-1">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Category & Urgency</span>
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-900 capitalize">
              {offeredJob.category.replace(/_/g, ' ')}
            </span>
            <PriorityBadge priority={offeredJob.priority} />
          </div>
          <div className="text-[11px] text-slate-500">
            Est. Duration: {offeredJob.estimatedDurationHours || 2.0}h
          </div>
        </div>
      </div>

      {/* Description Snippet */}
      <p className="text-xs text-slate-700 bg-white/60 p-3 rounded-xl border border-amber-200/50 mb-4 line-clamp-2 leading-relaxed">
        <span className="font-bold text-slate-900">Problem Description: </span>
        {offeredJob.description}
      </p>

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <button
          type="button"
          onClick={() => onViewReport && onViewReport(offeredJob)}
          className="text-xs font-bold text-blue-700 hover:text-blue-900 flex items-center gap-1 cursor-pointer"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>View Full Customer Complaint Report</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => setRejectingJobId(offeredJob.id)}
            className="px-4 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-xs transition cursor-pointer"
          >
            <X className="w-3.5 h-3.5 text-rose-600" />
            <span>Reject Job</span>
          </button>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleAccept}
            className="px-6 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-extrabold flex items-center gap-2 shadow-md shadow-emerald-600/30 transition transform active:scale-95 cursor-pointer"
          >
            <Check className="w-4 h-4" />
            <span>Accept Job ({secondsRemaining}s)</span>
          </button>
        </div>
      </div>

      {/* Reject Reason Confirmation Dialog */}
      {rejectingJobId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white w-full max-w-md rounded-2xl p-5 shadow-2xl border border-slate-200 space-y-4 animate-scale-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-rose-600 font-extrabold text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span>Decline Job Request</span>
              </div>
              <button
                onClick={() => setRejectingJobId(null)}
                className="w-7 h-7 rounded-lg bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              If you decline, this request will be immediately offered to the next nearest eligible electrician in Mysuru. Please select a reason:
            </p>

            <div className="space-y-2 text-xs">
              {[
                'Too far from current location',
                'Emergency personal leave',
                'Vehicle / equipment in maintenance',
                'Specialized high-voltage gear unavailable',
                'Other',
              ].map((r) => (
                <label
                  key={r}
                  className={`flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer transition ${
                    rejectReason === r ? 'border-rose-400 bg-rose-50/60 font-bold text-rose-900' : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="rejectReason"
                    value={r}
                    checked={rejectReason === r}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="text-rose-600"
                  />
                  <span>{r}</span>
                </label>
              ))}

              {rejectReason === 'Other' && (
                <textarea
                  rows={2}
                  value={customReason}
                  onChange={(e) => setCustomReason(e.target.value)}
                  placeholder="Specify reason..."
                  className="w-full p-2 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-rose-500/20"
                />
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setRejectingJobId(null)}
                className="px-3.5 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleRejectConfirm}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl shadow-xs transition cursor-pointer"
              >
                Confirm Decline
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

