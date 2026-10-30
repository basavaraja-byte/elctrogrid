import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Electrician, Job } from '../../types';
import { mockStore } from '../../services/mock/mockStore';
import { Radio, Users, Wrench, AlertTriangle, Layers, Play, Pause, Navigation } from 'lucide-react';

interface LeafletMapProps {
  electricians?: Electrician[];
  jobs?: Job[];
  selectedElectricianId?: string | null;
  selectedJobId?: string | null;
  onSelectElectrician?: (tech: Electrician) => void;
  onSelectJob?: (job: Job) => void;
  height?: string;
  center?: [number, number];
  zoom?: number;
}

export const LeafletMap: React.FC<LeafletMapProps> = ({
  electricians = [],
  jobs = [],
  selectedElectricianId,
  selectedJobId,
  onSelectElectrician,
  onSelectJob,
  height = '500px',
  center = [12.2958, 76.6394], // Mysuru, Karnataka, India
  zoom = 13,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  const [activeLayer, setActiveLayer] = useState<'all' | 'techs' | 'jobs' | 'emergency'>('all');
  const [isGpsSimulating, setIsGpsSimulating] = useState(false);

  // Periodic GPS Simulation Interval
  useEffect(() => {
    if (!isGpsSimulating) return;

    const intervalId = setInterval(() => {
      // Pick a subset of technicians to gently move along Mysuru streets
      const activeTechs = electricians.filter(
        (t) => t.status === 'en_route' || t.status === 'busy' || t.status === 'available'
      );

      activeTechs.forEach((t) => {
        const deltaLat = (Math.random() - 0.48) * 0.0014;
        const deltaLng = (Math.random() - 0.48) * 0.0014;
        
        // Keep bounded within Mysuru grid area
        let newLat = Number((t.currentLocation.lat + deltaLat).toFixed(6));
        let newLng = Number((t.currentLocation.lng + deltaLng).toFixed(6));

        if (newLat < 12.26) newLat = 12.30;
        if (newLat > 12.38) newLat = 12.32;
        if (newLng < 76.57) newLng = 76.64;
        if (newLng > 76.71) newLng = 76.63;

        mockStore.updateElectricianLocation(t.id, {
          lat: newLat,
          lng: newLng,
          isSimulated: true,
        });
      });
    }, 3500);

    return () => clearInterval(intervalId);
  }, [isGpsSimulating, electricians]);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center,
        zoom,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Markers
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;
    if (!map || !markersLayer) return;

    markersLayer.clearLayers();

    // 1. Plot Field Technicians in Mysuru
    if (activeLayer === 'all' || activeLayer === 'techs') {
      electricians.forEach((tech) => {
        const isSelected = tech.id === selectedElectricianId;
        const statusColor =
          tech.status === 'available'
            ? '#10b981' // emerald
            : tech.status === 'en_route'
            ? '#0ea5e9' // sky
            : tech.status === 'busy'
            ? '#f59e0b' // amber
            : '#94a3b8'; // slate

        const iconHtml = `
          <div style="
            background-color: ${statusColor};
            width: ${isSelected ? '34px' : '26px'};
            height: ${isSelected ? '34px' : '26px'};
            border-radius: 50%;
            border: 2.5px solid white;
            box-shadow: 0 4px 10px rgba(0,0,0,0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: bold;
            transition: all 0.2s;
            cursor: pointer;
          ">
            ⚡
          </div>
        `;

        const customIcon = L.divIcon({
          html: iconHtml,
          className: 'custom-tech-pin',
          iconSize: [isSelected ? 34 : 26, isSelected ? 34 : 26],
          iconAnchor: [isSelected ? 17 : 13, isSelected ? 17 : 13],
        });

        const marker = L.marker([tech.currentLocation.lat, tech.currentLocation.lng], {
          icon: customIcon,
        });

        const popupContent = `
          <div style="font-family: inherit; font-size: 12px; min-width: 210px; padding: 2px;">
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;">
              <span>${tech.name}</span>
              <span style="font-size: 10px; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; color: #475569;">${tech.employeeId}</span>
            </div>
            <div style="color: #64748b; font-size: 11px; margin-bottom: 6px;">
              Status: <b style="color: ${statusColor}; text-transform: capitalize;">${tech.status.replace('_', ' ')}</b>
            </div>
            <div style="font-size: 11px; color: #334155; margin-bottom: 3px;">
              <b>Shift:</b> ${tech.shiftHours.start} - ${tech.shiftHours.end}
            </div>
            <div style="font-size: 11px; color: #334155; margin-bottom: 6px;">
              <b>Daily Load:</b> ${tech.currentWorkload}h / ${tech.maxDailyHours}h
            </div>
            <div style="font-size: 10px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 4px;">
              Simulated Telemetry • Mysuru Grid
            </div>
          </div>
        `;

        marker.bindPopup(popupContent);
        marker.on('click', () => {
          if (onSelectElectrician) onSelectElectrician(tech);
        });

        markersLayer.addLayer(marker);
      });
    }

    // 2. Plot Active Jobs in Mysuru
    if (activeLayer === 'all' || activeLayer === 'jobs' || activeLayer === 'emergency') {
      jobs.forEach((job) => {
        if (activeLayer === 'emergency' && job.priority !== 'emergency') return;

        const isEmergency = job.priority === 'emergency';
        const isSelected = job.id === selectedJobId;
        const jobColor = isEmergency
          ? '#ef4444' // red
          : job.status === 'in_progress'
          ? '#f97316' // orange
          : job.status === 'assigned' || job.status === 'dispatched'
          ? '#8b5cf6' // purple
          : '#3b82f6'; // blue

        const iconHtml = `
          <div style="
            background-color: ${jobColor};
            width: ${isSelected ? '30px' : '22px'};
            height: ${isSelected ? '30px' : '22px'};
            border-radius: 5px;
            border: 2px solid white;
            box-shadow: 0 4px 10px rgba(0,0,0,0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 10px;
            font-weight: bold;
            cursor: pointer;
            ${isEmergency ? 'animation: pulse 1.5s infinite;' : ''}
          ">
            ${isEmergency ? '!' : 'J'}
          </div>
        `;

        const customIcon = L.divIcon({
          html: iconHtml,
          className: 'custom-job-pin',
          iconSize: [isSelected ? 30 : 22, isSelected ? 30 : 22],
          iconAnchor: [isSelected ? 15 : 11, isSelected ? 15 : 11],
        });

        const marker = L.marker([job.location.lat, job.location.lng], {
          icon: customIcon,
        });

        const popupContent = `
          <div style="font-family: inherit; font-size: 12px; min-width: 220px; padding: 2px;">
            <div style="font-weight: 700; color: #0f172a; margin-bottom: 2px;">
              ${job.id}: ${job.title}
            </div>
            <div style="color: #64748b; font-size: 11px; margin-bottom: 4px;">
              Customer: <b>${job.customerName}</b>
            </div>
            <div style="font-size: 11px; color: #334155; margin-bottom: 3px;">
              <b>Priority:</b> <span style="color: ${isEmergency ? '#ef4444' : '#2563eb'}; text-transform: uppercase; font-weight: bold;">${job.priority}</span>
            </div>
            <div style="font-size: 11px; color: #334155; margin-bottom: 3px;">
              <b>Status:</b> ${job.status.replace(/_/g, ' ')}
            </div>
            <div style="font-size: 11px; color: #334155; margin-bottom: 4px;">
              <b>Assigned:</b> ${job.assignedElectricianName || 'Unassigned'}
            </div>
            <div style="font-size: 10px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 4px;">
              📍 ${job.location.address}
            </div>
          </div>
        `;

        marker.bindPopup(popupContent);
        marker.on('click', () => {
          if (onSelectJob) onSelectJob(job);
        });

        markersLayer.addLayer(marker);
      });
    }
  }, [electricians, jobs, activeLayer, selectedElectricianId, selectedJobId, onSelectElectrician, onSelectJob]);

  return (
    <div className="relative rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-slate-100">
      {/* Top Banner: Mysuru Demo Label & Simulation Status */}
      <div className="absolute top-3 left-3 z-[1000] flex flex-wrap items-center gap-2">
        <div className={`backdrop-blur-md text-white text-xs px-3 py-1.5 rounded-lg shadow-md flex items-center gap-2 border ${
          isGpsSimulating
            ? 'bg-emerald-950/90 border-emerald-500/80'
            : 'bg-slate-900/90 border-slate-700'
        }`}>
          <Radio className={`w-3.5 h-3.5 ${isGpsSimulating ? 'text-emerald-400 animate-ping' : 'text-emerald-400'}`} />
          <span className="font-semibold tracking-wide text-[11px]">
            {isGpsSimulating
              ? 'SIMULATED GPS MOVEMENTS ACTIVE • MYSURU FLEET TELEMETRY'
              : 'SIMULATED DEMO LOCATIONS • MYSURU GRID TELEMETRY'}
          </span>
        </div>

        {/* Demo GPS Simulation Toggle Button */}
        <button
          onClick={() => setIsGpsSimulating(!isGpsSimulating)}
          className={`backdrop-blur-md text-xs px-3 py-1.5 rounded-lg shadow-md flex items-center gap-1.5 font-bold transition border ${
            isGpsSimulating
              ? 'bg-emerald-600 text-white border-emerald-500 shadow-emerald-500/30'
              : 'bg-white/95 text-slate-700 border-slate-200 hover:bg-slate-100'
          }`}
          title="Toggle periodic simulated GPS movements within Mysuru"
        >
          {isGpsSimulating ? (
            <>
              <Pause className="w-3.5 h-3.5" />
              <span>Simulating (3.5s)</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 text-blue-600" />
              <span>Start GPS Simulation</span>
            </>
          )}
        </button>
      </div>

      {/* Layer Filter Toolbar */}
      <div className="absolute top-3 right-3 z-[1000] bg-white/95 backdrop-blur-md rounded-lg shadow-md border border-slate-200 p-1 flex items-center gap-1">
        <button
          onClick={() => setActiveLayer('all')}
          className={`px-2.5 py-1 text-xs rounded font-medium flex items-center gap-1.5 transition ${
            activeLayer === 'all'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          All
        </button>
        <button
          onClick={() => setActiveLayer('techs')}
          className={`px-2.5 py-1 text-xs rounded font-medium flex items-center gap-1.5 transition ${
            activeLayer === 'techs'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          Technicians ({electricians.length})
        </button>
        <button
          onClick={() => setActiveLayer('jobs')}
          className={`px-2.5 py-1 text-xs rounded font-medium flex items-center gap-1.5 transition ${
            activeLayer === 'jobs'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Wrench className="w-3.5 h-3.5" />
          Jobs ({jobs.length})
        </button>
        <button
          onClick={() => setActiveLayer('emergency')}
          className={`px-2.5 py-1 text-xs rounded font-medium flex items-center gap-1.5 transition ${
            activeLayer === 'emergency'
              ? 'bg-red-600 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          Emergencies
        </button>
      </div>

      {/* Map Container */}
      <div ref={mapContainerRef} style={{ height, width: '100%' }} />

      {/* Bottom Map Legend */}
      <div className="absolute bottom-3 left-3 z-[1000] bg-white/95 backdrop-blur-md text-[11px] text-slate-600 px-3 py-1.5 rounded-lg shadow-md border border-slate-200 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
          <span>Available Tech</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
          <span>Busy Tech</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
          <span>En Route Tech</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-red-500"></span>
          <span>Emergency Job</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-blue-500"></span>
          <span>Standard Job</span>
        </div>
      </div>
    </div>
  );
};
