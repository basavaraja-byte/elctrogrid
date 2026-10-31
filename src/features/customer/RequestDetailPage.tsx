import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api/apiClient';
import { Modal } from '../../components/common/Modal';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { Avatar } from '../../components/common/Avatar';
import { PaymentCheckoutPanel } from '../../components/payment/PaymentCheckoutPanel';
import { formatDateTimeIST } from '../../utils/formatters';
import {
  MapPin,
  Calendar,
  Clock,
  HardHat,
  Phone,
  FileCheck,
  Star,
  CheckCircle,
  AlertCircle,
  Send,
  User,
  Image,
  Trash2,
} from 'lucide-react';

interface RequestDetailPageProps {
  requestId: string;
  onClose: () => void;
}

export const RequestDetailPage: React.FC<RequestDetailPageProps> = ({
  requestId,
  onClose,
}) => {
  const { user } = useAuth();
  const { serviceRequests, jobs, electricians, refreshData } = useApp();

  const request = serviceRequests.find((r) => r.id === requestId);
  const job = request?.associatedJobId
    ? jobs.find((j) => j.id === request.associatedJobId)
    : undefined;

  const assignedTech = job?.assignedElectricianId
    ? electricians.find((e) => e.id === job.assignedElectricianId)
    : undefined;

  // Feedback form state
  const [rating, setRating] = useState(5);
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);

  if (!request) return null;

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!job || !user) return;
    setIsSubmittingFeedback(true);

    try {
      await api.submitCustomerFeedback(job.id, rating, feedbackNotes, user);
      refreshData();
      setFeedbackSuccess(true);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const isCompleted = request.status === 'completed' || request.status === 'customer_confirmed' || request.status === 'closed';

  const handleDeleteRequest = async () => {
    if (window.confirm(`Are you sure you want to permanently delete service request ${request.id}?`)) {
      await api.deleteServiceRequest(request.id);
      refreshData();
      onClose();
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={`Request Details • ${request.id}`}
      subtitle="Complete electrical service lifecycle & status tracking"
      maxWidth="4xl"
    >
      <div className="space-y-6">
        {/* Header Summary Card */}
        <div className="bg-slate-50 rounded-xl p-4 sm:p-5 border border-slate-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono font-bold text-slate-500">
                  {request.id}
                </span>
                {request.associatedJobId && (
                  <span className="text-xs font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-semibold">
                    Job: {request.associatedJobId}
                  </span>
                )}
                <PriorityBadge priority={request.priority} />
                <StatusBadge status={request.status} />
              </div>
              <h3 className="text-lg font-bold text-slate-900">{request.title}</h3>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500 font-medium">
                Submitted: {formatDateTimeIST(request.submittedAt)}
              </span>
              <button
                type="button"
                onClick={handleDeleteRequest}
                className="px-2.5 py-1 text-xs font-semibold text-red-600 hover:text-white hover:bg-red-600 border border-red-200 hover:border-red-600 rounded-lg flex items-center gap-1 transition cursor-pointer"
                title="Delete this service request"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete</span>
              </button>
            </div>
          </div>

          <p className="mt-3 text-xs sm:text-sm text-slate-700 leading-relaxed bg-white p-3 rounded-lg border border-slate-200/80">
            {request.description}
          </p>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="flex items-start gap-2 text-slate-600">
              <MapPin className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block text-slate-800">Service Location:</span>
                <span>{request.location.address}, {request.location.city}</span>
              </div>
            </div>
            <div className="flex items-start gap-2 text-slate-600">
              <Calendar className="w-4 h-4 text-indigo-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block text-slate-800">Target Schedule:</span>
                <span>{request.preferredDate} ({request.preferredTimeWindow})</span>
              </div>
            </div>
            <div className="flex items-start gap-2 text-slate-600">
              <User className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block text-slate-800">Contact Person:</span>
                <span>{request.customerName} ({request.customerPhone})</span>
              </div>
            </div>
          </div>
        </div>

        {/* Attachments Preview if present */}
        {request.attachments && request.attachments.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
              <Image className="w-3.5 h-3.5" />
              Initial Complaint Photo Attachments
            </h4>
            <div className="flex flex-wrap gap-3">
              {request.attachments.map((imgUrl, i) => (
                <a
                  key={i}
                  href={imgUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-lg overflow-hidden border border-slate-200 w-28 h-28 hover:opacity-90 shadow-xs"
                >
                  <img src={imgUrl} alt={`Attachment ${i}`} className="w-full h-full object-cover" />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Intelligent Assignment Live Progress Banner */}
        {job?.currentOffer && job.currentOffer.status === 'offered' && (
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl p-4 border border-amber-200 shadow-xs">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping" />
                <h4 className="text-xs font-extrabold uppercase tracking-wider text-amber-900">
                  Electrician Assignment In Progress (Attempt #{job.currentOffer.attemptNumber})
                </h4>
              </div>
              <span className="text-[10px] font-bold bg-amber-200/80 text-amber-900 px-2 py-0.5 rounded-full">
                60s Acceptance Window
              </span>
            </div>
            <p className="text-xs text-amber-900 leading-relaxed">
              Dispatch offer sent to nearest available electrician <b className="font-semibold text-slate-900">{job.currentOffer.technicianName}</b> (~{job.currentOffer.estimatedDistanceKm?.toFixed(1) || '1.8'} km from your location). Awaiting confirmation...
            </p>
          </div>
        )}

        {(request.status === 'awaiting_assignment' || job?.status === 'awaiting_assignment') && !job?.currentOffer && (
          <div className="bg-amber-50 rounded-xl p-4 border border-amber-200">
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle className="w-4 h-4 text-amber-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900">
                Awaiting Operations Dispatch Allocation
              </h4>
            </div>
            <p className="text-xs text-amber-800 leading-relaxed">
              All immediate nearest candidate electricians are currently engaged on active repairs. Central Dispatch has been alerted to prioritize your ticket.
            </p>
          </div>
        )}

        {/* Assigned Electrician Card */}
        {assignedTech && (
          <div className="bg-blue-50/60 rounded-xl p-4 border border-blue-200">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-3 flex items-center gap-1.5">
              <HardHat className="w-4 h-4 text-blue-600" />
              Assigned Field Electrician
            </h4>
            <div className="flex items-center gap-4">
              <Avatar
                src={assignedTech.avatar}
                name={assignedTech.name}
                size="lg"
                className="border-2 border-blue-400 shadow-sm"
              />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h5 className="text-sm font-bold text-slate-900">{assignedTech.name}</h5>
                  <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded">
                    ★ {assignedTech.rating} Rating
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-0.5">
                  Certifications: {assignedTech.certifications.join(', ')}
                </p>
                <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  <span>{assignedTech.phone}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Status Lifecycle Timeline */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            Field Operational Lifecycle
          </h4>

          <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {job?.timeline && job.timeline.length > 0 ? (
              job.timeline.map((event, idx) => (
                <div key={idx} className="relative">
                  <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                  <div className="flex items-center gap-2">
                    <StatusBadge status={event.status} size="sm" />
                    <span className="text-xs text-slate-400">
                      {formatDateTimeIST(event.timestamp)}
                    </span>
                    <span className="text-xs font-semibold text-slate-600">
                      by {event.updatedBy} ({event.role})
                    </span>
                  </div>
                  {event.notes && (
                    <p className="text-xs text-slate-600 mt-1 pl-1 bg-slate-50 p-2 rounded">
                      {event.notes}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <div className="relative">
                <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                <div className="flex items-center gap-2">
                  <StatusBadge status={request.status} size="sm" />
                  <span className="text-xs text-slate-400">
                    {new Date(request.submittedAt).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-1 pl-1">
                  Request registered in ElectroGrid database.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Completion Report Section (if completed) */}
        {job?.completionReport && (
          <div className="bg-emerald-50/60 rounded-xl p-5 border border-emerald-200 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5">
                <FileCheck className="w-4 h-4 text-emerald-600" />
                Technician Field Completion Sign-Off
              </h4>
              <span className="text-xs text-emerald-700 font-semibold">
                Signed by: {job.completionReport.signedOffByElectrician}
              </span>
            </div>

            <div className="text-xs text-slate-700 space-y-2 bg-white/80 p-3 rounded-lg border border-emerald-100">
              <p>
                <b>Root Cause / Fault:</b> {job.completionReport.faultIdentified}
              </p>
              <p>
                <b>Work Completed:</b> {job.completionReport.workPerformed}
              </p>
              <p>
                <b>Materials Used:</b> {job.completionReport.materialsUsed.join(', ')}
              </p>
              <p>
                <b>Safety Verification Notes:</b> {job.completionReport.notes}
              </p>
            </div>

            {/* Before and After Photos */}
            {job.completionReport.afterPhotos && job.completionReport.afterPhotos.length > 0 && (
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1.5">
                  Inspection Verification Photos
                </span>
                <div className="flex gap-2">
                  {job.completionReport.afterPhotos.map((url, i) => (
                    <img
                      key={i}
                      src={url}
                      alt="Verification photo"
                      className="w-24 h-24 object-cover rounded-lg border border-slate-200"
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Razorpay Test Mode Payment Panel */}
        {job && isCompleted && (
          <PaymentCheckoutPanel job={job} onPaymentSuccess={() => refreshData()} />
        )}

        {/* Customer Feedback Section */}
        {isCompleted && (
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
              <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
              Customer Service Feedback
            </h4>

            {job?.feedback ? (
              <div className="p-3 bg-amber-50/50 border border-amber-200 rounded-lg text-xs space-y-1">
                <div className="flex items-center gap-1 text-amber-600 font-bold">
                  {Array.from({ length: job.feedback.rating }).map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-amber-500 text-amber-500" />
                  ))}
                  <span className="ml-2 text-slate-800">
                    {job.feedback.rating} / 5 Stars
                  </span>
                </div>
                <p className="text-slate-700 italic">"{job.feedback.comments}"</p>
                <span className="text-[10px] text-slate-400 block pt-1">
                  Submitted on: {new Date(job.feedback.submittedAt).toLocaleString()}
                </span>
              </div>
            ) : (
              <form onSubmit={handleFeedbackSubmit} className="space-y-3">
                <p className="text-xs text-slate-600">
                  Please rate your experience with field technician {job?.assignedElectricianName || 'electrician'}.
                </p>

                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRating(star)}
                      className="p-1 text-amber-400 hover:scale-110 transition"
                    >
                      <Star
                        className={`w-6 h-6 ${
                          star <= rating
                            ? 'fill-amber-400 text-amber-400'
                            : 'text-slate-300'
                        }`}
                      />
                    </button>
                  ))}
                  <span className="text-xs font-bold text-slate-700 ml-2">
                    {rating} of 5 Stars
                  </span>
                </div>

                <textarea
                  rows={2}
                  required
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="Share details on promptness, cleanliness, and communication..."
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={isSubmittingFeedback}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-sm"
                  >
                    <Send className="w-3.5 h-3.5" />
                    {isSubmittingFeedback ? 'Saving...' : 'Submit Feedback'}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
};

