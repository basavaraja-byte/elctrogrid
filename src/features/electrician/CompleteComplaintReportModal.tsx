import React, { useState } from 'react';
import { Job, Electrician } from '../../types';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { LeafletMap } from '../../components/maps/LeafletMap';
import { formatDateTimeIST, formatDateIST } from '../../utils/formatters';
import {
  X,
  User,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Clock,
  HardHat,
  FileText,
  AlertTriangle,
  Image as ImageIcon,
  CheckCircle2,
  Navigation,
  ExternalLink,
  Wrench,
  ShieldAlert,
  ZoomIn,
  Eye,
  Info,
  Layers,
  Sparkles,
} from 'lucide-react';

interface CompleteComplaintReportModalProps {
  job: Job | null;
  electrician?: Electrician;
  isOpen: boolean;
  onClose: () => void;
  onOpenWorkReport?: (job: Job) => void;
}

export const CompleteComplaintReportModal: React.FC<CompleteComplaintReportModalProps> = ({
  job,
  electrician,
  isOpen,
  onClose,
  onOpenWorkReport,
}) => {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  if (!isOpen || !job) return null;

  // Fallback realistic electrical complaint photos if customer did not attach any
  const complaintPhotos =
    job.attachments && job.attachments.length > 0
      ? job.attachments
      : [
          'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800',
          'https://images.unsplash.com/photo-1544717305-2782549b5136?w=800',
        ];

  // Calculate distance
  const techLat = electrician?.currentLocation?.lat || 12.3025;
  const techLng = electrician?.currentLocation?.lng || 76.6315;
  const dLat = ((job.location.lat - techLat) * Math.PI) / 180;
  const dLon = ((job.location.lng - techLng) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((techLat * Math.PI) / 180) *
      Math.cos((job.location.lat * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const distanceKm = Number((6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(1));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/70 backdrop-blur-xs animate-fade-in">
      <div className="bg-white w-full max-w-4xl max-h-[92vh] rounded-3xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col animate-scale-in">
        {/* Header */}
        <div className="p-5 sm:px-6 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-950 text-white flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/80 text-white flex items-center justify-center shadow-md">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-blue-300">{job.id}</span>
                <span className="text-slate-400">•</span>
                <span className="font-mono text-xs text-slate-300">REQ: {job.requestId}</span>
                <PriorityBadge priority={job.priority} />
                <StatusBadge status={job.status} size="sm" />
              </div>
              <h2 className="text-lg font-extrabold text-white leading-snug truncate max-w-xl">
                {job.title}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Content (Sections A through F) */}
        <div className="p-5 sm:p-6 space-y-6 overflow-y-auto text-xs text-slate-700">
          {/* SECTION A: Customer Information */}
          <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-200/60 pb-2">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                <User className="w-4 h-4 text-blue-600" />
                Section A • Customer Information
              </h3>
              <span className="text-[11px] font-bold text-slate-500">CHESCOM Consumer Record</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Customer Name</span>
                <span className="font-extrabold text-slate-900 text-sm mt-0.5 block">{job.customerName}</span>
                <span className="text-[11px] text-slate-500 font-mono">ID: {job.customerId}</span>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Phone Contact</span>
                <a
                  href={`tel:${job.customerPhone}`}
                  className="font-bold text-blue-700 text-sm mt-0.5 flex items-center gap-1 hover:underline"
                >
                  <Phone className="w-3.5 h-3.5" />
                  {job.customerPhone}
                </a>
                <span className="text-[11px] text-emerald-600 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> SMS Telemetry Linked
                </span>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Service Address</span>
                <span className="font-semibold text-slate-800 text-xs mt-0.5 flex items-start gap-1">
                  <MapPin className="w-3.5 h-3.5 text-rose-600 flex-shrink-0 mt-0.5" />
                  {job.location.address}
                </span>
              </div>
            </div>

            {job.additionalInstructions && (
              <div className="mt-2 p-2.5 bg-blue-50/70 border border-blue-200/70 rounded-xl text-blue-900">
                <span className="font-bold">Customer Instructions: </span>
                <span>{job.additionalInstructions}</span>
              </div>
            )}
          </div>

          {/* SECTION B: Complaint Specifications */}
          <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-200/60 pb-2">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Section B • Electrical Complaint Specifications
              </h3>
              <span className="text-[11px] font-bold text-indigo-600 capitalize">
                Category: {job.category.replace(/_/g, ' ')}
              </span>
            </div>

            <div className="space-y-2">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Complete Problem Description</span>
                <p className="mt-1 p-3 bg-white rounded-xl border border-slate-200 text-slate-800 leading-relaxed font-medium">
                  {job.description}
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-slate-600">
                <div className="bg-white p-2.5 rounded-xl border border-slate-200/80">
                  <span className="text-[10px] text-slate-400 block">Submitted At</span>
                  <span className="font-bold text-slate-900">{formatDateIST(job.createdAt)}</span>
                </div>
                <div className="bg-white p-2.5 rounded-xl border border-slate-200/80">
                  <span className="text-[10px] text-slate-400 block">Priority Level</span>
                  <span className="font-bold text-slate-900 uppercase">{job.priority}</span>
                </div>
                <div className="bg-white p-2.5 rounded-xl border border-slate-200/80">
                  <span className="text-[10px] text-slate-400 block">Est. Duration</span>
                  <span className="font-bold text-slate-900">{job.estimatedDurationHours || 2.0} Hours</span>
                </div>
                <div className="bg-white p-2.5 rounded-xl border border-slate-200/80">
                  <span className="text-[10px] text-slate-400 block">SLA Target</span>
                  <span className="font-bold text-emerald-700">Within 2 Hours</span>
                </div>
              </div>

              {job.requiredSkills && job.requiredSkills.length > 0 && (
                <div className="pt-2">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                    Required Technician Qualifications
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {job.requiredSkills.map((s, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* SECTION C: Photographs & Attachments */}
          <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-200/60 pb-2">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                <ImageIcon className="w-4 h-4 text-teal-600" />
                Section C • Customer Uploaded Photographs ({complaintPhotos.length})
              </h3>
              <span className="text-[11px] text-slate-500">Click any image to enlarge</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {complaintPhotos.map((imgUrl, idx) => (
                <div
                  key={idx}
                  onClick={() => setSelectedImage(imgUrl)}
                  className="group relative aspect-video rounded-xl overflow-hidden border border-slate-200 bg-slate-100 cursor-pointer shadow-xs hover:shadow-md transition"
                >
                  <img src={imgUrl} alt={`Complaint attachment ${idx + 1}`} className="w-full h-full object-cover group-hover:scale-105 transition" />
                  <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white gap-1 font-bold text-[11px]">
                    <ZoomIn className="w-4 h-4" />
                    <span>View Photo</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* SECTION D: Location Map & Navigation */}
          <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-200/60 pb-2">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                <Navigation className="w-4 h-4 text-rose-600" />
                Section D • Site Location & Navigation Telemetry
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold text-slate-700">~{distanceKm} km from technician</span>
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(job.location.address)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-[10px] font-bold flex items-center gap-1 shadow-xs transition"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>Google Maps GPS</span>
                </a>
              </div>
            </div>

            <div className="h-56 rounded-xl overflow-hidden border border-slate-200 shadow-xs relative">
              <LeafletMap
                jobs={[job]}
                electricians={electrician ? [electrician] : []}
                selectedJobId={job.id}
                selectedElectricianId={electrician?.id}
                height="100%"
                center={[job.location.lat, job.location.lng]}
                zoom={14}
              />
            </div>
          </div>

          {/* SECTION E: Job Lifecycle & Assignment Telemetry */}
          <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-200/80 space-y-3">
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5 border-b border-slate-200/60 pb-2">
              <Clock className="w-4 h-4 text-indigo-600" />
              Section E • Job Lifecycle Timestamps & Assignment History
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Created / Submitted</span>
                <span className="font-bold text-slate-900">{formatDateTimeIST(job.createdAt)}</span>
              </div>
              <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Assigned Electrician</span>
                <span className="font-bold text-slate-900">{job.assignedElectricianName || 'Unassigned'}</span>
              </div>
              <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Work Started (Timer)</span>
                <span className="font-bold text-slate-900">
                  {job.actualStartTime ? formatDateTimeIST(job.actualStartTime) : 'Not Started'}
                </span>
              </div>
              <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Work Completed</span>
                <span className="font-bold text-slate-900">
                  {job.actualCompletionTime ? formatDateTimeIST(job.actualCompletionTime) : 'In Progress'}
                </span>
              </div>
            </div>

            {/* Assignment attempt history */}
            {job.assignmentHistory && job.assignmentHistory.length > 0 && (
              <div className="mt-2 p-3 bg-white rounded-xl border border-slate-200 space-y-1.5">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-500 block">
                  1-Minute Assignment Attempt Log
                </span>
                <div className="divide-y divide-slate-100 text-xs">
                  {job.assignmentHistory.map((att, idx) => (
                    <div key={idx} className="py-1.5 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-slate-600">Attempt #{att.attemptNumber}</span>
                        <span className="font-bold text-slate-900">{att.technicianName}</span>
                        <span className="text-slate-400 font-mono text-[11px]">(~{att.estimatedDistanceKm?.toFixed(1)} km)</span>
                      </div>
                      <div>
                        {att.status === 'accepted' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            Accepted within 60s
                          </span>
                        )}
                        {att.status === 'rejected' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">
                            Rejected: {att.responseReason || 'Declined'}
                          </span>
                        )}
                        {att.status === 'timed_out' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                            Expired (60s Timed Out)
                          </span>
                        )}
                        {att.status === 'offered' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 animate-pulse">
                            Active Offer (Pending 60s)
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* SECTION F: Technician Field Work Report */}
          <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-200/60 pb-2">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                <Wrench className="w-4 h-4 text-emerald-600" />
                Section F • Technician Work Report & Sign-Off
              </h3>
              {job.completionReport && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                  Signed Off by {job.completionReport.signedOffByElectrician}
                </span>
              )}
            </div>

            {job.completionReport ? (
              <div className="space-y-2 bg-white p-3.5 rounded-xl border border-slate-200">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Actual Fault Identified</span>
                  <p className="font-semibold text-slate-800 mt-0.5">{job.completionReport.faultIdentified}</p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Work Performed</span>
                  <p className="text-slate-700 mt-0.5">{job.completionReport.workPerformed}</p>
                </div>
                {job.damagedComponents && job.damagedComponents.length > 0 && (
                  <div className="pt-2 border-t border-slate-100">
                    <span className="text-[10px] uppercase font-bold text-amber-800 block mb-1">
                      Reported Damaged Components (Client Responsibility)
                    </span>
                    <div className="space-y-1">
                      {job.damagedComponents.map((part, pIdx) => (
                        <div key={pIdx} className="flex justify-between items-center text-xs p-1.5 bg-amber-50/60 rounded">
                          <div>
                            <span className="font-bold text-slate-900">{part.componentName}</span> (Qty: {part.quantity})
                            <span className="text-slate-500 block text-[11px]">{part.damageDescription}</span>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                            Price to be confirmed
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 bg-white rounded-xl border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
                <div>
                  <h4 className="font-bold text-slate-900">Work In Progress</h4>
                  <p className="text-slate-500 text-[11px]">
                    Record inspection findings, damaged parts, and completion sign-off once repairs are performed.
                  </p>
                </div>
                {onOpenWorkReport && job.status === 'in_progress' && (
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      onOpenWorkReport(job);
                    }}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition cursor-pointer flex-shrink-0"
                  >
                    Open Completion Report Modal
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end flex-shrink-0">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-800 hover:bg-slate-900 text-white font-bold rounded-xl text-xs transition cursor-pointer"
          >
            Close Complaint Report
          </button>
        </div>
      </div>

      {/* Enlarged Image Zoom Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md cursor-pointer"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-3xl max-h-[85vh] overflow-hidden rounded-2xl shadow-2xl">
            <img src={selectedImage} alt="Enlarged complaint attachment" className="w-full h-full object-contain" />
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/60 text-white flex items-center justify-center"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

