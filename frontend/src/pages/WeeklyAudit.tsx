import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Upload,
  CalendarCheck,
  Check,
  RotateCcw,
  Sparkles,
  Layers,
  ArrowRight
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { auditApi } from '../services/api';
import { AuditSession } from '../types';
import { useNotification } from '../context/NotificationContext';

export const WeeklyAudit: React.FC = () => {
  const [sessions, setSessions] = useState<AuditSession[]>([]);
  const [currentSession, setCurrentSession] = useState<AuditSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [filePreviews, setFilePreviews] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useNotification();

  const loadSessions = async () => {
    try {
      const data = await auditApi.getSessions();
      setSessions(data);
      if (data.length > 0 && !currentSession) {
        setCurrentSession(data[0]);
      }
    } catch (err) {
      console.error('Failed to load audit sessions:', err);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleFilesSelect = (files: FileList | null) => {
    if (!files) return;
    const fileArr = Array.from(files).slice(0, 5);
    setSelectedFiles(fileArr);
    setFilePreviews(fileArr.map((f) => URL.createObjectURL(f)));
  };

  const handleRunAudit = async () => {
    if (selectedFiles.length === 0) {
      showToast('warning', 'Please select at least 1 fridge photo.');
      return;
    }
    setLoading(true);
    try {
      const res = await auditApi.submitAudit(selectedFiles);
      setCurrentSession(res);
      setSessions((prev) => [res, ...prev]);
      setSelectedFiles([]);
      setFilePreviews([]);
      confetti({ particleCount: 70, spread: 60, origin: { y: 0.6 } });
      showToast('success', `Audit complete: ${res.matched_count} matched, ${res.missing_count} missing.`, 'Audit Processed');
    } catch (err) {
      console.error(err);
      showToast('error', 'Audit processing failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResolveMissing = async (resultId: number, resolution: 'marked_used' | 'still_here') => {
    try {
      await auditApi.resolveMissing(resultId, resolution);
      showToast('success', resolution === 'marked_used' ? 'Marked as consumed' : 'Confirmed still in fridge');
      
      // Update local state
      if (currentSession) {
        const updatedResults = currentSession.results.map((r) =>
          r.id === resultId ? { ...r, resolution } : r
        );
        setCurrentSession({ ...currentSession, results: updatedResults });
      }
    } catch (err) {
      showToast('error', 'Failed to resolve item');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <CalendarCheck className="w-6 h-6 text-emerald-600" />
          Weekly Fridge Audit
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
          Sunday routine: Upload 2–5 photos from different angles to cross-verify inventory and auto-detect missing items
        </p>
      </div>

      {/* Upload & Run Audit Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Camera className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-800">
                Capture Refrigerator Shelves
              </h2>
              <p className="text-xs text-slate-500">
                Take photos of top, middle, and bottom shelves plus door racks
              </p>
            </div>
          </div>
          <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
            Sunday Scheduled
          </span>
        </div>

        {/* Dropzone */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-300 hover:border-emerald-500 rounded-2xl p-6 text-center cursor-pointer transition-all bg-slate-50/50 hover:bg-emerald-50/20"
        >
          <input
            type="file"
            ref={fileInputRef}
            multiple
            accept="image/*"
            className="hidden"
            onChange={(e) => handleFilesSelect(e.target.files)}
          />

          {filePreviews.length > 0 ? (
            <div>
              <p className="text-xs font-bold text-emerald-700 mb-3">
                {filePreviews.length} photo(s) ready for multi-object audit analysis:
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                {filePreviews.map((src, i) => (
                  <img
                    key={i}
                    src={src}
                    alt={`Preview ${i}`}
                    className="w-24 h-24 object-cover rounded-xl border border-slate-200 shadow-sm"
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-slate-400" />
              <p className="text-sm font-bold text-slate-800">
                Select 2–5 angle photos of your fridge
              </p>
              <p className="text-xs text-slate-400">
                JPG, PNG, WebP supported. Mobile camera captures recommended.
              </p>
            </div>
          )}
        </div>

        {selectedFiles.length > 0 && (
          <div className="flex justify-end">
            <button
              onClick={handleRunAudit}
              disabled={loading}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs sm:text-sm px-6 py-2.5 rounded-xl shadow-md shadow-emerald-500/20 transition-all flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              {loading ? 'Running Computer Vision Audit...' : 'Execute Audit & Match Inventory'}
            </button>
          </div>
        )}
      </div>

      {/* Audit Results Panel */}
      {currentSession && (
        <div className="space-y-5 animate-in fade-in duration-300">
          {/* Summary Stat bar */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-2xl">
              <span className="text-xs font-bold text-emerald-700 block">Matched in Inventory</span>
              <span className="text-2xl font-black text-emerald-800">{currentSession.matched_count}</span>
            </div>
            <div className="bg-amber-50 border border-amber-200 p-4 rounded-2xl">
              <span className="text-xs font-bold text-amber-700 block">Items Not Seen (Missing)</span>
              <span className="text-2xl font-black text-amber-800">{currentSession.missing_count}</span>
            </div>
            <div className="bg-blue-50 border border-blue-200 p-4 rounded-2xl">
              <span className="text-xs font-bold text-blue-700 block">Unknown Items Found</span>
              <span className="text-2xl font-black text-blue-800">{currentSession.unknown_count}</span>
            </div>
          </div>

          {/* Missing Items Action List */}
          {currentSession.results.filter((r) => r.status === 'missing').length > 0 && (
            <div className="bg-white p-6 rounded-2xl border border-amber-200 shadow-soft">
              <h3 className="text-sm font-bold text-amber-900 mb-1 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Missing Items Verification
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                These items exist in your inventory list but were not visible in the audit photos.
              </p>

              <div className="space-y-3">
                {currentSession.results
                  .filter((r) => r.status === 'missing')
                  .map((item) => (
                    <div
                      key={item.id}
                      className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div>
                        <h4 className="font-bold text-xs sm:text-sm text-amber-950">
                          {item.detected_name} was not seen. Did you consume or discard it?
                        </h4>
                        <p className="text-[11px] text-amber-800/80">
                          Alert notification sent to phone. Resolve status below:
                        </p>
                      </div>

                      {item.resolution ? (
                        <span className="text-xs font-bold px-3 py-1 rounded-full bg-white text-emerald-700 border border-emerald-200">
                          {item.resolution === 'marked_used' ? '✓ Marked Consumed' : '✓ Still in Fridge'}
                        </span>
                      ) : (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleResolveMissing(item.id, 'marked_used')}
                            className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 transition-colors shadow-xs"
                          >
                            Mark as Used
                          </button>
                          <button
                            onClick={() => handleResolveMissing(item.id, 'still_here')}
                            className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-100 transition-colors"
                          >
                            Still here
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Matched Items List */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
            <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Verified & Matched Items
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {currentSession.results
                .filter((r) => r.status === 'matched')
                .map((m) => (
                  <div
                    key={m.id}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between"
                  >
                    <div>
                      <p className="text-xs font-bold text-slate-800">{m.detected_name}</p>
                      <p className="text-[11px] text-slate-400">Freshness: {m.detected_freshness}</p>
                    </div>
                    <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                      Verified
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
