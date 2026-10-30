import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { Modal } from '../common/Modal';
import { DisruptionType, DisruptionRecord } from '../../types';
import {
  Sparkles,
  AlertTriangle,
  Play,
  CheckCircle2,
  Car,
  Clock,
  Zap,
  Wrench,
  Radio,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DemoScenarioRunnerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface DemoScenario {
  id: string;
  type: DisruptionType;
  title: string;
  badge: string;
  description: string;
  locality: string;
  icon: any;
  iconBg: string;
  iconColor: string;
  expectedOutcome: string;
}

export const DemoScenarioRunnerModal: React.FC<DemoScenarioRunnerModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { user } = useAuth();
  const { electricians, refreshData } = useApp();
  const navigate = useNavigate();

  const [isRunning, setIsRunning] = useState(false);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('scenario-1');
  const [lastExecutedRecord, setLastExecutedRecord] = useState<DisruptionRecord | null>(null);

  const scenarios: DemoScenario[] = [
    {
      id: 'scenario-1',
      type: 'electrician_unavailable',
      title: 'Technician Vehicle Breakdown',
      badge: 'Unscheduled Absence',
      description: 'Pradeep Hegde reports sudden utility van engine breakdown near Sayyaji Rao Road corridor.',
      locality: 'Sayyaji Rao Road / Devaraja Mohalla',
      icon: Car,
      iconBg: 'bg-rose-50 border-rose-200',
      iconColor: 'text-rose-600',
      expectedOutcome: 'Recovery engine takes technician off-duty and automatically reallocates ticket to standby wireman.',
    },
    {
      id: 'scenario-2',
      type: 'technician_delay',
      title: 'Severe Traffic Corridor Gridlock',
      badge: '+90 Mins Delay',
      description: 'Massive gridlock on Bangalore-Mysuru expressway near Columbia Asia junction delaying technician ETA.',
      locality: 'Hebbal Industrial / Ring Road',
      icon: Clock,
      iconBg: 'bg-amber-50 border-amber-200',
      iconColor: 'text-amber-600',
      expectedOutcome: 'Recovery engine recalculates arrival matrix and swaps schedule to prevent SLA breach.',
    },
    {
      id: 'scenario-3',
      type: 'emergency_job_injection',
      title: 'Hospital Emergency Feeder Outage',
      badge: 'Emergency Dispatch',
      description: 'High-voltage substation transformer flashover threatening critical ICU power at KR Hospital.',
      locality: 'Kuvempunagar / Saraswathipuram',
      icon: Zap,
      iconBg: 'bg-purple-50 border-purple-200',
      iconColor: 'text-purple-600',
      expectedOutcome: 'Engine shifts standard maintenance jobs and immediately dispatches Cat 4 Arc Flash specialist.',
    },
    {
      id: 'scenario-4',
      type: 'equipment_failure',
      title: 'Digital Cable Fault Locator Failure',
      badge: 'Tool Inoperable',
      description: 'Diagnostic equipment failed automated calibration verification prior to 3-phase testing.',
      locality: 'Vijayanagar 2nd Stage',
      icon: Wrench,
      iconBg: 'bg-blue-50 border-blue-200',
      iconColor: 'text-blue-600',
      expectedOutcome: 'Engine automatically matches an available wireman equipped with identical testing kit.',
    },
  ];

  const handleExecuteScenario = async (scenario: DemoScenario) => {
    if (!user) return;
    setIsRunning(true);
    setLastExecutedRecord(null);

    try {
      // 1. Simulate disruption using existing recovery engine
      const record = await api.simulateDisruption(
        {
          type: scenario.type,
          notes: `${scenario.title}: ${scenario.description} (Locality: ${scenario.locality})`,
        },
        user
      );

      // 2. Automatically execute recovery resolution so state reflects new schedule immediately
      await api.applyRecovery(record, user);

      // 3. Refresh app context
      refreshData();
      setLastExecutedRecord(record);
    } catch (err) {
      console.error('Failed to run demo scenario', err);
    } finally {
      setIsRunning(false);
    }
  };

  const selectedScenario = scenarios.find((s) => s.id === selectedScenarioId) || scenarios[0];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Demonstration Scenario Runner"
      subtitle="DEMONSTRATION MODE – SIMULATED FIELD EVENTS"
      maxWidth="4xl"
    >
      <div className="space-y-5">
        {/* Banner with Clear Demo Mode Label */}
        <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 p-4 rounded-xl text-white flex items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-white/10 border border-white/20">
              <Sparkles className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-400 text-slate-900">
                  DEMO ONLY
                </span>
                <span className="text-xs font-semibold text-blue-200">
                  Simulated Operational Disruptions
                </span>
              </div>
              <h3 className="text-sm font-bold text-white mt-0.5">
                Trigger Real-Time Autonomous Recovery
              </h3>
            </div>
          </div>
          <span className="text-[11px] text-slate-300 hidden sm:inline">
            Mysuru Sector Telemetry
          </span>
        </div>

        {/* Scenarios Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {scenarios.map((scenario) => {
            const Icon = scenario.icon;
            const isSelected = selectedScenarioId === scenario.id;

            return (
              <div
                key={scenario.id}
                onClick={() => setSelectedScenarioId(scenario.id)}
                className={`p-4 rounded-xl border-2 transition cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'bg-blue-50/70 border-blue-600 shadow-sm'
                    : 'bg-white border-slate-200 hover:border-blue-300 hover:bg-slate-50'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className={`p-1.5 rounded-lg border ${scenario.iconBg}`}>
                      <Icon className={`w-4 h-4 ${scenario.iconColor}`} />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                      {scenario.badge}
                    </span>
                  </div>

                  <h4 className="font-bold text-slate-900 text-sm">{scenario.title}</h4>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed line-clamp-2">
                    {scenario.description}
                  </p>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
                  <span>📍 {scenario.locality}</span>
                  {isSelected && (
                    <span className="font-bold text-blue-600">Selected</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Scenario Preview & Run Button */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="text-[10px] font-bold uppercase text-slate-400 block">
                Autonomous Reaction Protocol:
              </span>
              <p className="text-xs font-semibold text-slate-800 mt-0.5">
                {selectedScenario.expectedOutcome}
              </p>
            </div>

            <button
              disabled={isRunning}
              onClick={() => handleExecuteScenario(selectedScenario)}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 flex items-center gap-2 transition disabled:opacity-50 self-start sm:self-auto"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing Autonomous Recovery...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-white" />
                  <span>Execute Simulated Scenario</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Execution Result Notification */}
        {lastExecutedRecord && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2 text-xs text-emerald-950 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-emerald-800 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Scenario Successfully Executed & Recovered
              </span>
              <span className="font-mono text-emerald-700 font-bold">
                {lastExecutedRecord.id}
              </span>
            </div>

            <p className="leading-relaxed">
              {lastExecutedRecord.proposedResolution?.impactSummary ||
                'Autonomous recovery plan implemented immediately across all active technician schedules.'}
            </p>

            <div className="pt-2 flex flex-wrap gap-2">
              <button
                onClick={() => {
                  onClose();
                  navigate('/supervisor/recovery');
                }}
                className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg text-xs flex items-center gap-1 transition"
              >
                <span>View Before & After Comparison</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => {
                  onClose();
                  navigate('/supervisor/workforce');
                }}
                className="px-3 py-1.5 bg-white border border-emerald-300 text-emerald-800 hover:bg-emerald-100/50 font-bold rounded-lg text-xs transition"
              >
                Inspect Updated Gantt Timeline
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
