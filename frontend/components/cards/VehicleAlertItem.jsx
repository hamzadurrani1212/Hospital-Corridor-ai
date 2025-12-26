import React from 'react';
import { FiTruck, FiActivity, FiMapPin, FiClock, FiAlertCircle } from 'react-icons/fi';
import { RiCarLine, RiMotorbikeLine, RiBusLine } from 'react-icons/ri';

const VEHICLE_ICONS = {
    car: <RiCarLine size={24} />,
    van: <RiCarLine size={24} />, // Could use a different icon if available
    truck: <FiTruck size={24} />,
    bus: <RiBusLine size={24} />,
    motorcycle: <RiMotorbikeLine size={24} />,
    ambulance: <FiActivity size={24} className="text-rose-500" />
};

export default function VehicleAlertItem({
    id,
    vehicleType = "car",
    plateNumber = "Unknown",
    status = "moving", // moving, parked, unauthorized
    location = "Entrance",
    camera = "CAM01",
    time = "Just now",
    severity = "warning",
    snapshot,
    isAcknowledged = false,
    onAcknowledge
}) {
    const isUnauthorized = status === 'unauthorized' || severity === 'critical';

    return (
        <div className={`group relative bg-slate-900/40 border ${isUnauthorized && !isAcknowledged ? 'border-rose-500/30' : isAcknowledged ? 'border-emerald-500/20' : 'border-slate-800'} rounded-xl p-4 mb-4 hover:bg-slate-800/60 transition-all duration-300 backdrop-blur-sm`}>
            {isUnauthorized && !isAcknowledged && (
                <div className="absolute -top-2 -right-2 bg-rose-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-lg animate-pulse">
                    UNAUTHORIZED
                </div>
            )}

            {isAcknowledged && (
                <div className="absolute -top-2 -right-2 bg-emerald-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-lg">
                    RESOLVED
                </div>
            )}

            <div className="flex gap-4">
                {/* Vehicle Icon / Thumbnail Column */}
                <div className="flex-shrink-0">
                    <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${isUnauthorized && !isAcknowledged ? 'bg-rose-500/10 text-rose-400' : isAcknowledged ? 'bg-emerald-500/10 text-emerald-400' : 'bg-accent/10 text-accent'} border border-white/5`}>
                        {VEHICLE_ICONS[vehicleType.toLowerCase()] || <RiCarLine size={24} />}
                    </div>
                </div>

                {/* Info Column */}
                <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start mb-1">
                        <div>
                            <h4 className="text-white font-semibold text-base flex items-center gap-2">
                                {vehicleType.toUpperCase()} <span className="text-slate-500 text-xs font-mono">[{plateNumber}]</span>
                            </h4>
                            <p className="text-slate-400 text-xs flex items-center gap-1 mt-0.5">
                                <span className="text-accent">{camera}</span> • {status.toUpperCase()}
                            </p>
                        </div>
                        <div className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${status === 'moving' ? 'bg-emerald-500/10 text-emerald-400' :
                            status === 'parked' ? 'bg-amber-500/10 text-amber-400' :
                                'bg-rose-500/10 text-rose-400'
                            }`}>
                            {status}
                        </div>
                    </div>

                    <div className="flex items-center gap-4 mt-3 text-slate-500 text-[11px]">
                        <div className="flex items-center gap-1">
                            <FiMapPin size={12} className="text-accent" />
                            {location}
                        </div>
                        <div className="flex items-center gap-1">
                            <FiClock size={12} />
                            {time}
                        </div>
                        {!isAcknowledged && onAcknowledge && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onAcknowledge(); }}
                                className="ml-auto text-accent hover:text-white transition-colors font-bold uppercase tracking-tighter"
                            >
                                Acknowledge
                            </button>
                        )}
                    </div>
                </div>

                {/* Snapshot Preview (Right side) */}
                {snapshot && (
                    <div className="hidden sm:block flex-shrink-0 w-24 h-16 rounded-lg overflow-hidden border border-slate-700 bg-black group-hover:border-accent/50 transition-colors">
                        <img
                            src={snapshot.startsWith('http') ? snapshot : `${process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || "http://localhost:8000"}${snapshot}`}
                            alt="Vehicle Snapshot"
                            className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                        />
                    </div>
                )}
            </div>

            {/* Interactive Hover Overlay */}
            <div className="absolute inset-0 rounded-xl border-accent/0 border-2 group-hover:border-accent/10 pointer-events-none transition-all duration-300"></div>
        </div>
    );
}

