import { FiClock, FiMapPin, FiChevronRight } from "react-icons/fi";

const SEVERITY_CONFIG = {
    critical: {
        color: "text-rose-400",
        border: "border-l-rose-500",
        label: "Critical",
    },
    warning: {
        color: "text-amber-400",
        border: "border-l-amber-500",
        label: "Warning",
    },
    info: {
        color: "text-blue-400",
        border: "border-l-blue-500",
        label: "Info",
    },
};

export default function AlertItem({
    severity = "info",
    title,
    description,
    location,
    time,
    isAcknowledged = false,
    snapshot
}) {
    const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;

    return (
        <div className={`bg-card/50 border border-slate-800 rounded-lg p-4 mb-3 border-l-4 ${config.border} hover:bg-slate-800/80 transition-colors cursor-pointer group`}>
            <div className="flex justify-between items-start">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-bold uppercase tracking-wider ${config.color}`}>
                            {config.label}
                        </span>
                        {isAcknowledged && (
                            <span className="text-xs text-slate-500 flex items-center gap-1">
                                • Acknowledged
                            </span>
                        )}
                    </div>

                    <h4 className="text-white font-medium mb-1 group-hover:text-accent transition-colors">
                        {title}
                    </h4>

                    <p className="text-slate-400 text-sm mb-3 line-clamp-2">
                        {description}
                    </p>

                    <div className="flex items-center gap-4 text-xs text-slate-500">
                        {location && (
                            <div className="flex items-center gap-1">
                                <FiMapPin /> {location}
                            </div>
                        )}
                        <div className="flex items-center gap-1">
                            <FiClock /> {time}
                        </div>
                    </div>

                    {/* Snapshot Display */}
                    {snapshot && (
                        <div className="mt-2 rounded-md overflow-hidden border border-slate-700 w-24 h-16 bg-black">
                            <img
                                src={snapshot.startsWith('http') ? snapshot : `${process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || "http://localhost:8000"}${snapshot}`}
                                alt="Alert Snapshot"
                                className="w-full h-full object-cover"
                            />
                        </div>
                    )}
                </div>

                <div className="ml-4 text-slate-600 group-hover:text-white transition-colors self-center">
                    <FiChevronRight size={20} />
                </div>
            </div>
        </div>
    );
}
