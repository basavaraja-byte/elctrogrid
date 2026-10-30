import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { Modal } from '../../components/common/Modal';
import { LeafletMap } from '../../components/maps/LeafletMap';
import {
  Radio,
  Play,
  Pause,
  RotateCcw,
  Navigation,
  Compass,
  Gauge,
  MapPin,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

interface SimulatedLocationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Waypoint {
  name: string;
  lat: number;
  lng: number;
  speedKmH: number;
  heading: string;
}

const MYSURU_ROUTE_WAYPOINTS: Waypoint[] = [
  { name: 'Saraswathipuram CHESCOM Division (Base)', lat: 12.3052, lng: 76.6358, speedKmH: 0, heading: 'Stationary' },
  { name: 'Kantharaj Urs Road Junction', lat: 12.3005, lng: 76.6321, speedKmH: 28, heading: '210° SSW' },
  { name: 'Kuvempunagar Complex & Feeder Zone', lat: 12.2905, lng: 76.6320, speedKmH: 34, heading: '180° S' },
  { name: 'Ramakrishnanagar Circle', lat: 12.2850, lng: 76.6210, speedKmH: 38, heading: '240° WSW' },
  { name: 'Jayanagar Electrical Substation', lat: 12.2910, lng: 76.6450, speedKmH: 32, heading: '75° ENE' },
  { name: 'Chamundipuram Main Road', lat: 12.2920, lng: 76.6560, speedKmH: 26, heading: '95° E' },
  { name: 'Sayyaji Rao Road Corridor', lat: 12.3130, lng: 76.6500, speedKmH: 30, heading: '345° NNW' },
  { name: 'Gokulam 3rd Stage Feeder', lat: 12.3280, lng: 76.6290, speedKmH: 35, heading: '315° NW' },
];

export const SimulatedLocationModal: React.FC<SimulatedLocationModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { user } = useAuth();
  const { electricians, refreshData } = useApp();

  const currentTech =
    electricians.find(
      (e) =>
        e.userId === user?.id ||
        e.id === user?.id ||
        (user?.employeeId && e.employeeId === user.employeeId) ||
        (user?.email && e.email.toLowerCase() === user.email.toLowerCase())
    ) || electricians[0];

  const [waypointIndex, setWaypointIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [currentLat, setCurrentLat] = useState(
    currentTech?.currentLocation?.lat || MYSURU_ROUTE_WAYPOINTS[0].lat
  );
  const [currentLng, setCurrentLng] = useState(
    currentTech?.currentLocation?.lng || MYSURU_ROUTE_WAYPOINTS[0].lng
  );
  const [currentSpeed, setCurrentSpeed] = useState(0);
  const [currentHeading, setCurrentHeading] = useState('Stationary');
  const [transmissionCount, setTransmissionCount] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Synchronize when tech changes
  useEffect(() => {
    if (currentTech?.currentLocation) {
      setCurrentLat(currentTech.currentLocation.lat);
      setCurrentLng(currentTech.currentLocation.lng);
    }
  }, [currentTech]);

  // Movement timer loop
  useEffect(() => {
    if (isRunning) {
      timerRef.current = setInterval(() => {
        setWaypointIndex((prevIdx) => {
          const nextIdx = (prevIdx + 1) % MYSURU_ROUTE_WAYPOINTS.length;
          const wp = MYSURU_ROUTE_WAYPOINTS[nextIdx];

          // Small random jitter for authentic GPS telemetry
          const jitterLat = Number((wp.lat + (Math.random() - 0.5) * 0.0008).toFixed(6));
          const jitterLng = Number((wp.lng + (Math.random() - 0.5) * 0.0008).toFixed(6));

          setCurrentLat(jitterLat);
          setCurrentLng(jitterLng);
          setCurrentSpeed(wp.speedKmH);
          setCurrentHeading(wp.heading);
          setTransmissionCount((c) => c + 1);

          if (currentTech) {
            void api.updateElectricianLocation(currentTech.id, {
              lat: jitterLat,
              lng: jitterLng,
              isSimulated: true,
            });
            refreshData();
          }

          return nextIdx;
        });
      }, 2000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRunning, currentTech, refreshData]);

  const handleStart = () => {
    setIsRunning(true);
  };

  const handlePause = () => {
    setIsRunning(false);
    setCurrentSpeed(0);
  };

  const handleReset = async () => {
    setIsRunning(false);
    setWaypointIndex(0);
    const baseWp = MYSURU_ROUTE_WAYPOINTS[0];
    setCurrentLat(baseWp.lat);
    setCurrentLng(baseWp.lng);
    setCurrentSpeed(0);
    setCurrentHeading('Stationary');

    if (currentTech) {
      await api.updateElectricianLocation(currentTech.id, {
        lat: baseWp.lat,
        lng: baseWp.lng,
        isSimulated: true,
      });
      refreshData();
    }
  };

  if (!currentTech) return null;

  const currentWp = MYSURU_ROUTE_WAYPOINTS[waypointIndex];
  const progressPct = Math.round(((waypointIndex + 1) / MYSURU_ROUTE_WAYPOINTS.length) * 100);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Field Vehicle Telemetry & GPS Route Simulation"
      subtitle="Interactive mock telemetry tracking for Mysuru electrical distribution circle"
      maxWidth="4xl"
    >
      <div className="space-y-4">
        {/* Prominent Simulated Badge Banner */}
        <div className="bg-blue-900 text-white p-4 rounded-2xl shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-xl ${isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-blue-800'}`}>
              <Radio className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-amber-400 text-amber-950">
                  ● SIMULATED GPS (DEMO MODE)
                </span>
                <span className="text-xs text-blue-200">
                  Transmissions: {transmissionCount} pings
                </span>
              </div>
              <p className="text-sm font-bold text-white mt-0.5">
                {currentTech.name} • {currentTech.employeeId} ({currentTech.skills.slice(0, 2).join(', ')})
              </p>
            </div>
          </div>

          {/* Action Buttons: Start, Pause, Reset */}
          <div className="flex items-center gap-2">
            {!isRunning ? (
              <button
                type="button"
                onClick={handleStart}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition cursor-pointer"
              >
                <Play className="w-4 h-4 fill-white" />
                {waypointIndex === 0 ? 'Start Route Simulation' : 'Resume Simulation'}
              </button>
            ) : (
              <button
                type="button"
                onClick={handlePause}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition cursor-pointer"
              >
                <Pause className="w-4 h-4 fill-white" />
                Pause
              </button>
            )}

            <button
              type="button"
              onClick={handleReset}
              className="px-3.5 py-2 bg-blue-800 hover:bg-blue-700 text-blue-100 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
            >
              <RotateCcw className="w-4 h-4" />
              Reset to Base
            </button>
          </div>
        </div>

        {/* Live Telemetry HUD Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
              Current Waypoint
            </span>
            <span className="font-bold text-slate-800 truncate block" title={currentWp.name}>
              {currentWp.name}
            </span>
          </div>

          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
              Simulated Speed
            </span>
            <span className="font-bold text-slate-800 flex items-center gap-1.5">
              <Gauge className="w-3.5 h-3.5 text-blue-600" />
              {currentSpeed} km/h
            </span>
          </div>

          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
              Heading & Bearing
            </span>
            <span className="font-bold text-slate-800 flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-indigo-600" />
              {currentHeading}
            </span>
          </div>

          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
              Route Progress
            </span>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-slate-200 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-blue-600 h-full rounded-full transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <span className="font-bold text-slate-800">{progressPct}%</span>
            </div>
          </div>
        </div>

        {/* Leaflet Map with Active Waypoint Position */}
        <div className="rounded-xl overflow-hidden border border-slate-200 shadow-xs">
          <LeafletMap
            electricians={[
              {
                ...currentTech,
                currentLocation: {
                  lat: currentLat,
                  lng: currentLng,
                  lastUpdated: new Date().toISOString(),
                  isSimulated: true,
                },
              },
            ]}
            center={[currentLat, currentLng]}
            zoom={13}
            height="300px"
          />
        </div>

        {/* Coordinate Readout */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs text-slate-600 font-mono">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-rose-500" />
            <span>
              LAT: <b className="text-slate-900">{currentLat}</b> • LNG: <b className="text-slate-900">{currentLng}</b>
            </span>
          </div>
          <span className="text-[11px] text-slate-400">
            Status: {isRunning ? '● Telemetry Streaming' : '○ Paused'}
          </span>
        </div>
      </div>
    </Modal>
  );
};
