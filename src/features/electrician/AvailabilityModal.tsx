import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { Modal } from '../../components/common/Modal';
import { CheckCircle2, Clock, AlertTriangle, Coffee } from 'lucide-react';

interface AvailabilityModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AvailabilityModal: React.FC<AvailabilityModalProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const { electricians, refreshData } = useApp();

  const currentTech = electricians.find((e) => e.userId === user?.id) || electricians[0];

  const [status, setStatus] = useState<any>(currentTech?.status || 'available');
  const [isUpdating, setIsUpdating] = useState(false);

  const handleSave = async () => {
    if (!currentTech) return;
    setIsUpdating(true);

    try {
      await api.updateElectrician(currentTech.id, {
        status,
        isAvailable: status === 'available',
      });
      refreshData();
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Field Availability & Status"
      subtitle={`Duty control for ${currentTech?.name}`}
      maxWidth="md"
      footer={
        <div className="flex justify-end gap-2 w-full">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isUpdating}
            onClick={handleSave}
            className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm"
          >
            {isUpdating ? 'Saving...' : 'Update Status'}
          </button>
        </div>
      }
    >
      <div className="space-y-3 text-xs">
        <p className="text-slate-600">
          Updating your operational status dynamically notifies the central dispatch engine to pause or route new assignments:
        </p>

        <div className="grid grid-cols-1 gap-2">
          {[
            { value: 'available', label: '🟢 Available on Shift', desc: 'Active in service zone and accepting jobs' },
            { value: 'busy', label: '🟡 Busy (On Job)', desc: 'Currently executing electrical work' },
            { value: 'on_break', label: '☕ On Break (30m)', desc: 'Temporarily paused for meal/rest' },
            { value: 'off_duty', label: '⚪ Off Duty / End of Shift', desc: 'Shift concluded' },
            { value: 'leave', label: '🔴 Report Unexpected Absence', desc: 'Vehicle failure / Emergency leave' },
          ].map((opt) => (
            <label
              key={opt.value}
              className={`p-3 rounded-xl border flex items-start gap-3 cursor-pointer transition ${
                status === opt.value
                  ? 'border-blue-600 bg-blue-50/60 shadow-xs'
                  : 'border-slate-200 hover:bg-slate-50'
              }`}
            >
              <input
                type="radio"
                name="availability"
                checked={status === opt.value}
                onChange={() => setStatus(opt.value)}
                className="mt-0.5 accent-blue-600"
              />
              <div>
                <span className="font-bold text-slate-900 block">{opt.label}</span>
                <span className="text-[11px] text-slate-500">{opt.desc}</span>
              </div>
            </label>
          ))}
        </div>
      </div>
    </Modal>
  );
};

