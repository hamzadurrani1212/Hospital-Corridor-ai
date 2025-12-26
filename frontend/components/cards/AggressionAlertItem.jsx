import React from 'react';
import { FiUsers, FiAlertTriangle, FiMapPin, FiClock, FiVideo } from 'react-icons/fi';
import { GiPunch } from 'react-icons/gi';

export default function AggressionAlertItem({
    id,
    type = "Physical Altercation",
    severity = "critical",
    description,
    location = "Main Corridor",
    personCount = 2,
    camera = "CAM01",
    time = "Just now",
    snapshot,
    isAcknowledged = false,
    onAcknowledge
}) {
    const isCritical = severity === 'critical';

    return (
        <div className={`relative overflow-hidden bg-slate-900/60 border-l-4 ${isCritical ? 'border-l-rose-600' : 'border-l-amber-500'} border border-slate-800 rounded-xl p-5 mb-4 shadow-2xl backdrop-blur-md group hover:border-slate-700 transition-all`}>
            {/* Background Pulse for Critical */}
            {isCritical && !isAcknowledged && (
                <div className="absolute inset-0 bg-rose-500/5 animate-pulse pointer-events-none"></div>
            )}

            <div className="flex justify-between items-start">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                        <span className={`flex items-center gap-1 text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-sm ${isCritical ? 'bg-rose-600 text-white' : 'bg-amber-500 text-black'
                            }`}>
                            <FiAlertTriangle size={12} /> {severity}
                        </span>
                        <span className="text-slate-500 text-xs font-mono">{camera}</span>
                        {isAcknowledged && (
                            <span className="text-emerald-500 text-[10px] font-bold uppercase tracking-wider ml-2">✓ Acknowledged</span>
                        )}
                    </div>

                    <h3 className="text-white text-lg font-bold mb-1 group-hover:text-rose-400 transition-colors">
                        {type}
                    </h3>

                    <p className="text-slate-400 text-sm mb-4 line-clamp-2 italic">
                        {description || "Active aggressive behavior detected via motion patterns."}
                    </p>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex items-center gap-2 text-slate-300 text-xs bg-slate-800/50 px-3 py-1.5 rounded-lg border border-white/5">
                            <FiUsers className="text-accent" />
                            <span>{personCount} {personCount === 1 ? 'Person' : 'Persons'} involved</span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-300 text-xs bg-slate-800/50 px-3 py-1.5 rounded-lg border border-white/5">
                            <FiMapPin className="text-accent" />
                            <span>{location}</span>
                        </div>
                    </div>
                </div>

                {/* Snapshot / Visual Column */}
                <div className="ml-6 flex flex-col gap-2">
                    {snapshot ? (
                        <div className="w-32 h-24 rounded-xl overflow-hidden border-2 border-slate-800 shadow-lg relative group-hover:border-rose-500/50 transition-all">
                            <img
                                src={snapshot.startsWith('http') ? snapshot : `${process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || "http://localhost:8000"}${snapshot}`}
                                alt="Incident Snapshot"
                                className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent flex items-end justify-center pb-1">
                                <span className="text-[9px] text-white/70 flex items-center gap-1">
                                    <FiClock size={10} /> {time}
                                </span>
                            </div>
                        </div>
                    ) : (
                        <div className="w-32 h-24 rounded-xl bg-slate-800 flex items-center justify-center border border-white/5">
                            <FiVideo size={24} className="text-slate-600" />
                        </div>
                    )}

                    {!isAcknowledged && onAcknowledge ? (
                        <button
                            onClick={(e) => { e.stopPropagation(); onAcknowledge(); }}
                            className="text-[10px] text-rose-400 font-bold uppercase hover:text-white transition-colors flex items-center justify-center gap-1 bg-rose-500/10 py-1.5 rounded-lg border border-rose-500/20"
                        >
                            Acknowledge Alert
                        </button>
                    ) : (
                        <button className="text-[10px] text-slate-400 font-bold uppercase transition-colors flex items-center justify-center gap-1 bg-slate-800/50 py-1.5 rounded-lg border border-white/5 cursor-default">
                            Response Logged
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

