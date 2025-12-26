"use client";

export default function AlertsTable({ alerts }) {
  const getRowStyle = (alert) => {
    if (alert.type === "AGGRESSIVE_BEHAVIOR" || alert.severity === "critical") {
      return "bg-red-50 border-l-4 border-red-500 animate-pulse";
    }
    return "hover:bg-gray-50 border-l-4 border-transparent";
  };

  const getStatusStyle = (status) => {
    switch (status?.toLowerCase()) {
      case "critical":
        return "text-red-700 bg-red-100 px-2 py-1 rounded-full uppercase text-xs font-bold";
      case "high":
        return "text-orange-700 bg-orange-100 px-2 py-1 rounded-full uppercase text-xs font-bold";
      default:
        return "text-green-700 bg-green-100 px-2 py-1 rounded-full uppercase text-xs font-bold";
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return "---";
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString();
  };

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-100">
      <div className="bg-gradient-to-r from-gray-800 to-gray-900 px-6 py-4 flex justify-between items-center">
        <h2 className="text-white font-semibold flex items-center gap-2">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-ping"></span>
          REAL-TIME SECURITY EVENTS
        </h2>
        <span className="text-gray-400 text-xs font-mono uppercase tracking-widest">
          Live Feed Updated
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 border-b text-xs font-bold text-gray-500 uppercase tracking-wider">Time</th>
              <th className="px-6 py-3 border-b text-xs font-bold text-gray-500 uppercase tracking-wider">Camera</th>
              <th className="px-6 py-3 border-b text-xs font-bold text-gray-500 uppercase tracking-wider">Event Type</th>
              <th className="px-6 py-3 border-b text-xs font-bold text-gray-500 uppercase tracking-wider">Resolution</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {alerts.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-10 text-center text-gray-400 italic">
                  No security events detected recently
                </td>
              </tr>
            ) : (
              alerts.map((alert, idx) => (
                <tr key={idx} className={`${getRowStyle(alert)} transition-all duration-300`}>
                  <td className="px-6 py-4 text-sm text-gray-600 font-medium">
                    {formatTimestamp(alert.timestamp)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 font-bold">
                    {alert.location || alert.camera || "MAIN_CAM"}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className={`text-sm font-black ${alert.type === "AGGRESSIVE_BEHAVIOR" ? "text-red-600" : "text-gray-800"
                        }`}>
                        {alert.title || alert.type}
                      </span>
                      <span className="text-xs text-gray-500 truncate max-w-xs">
                        {alert.description}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={getStatusStyle(alert.severity || alert.status)}>
                      {alert.severity || alert.status || "Normal"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { background-color: rgba(254, 226, 226, 0.5); }
          50% { background-color: rgba(254, 226, 226, 1); }
        }
        .animate-pulse {
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
      `}</style>
    </div>
  );
}
