import React, { useState, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { Modal } from '../../components/common/Modal';
import { ProblemCategory, JobPriority, LocationCoordinates } from '../../types';
import { MYSURU_LOCALITIES } from '../../data/seedData';
import {
  Upload,
  Trash2,
  AlertTriangle,
  Send,
  Zap,
  MapPin,
  Image as ImageIcon,
  FileText,
  PlusCircle,
  X,
} from 'lucide-react';

interface AttachmentFile {
  id: string;
  name: string;
  sizeKb: number;
  dataUrl: string;
}

interface CreateRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (requestId: string) => void;
}

export const CreateRequestModal: React.FC<CreateRequestModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { user } = useAuth();
  const { refreshData } = useApp();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const isCommercial = user?.customerCategory === 'commercial';
  const commercialLocations = user?.commercialLocations || [];

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<ProblemCategory>('residential_wiring');
  const [priority, setPriority] = useState<JobPriority>('medium');
  const [preferredDate, setPreferredDate] = useState(
    new Date(Date.now() + 86400000).toISOString().split('T')[0]
  );
  const [preferredTimeWindow, setPreferredTimeWindow] = useState('09:00 - 12:00');
  const [contactName, setContactName] = useState(user?.name || '');
  const [contactPhone, setContactPhone] = useState(user?.phone || '+91 98450 21001');
  const [additionalInstructions, setAdditionalInstructions] = useState('');
  
  // Mysuru locality selection
  const [selectedLocalityIdx, setSelectedLocalityIdx] = useState(0);
  const [selectedLocationIndex, setSelectedLocationIndex] = useState(0);
  const [address, setAddress] = useState(
    isCommercial && commercialLocations.length > 0
      ? commercialLocations[0].address
      : '#142, 5th Cross, Saraswathipuram'
  );
  const [city, setCity] = useState('Mysuru');
  const [postalCode, setPostalCode] = useState(
    isCommercial && commercialLocations.length > 0
      ? commercialLocations[0].postalCode
      : '570009'
  );

  // Attachments State
  const [attachments, setAttachments] = useState<AttachmentFile[]>([
    {
      id: 'att-seed-1',
      name: 'distribution_breaker_panel.jpg',
      sizeKb: 184,
      dataUrl: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600',
    },
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const dataUrl = event.target?.result as string;
        setAttachments((prev) => [
          ...prev,
          {
            id: `att-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
            name: file.name,
            sizeKb: Math.round(file.size / 1024),
            dataUrl,
          },
        ]);
      };
      reader.readAsDataURL(file);
    });

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAddSamplePhoto = () => {
    const samplePhotos = [
      {
        name: 'mcb_tripped_switchboard.jpg',
        sizeKb: 210,
        url: 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600',
      },
      {
        name: 'motor_starter_sparking.jpg',
        sizeKb: 340,
        url: 'https://images.unsplash.com/photo-1544724569-5f546fd6f2b5?w=600',
      },
      {
        name: 'earthing_ground_rod_corrosion.jpg',
        sizeKb: 175,
        url: 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=600',
      },
    ];
    const picked = samplePhotos[attachments.length % samplePhotos.length];
    setAttachments((prev) => [
      ...prev,
      {
        id: `att-sample-${Date.now()}`,
        name: picked.name,
        sizeKb: picked.sizeKb,
        dataUrl: picked.url,
      },
    ]);
  };

  const handleRemoveAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setError('Please provide a title and detailed problem description.');
      return;
    }

    if (!user) return;
    setIsSubmitting(true);
    setError('');

    try {
      const activeLocality = MYSURU_LOCALITIES[selectedLocalityIdx % MYSURU_LOCALITIES.length];
      const location: LocationCoordinates = {
        lat: activeLocality.lat + (Math.random() - 0.5) * 0.005,
        lng: activeLocality.lng + (Math.random() - 0.5) * 0.005,
        address,
        city: 'Mysuru',
        postalCode,
      };

      const created = await api.createServiceRequest(
        {
          customerId: user.id,
          customerName: user.name,
          customerType: user.customerCategory || 'individual',
          customerPhone: contactPhone,
          customerEmail: user.email,
          title,
          description,
          category,
          priority,
          location,
          preferredDate,
          preferredTimeWindow,
          attachments: attachments.map((a) => a.dataUrl),
          additionalInstructions,
        },
        user
      );

      refreshData();
      if (onSuccess) onSuccess(created.id);
      onClose();
      // Reset form
      setTitle('');
      setDescription('');
    } catch (err: any) {
      setError(err.message || 'Failed to submit service request');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Submit Electrical Service Request"
      subtitle="Report an issue or request electrical maintenance in Mysuru"
      maxWidth="2xl"
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Category & Urgency */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Electrical Problem Category *
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as ProblemCategory)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 bg-white"
            >
              <option value="residential_wiring">⚡ Residential Wiring & Cabling Fault</option>
              <option value="power_outage">🔌 Power Outage & Feeder Breakdown</option>
              <option value="switch_socket">🔌 Switchboards, Sockets & Earthing</option>
              <option value="panel_breaker">🎛️ Distribution Panel & MCB Breaker Trip</option>
              <option value="short_circuit">💥 Short Circuit & Arcing Fault</option>
              <option value="lighting_fixture">💡 Lighting Fixtures & High-Mast Lamps</option>
              <option value="fan_motor_repair">🌀 Ceiling Fan & Exhaust Motor Repair</option>
              <option value="three_phase_power">⚙️ 3-Phase Heavy Power & Motor Starter</option>
              <option value="solar_inverter">☀️ Solar Rooftop PV & Inverter Grid-Tie</option>
              <option value="ev_charging">🚗 EV Charging Station Fault</option>
              <option value="generator_backup">🔋 Diesel Generator Backup & ATS</option>
              <option value="transformer_substation">🏭 Transformer & Substation Fault</option>
              <option value="preventive_maintenance">🛠️ Scheduled Electrical Inspection & Safety Audit</option>
              <option value="other_electrical">📋 Other Electrical Anomaly</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Urgency / Priority *
            </label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as JobPriority)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
            >
              <option value="low">Low (Standard maintenance, 48h-72h)</option>
              <option value="medium">Medium (Standard repair, 24h)</option>
              <option value="high">High (Major impact / partial outage, 2h-4h)</option>
              <option value="emergency">🚨 EMERGENCY (Life safety / Total blackout, 45m)</option>
            </select>
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Problem Title *
          </label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Total power outage in server room after thunderstorm"
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Detailed Description & Observations *
          </label>
          <textarea
            required
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what occurred, any noises, smells, sparks, or equipment affected..."
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
          />
        </div>

        {/* Multi-Location Selection for Commercial */}
        {isCommercial && commercialLocations.length > 0 && (
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Select Enterprise Facility
            </label>
            <select
              value={selectedLocationIndex}
              onChange={(e) => {
                const idx = Number(e.target.value);
                setSelectedLocationIndex(idx);
                setAddress(commercialLocations[idx].address);
                setCity(commercialLocations[idx].city);
                setPostalCode(commercialLocations[idx].postalCode);
              }}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-blue-50/30"
            >
              {commercialLocations.map((loc, idx) => (
                <option key={idx} value={idx}>
                  {loc.address} ({loc.city}, {loc.postalCode})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Mysuru Locality Selector for Individual Customers */}
        {!isCommercial && (
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Mysuru Neighborhood / Feeder Zone *
            </label>
            <select
              value={selectedLocalityIdx}
              onChange={(e) => {
                const idx = Number(e.target.value);
                setSelectedLocalityIdx(idx);
                const loc = MYSURU_LOCALITIES[idx % MYSURU_LOCALITIES.length];
                setAddress(`#${10 + idx * 4}, Main Road, ${loc.name}`);
                setPostalCode(loc.postalCode);
              }}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-blue-50/20"
            >
              {MYSURU_LOCALITIES.map((loc, idx) => (
                <option key={idx} value={idx}>
                  {loc.name} (Pin: {loc.postalCode})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Address */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-2">
            <label className="block text-xs font-semibold text-slate-700 mb-1">Service Address (Mysuru)</label>
            <input
              type="text"
              required
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="House/Plot #, Cross Road, Locality"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Postal Code (PIN)</label>
            <input
              type="text"
              required
              value={postalCode}
              onChange={(e) => setPostalCode(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg font-mono"
            />
          </div>
        </div>

        {/* Date & Time Window */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Preferred Service Date
            </label>
            <input
              type="date"
              value={preferredDate}
              onChange={(e) => setPreferredDate(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Preferred Time Window
            </label>
            <select
              value={preferredTimeWindow}
              onChange={(e) => setPreferredTimeWindow(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg"
            >
              <option value="08:00 - 12:00">Morning (08:00 - 12:00)</option>
              <option value="12:00 - 16:00">Afternoon (12:00 - 16:00)</option>
              <option value="16:00 - 20:00">Evening (16:00 - 20:00)</option>
              <option value="Flexible / Immediate">Flexible / Immediate Emergency</option>
            </select>
          </div>
        </div>

        {/* Contact Info */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">On-Site Contact</label>
            <input
              type="text"
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Phone</label>
            <input
              type="tel"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg"
            />
          </div>
        </div>

        {/* Attachments Section: Real File Upload + Preview */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-semibold text-slate-700">
              Complaint Photos & Equipment Documents
            </label>
            <span className="text-[11px] text-slate-500">
              {attachments.length} attached • JPG, PNG, PDF up to 10MB
            </span>
          </div>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,application/pdf"
            onChange={handleFileUpload}
            className="hidden"
          />

          {/* Upload Dropzone & Action Buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-3 border-2 border-dashed border-blue-200 hover:border-blue-400 bg-blue-50/40 hover:bg-blue-50 rounded-xl text-left flex items-center gap-3 transition cursor-pointer"
            >
              <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center flex-shrink-0">
                <Upload className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-900">Upload Files from Device</p>
                <p className="text-[10px] text-slate-500">Click to select photos or work orders</p>
              </div>
            </button>

            <button
              type="button"
              onClick={handleAddSamplePhoto}
              className="p-3 border border-slate-200 hover:border-amber-400 bg-slate-50 hover:bg-amber-50/40 rounded-xl text-left flex items-center gap-3 transition cursor-pointer"
            >
              <div className="w-8 h-8 rounded-lg bg-amber-500 text-white flex items-center justify-center flex-shrink-0">
                <PlusCircle className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-900">+ Add Demo Electrical Photo</p>
                <p className="text-[10px] text-slate-500">Fast 1-click test fixture</p>
              </div>
            </button>
          </div>

          {/* Attached Files List & Thumbnails */}
          {attachments.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {attachments.map((att) => (
                <div
                  key={att.id}
                  className="relative group p-1.5 bg-white rounded-xl border border-slate-200 shadow-xs flex items-center gap-2 overflow-hidden hover:border-slate-300 transition"
                >
                  <img
                    src={att.dataUrl}
                    alt={att.name}
                    className="w-11 h-11 rounded-lg object-cover bg-slate-100 flex-shrink-0 border border-slate-200"
                  />
                  <div className="min-w-0 flex-1 pr-5">
                    <p className="text-[11px] font-semibold text-slate-800 truncate" title={att.name}>
                      {att.name}
                    </p>
                    <span className="text-[10px] text-slate-400">{att.sizeKb} KB</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveAttachment(att.id)}
                    className="absolute right-1.5 top-1.5 p-1 bg-red-50 text-red-600 hover:bg-red-600 hover:text-white rounded-md transition"
                    title="Remove attachment"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-5 py-2.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20 rounded-xl flex items-center gap-2 transition disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            {isSubmitting ? 'Transmitting Request...' : 'Submit Request'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

