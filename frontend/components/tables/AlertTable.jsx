"use client";

export default function AlertsTable({ alerts }) {
  return (
    <div className="card">
      <div className="card-header">Recent Alerts</div>
      <div className="card-body overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="px-3 py-2 border-b">Time</th>
              <th className="px-3 py-2 border-b">Camera</th>
              <th className="px-3 py-2 border-b">Type</th>
              <th className="px-3 py-2 border-b">Status</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-3 py-2 border-b">{alert.time}</td>
                <td className="px-3 py-2 border-b">{alert.camera}</td>
                <td className="px-3 py-2 border-b">{alert.type}</td>
                <td className={`px-3 py-2 border-b font-medium ${
                  alert.status === "critical" ? "text-red-600" : "text-green-600"
                }`}>{alert.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
