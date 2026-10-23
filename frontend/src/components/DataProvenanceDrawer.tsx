import React from "react";
import type { AdminSourceItem } from "../types";

interface DataProvenanceDrawerProps {
  source: AdminSourceItem | null;
  onClose: () => void;
  onRefresh?: (sourceId: string) => void;
  isRefreshing?: boolean;
}

export const DataProvenanceDrawer: React.FC<DataProvenanceDrawerProps> = ({
  source,
  onClose,
  onRefresh,
  isRefreshing = false,
}) => {
  if (!source) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case "LIVE":
      case "ONLINE":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
      case "FRESH":
        return "bg-blue-500/20 text-blue-300 border-blue-500/30";
      case "STANDBY":
        return "bg-amber-500/20 text-amber-300 border-amber-500/30";
      case "SIMULATED":
        return "bg-purple-500/20 text-purple-300 border-purple-500/30";
      case "STATIC":
        return "bg-slate-500/20 text-slate-300 border-slate-500/30";
      case "STALE":
      case "UNAVAILABLE":
      default:
        return "bg-rose-500/20 text-rose-300 border-rose-500/30";
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="provenance-drawer-title"
    >
      <div
        className="w-full max-w-xl h-full bg-slate-900 border-l border-slate-800 shadow-2xl p-6 overflow-y-auto flex flex-col justify-between"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          {/* Header */}
          <div className="flex items-start justify-between border-b border-slate-800 pb-4 mb-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
                  {source.category}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full border font-medium ${getStatusColor(
                    source.status
                  )}`}
                >
                  {source.status}
                </span>
              </div>
              <h2
                id="provenance-drawer-title"
                className="text-xl font-bold text-white tracking-tight"
              >
                {source.name}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              aria-label="Close provenance drawer"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Core Metadata Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Source Identifier</span>
              <code className="text-xs font-mono text-cyan-300">{source.id}</code>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Coverage Scope</span>
              <span className="text-xs text-slate-200">{source.coverage_scope || source.coverage}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Freshness / Age</span>
              <span className="text-xs text-slate-200 font-medium">{source.age}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block mb-0.5">Last Sync Timestamp</span>
              <span className="text-xs font-mono text-slate-300">
                {source.last_updated ? new Date(source.last_updated).toLocaleString() : "Not Synced"}
              </span>
            </div>
            <div className="col-span-2">
              <span className="text-xs text-slate-400 block mb-0.5">Cryptographic Version Hash</span>
              <code className="text-xs font-mono text-emerald-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800 block truncate">
                {source.version_hash}
              </code>
            </div>
          </div>

          {/* Truth-in-Advertising & Data Provenance */}
          <div className="mb-6 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Data Provenance & Ingestion Protocol
              </h3>
              <p className="text-sm text-slate-300 bg-slate-800/40 p-3 rounded-lg border border-slate-800 leading-relaxed">
                {source.provenance}
              </p>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-amber-400 mb-1 flex items-center gap-1.5">
                <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Operational Boundaries & Disclaimers
              </h3>
              <p className="text-xs text-amber-200/90 bg-amber-950/30 p-3 rounded-lg border border-amber-900/40 leading-relaxed">
                {source.disclaimer}
              </p>
            </div>

            {source.error_message && (
              <div className="bg-rose-950/30 border border-rose-900/40 p-3 rounded-lg">
                <span className="text-xs font-semibold text-rose-400 block mb-1">
                  ⚠️ Status Diagnosis / Alert
                </span>
                <p className="text-xs text-rose-200">{source.error_message}</p>
              </div>
            )}
          </div>
        </div>

        {/* Action footer */}
        <div className="border-t border-slate-800 pt-4 flex items-center justify-between gap-3">
          <div className="text-xs text-slate-500">
            RaahSetu SIH26002 • Sovereign Logistics Resilience
          </div>
          <div className="flex items-center gap-2">
            {source.is_refreshable && onRefresh && (
              <button
                onClick={() => onRefresh(source.id)}
                disabled={isRefreshing}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 text-white text-xs font-semibold rounded-lg shadow transition flex items-center gap-1.5"
              >
                <svg
                  className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                {isRefreshing ? "Purging Cache..." : "Refresh Cache & Poll"}
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
