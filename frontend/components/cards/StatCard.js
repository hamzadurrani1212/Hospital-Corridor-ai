import { FiMoreHorizontal } from "react-icons/fi";

export default function StatCard({ title, value, subtext, type = "neutral", headerAction }) {
  // Determine color for the trend/subtext based on type
  let subtextColor = "text-slate-400";
  if (type === "positive") subtextColor = "text-emerald-400";
  if (type === "negative") subtextColor = "text-rose-400";

  return (
    <div className="bg-card border border-slate-800 rounded-xl p-5 flex flex-col justify-between h-full hover:border-slate-700 transition-colors">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
        {headerAction || (
          <button className="text-slate-500 hover:text-white transition-colors">
            {/* Using a dot if needed, or just standard icon */}
          </button>
        )}
      </div>

      <div>
        <div className="text-2xl font-semibold text-white mb-1">{value}</div>
        {subtext && <p className={`text-xs ${subtextColor}`}>{subtext}</p>}
      </div>
    </div>
  );
}
