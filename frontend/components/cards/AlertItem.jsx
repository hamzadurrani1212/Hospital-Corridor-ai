import { FiClock, FiMapPin, FiChevronRight } from "react-icons/fi";
import VehicleAlertItem from "./VehicleAlertItem";
import AggressionAlertItem from "./AggressionAlertItem";

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
    id,
    type,
    severity = "info",
    title,
    description,
    location,
    time,
    isAcknowledged = false,
    snapshot,
    onAcknowledge,
    ...rest
}) {
    // 1. Vehicle Alerts Routing
    if (type?.startsWith("VEHICLE_") || type?.includes("PARKING") || type?.includes("VEHICLE") || type?.includes("SPEED")) {
        return (
            <VehicleAlertItem
                id={id}
                vehicleType={rest.vehicle_type || "Vehicle"}
                plateNumber={rest.plate_number || "REQ-SCAN"}
                status={type === "UNAUTHORIZED_PARKING" ? "unauthorized" : rest.status || "moving"}
                location={location}
                camera={rest.camera || "CAM01"}
                time={time}
                severity={severity}
                snapshot={snapshot}
                isAcknowledged={isAcknowledged}
                onAcknowledge={onAcknowledge}
            />
        );
    }

    // 2. Aggression Alerts Routing
    if (type === "AGGRESSIVE_BEHAVIOR") {
        return (
            <AggressionAlertItem
                id={id}
                type={title}
                severity={severity}
                description={description}
                location={location}
                personCount={rest.behavior_data?.person_count || 2}
                camera={rest.camera || "CAM-SEC"}
                time={time}
                snapshot={snapshot}
                isAcknowledged={isAcknowledged}
                onAcknowledge={onAcknowledge}
            />
        );
    }

    // 3. Fallback for Standard Alerts (Loitering, Restricted Area, etc.)
    const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;

    return (
        <div className={`bg-card/50 border border-slate-800 rounded-lg p-4 mb-3 border-l-4 ${config.border} hover:bg-slate-800/80 transition-colors cursor-pointer group`}>
            <div className="flex justify-between items-start">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-bold uppercase tracking-wider ${config.color}`}>
                            {config.label}
                        </span>
                        {(type === "AGGRESSIVE_BEHAVIOR" || type === "FIGHT_DETECTED" || type?.startsWith("VEHICLE")) && (
                            <span className="bg-rose-500/20 text-rose-500 text-[10px] font-black uppercase px-2 py-0.5 rounded-full border border-rose-500/30 animate-pulse">
                                Priority
                            </span>
                        )}
                        {isAcknowledged && (
                            <span className="text-xs text-slate-500 flex items-center gap-1">
                                • Acknowledged
                            </span>
                        )}
                    </div>

                    <div className="flex items-center gap-2 mb-1">
                        <h4 className="text-white font-medium group-hover:text-accent transition-colors">
                            {title}
                        </h4>
                        {rest.person_role && rest.person_role !== "Unknown" && (
                            <span className="bg-slate-700/50 text-slate-300 text-[10px] px-1.5 py-0.5 rounded border border-slate-600">
                                {rest.person_role}
                            </span>
                        )}
                    </div>

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

                <div className="ml-4 flex flex-col gap-2 self-center">
                    {!isAcknowledged && onAcknowledge && (
                        <button
                            onClick={(e) => { e.stopPropagation(); onAcknowledge(); }}
                            className="bg-accent/10 border border-accent/30 text-accent text-[10px] font-bold uppercase py-1 px-3 rounded hover:bg-accent hover:text-white transition-all whitespace-nowrap"
                        >
                            Acknowledge
                        </button>
                    )}
                    <div className="text-slate-600 group-hover:text-white transition-colors self-center">
                        <FiChevronRight size={20} />
                    </div>
                </div>
            </div>
        </div>
    );
}
