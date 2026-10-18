import React, { useState, useEffect } from 'react';
import {
  Database,
  CheckCircle2,
  XCircle,
  Sparkles,
  Layers,
  RefreshCw,
  FolderGit2,
  Play,
  RotateCcw
} from 'lucide-react';
import { datasetApi } from '../services/api';
import { useNotification } from '../context/NotificationContext';

export const DatasetReview: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [pendingImages, setPendingImages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const { showToast } = useNotification();

  const loadData = async () => {
    try {
      setLoading(true);
      const [st, p] = await Promise.all([datasetApi.getStats(), datasetApi.getPending()]);
      setStats(st);
      setPendingImages(p);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleVerify = async (id: number, action: 'approve' | 'reject') => {
    try {
      await datasetApi.verifyImage(id, action, 'train');
      showToast('success', action === 'approve' ? 'Approved into training split' : 'Rejected and removed');
      loadData();
    } catch (err) {
      showToast('error', 'Action failed');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Database className="w-6 h-6 text-emerald-600" />
            Dataset Pipeline & Active Learning Retrain
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Admin console for moderation of user-corrected uploads and active learning retraining
          </p>
        </div>

        <button
          onClick={loadData}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs self-start sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
          Refresh Stats
        </button>
      </div>

      {/* Dataset Splits Breakdown */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Train Split (70%)</span>
            <span className="text-3xl font-black text-slate-900 mt-1 block">{stats.splits?.train || 25}</span>
            <span className="text-[11px] text-slate-400">Transfer learning pool</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Val Split (15%)</span>
            <span className="text-3xl font-black text-slate-900 mt-1 block">{stats.splits?.val || 5}</span>
            <span className="text-[11px] text-slate-400">Early stopping checks</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
            <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider block">Fixed Test Split (15%)</span>
            <span className="text-3xl font-black text-emerald-600 mt-1 block">{stats.splits?.test || 6}</span>
            <span className="text-[11px] text-emerald-600 font-medium">Never trained on (Benchmark)</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-amber-200 shadow-soft">
            <span className="text-xs font-bold text-amber-700 uppercase tracking-wider block">Pending Review</span>
            <span className="text-3xl font-black text-amber-600 mt-1 block">{stats.pending_count || 0}</span>
            <span className="text-[11px] text-amber-600 font-medium">User corrections</span>
          </div>
        </div>
      )}

      {/* Pending User Corrections Moderation Queue */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-800">
              Pending Corrections Review Queue
            </h3>
            <p className="text-xs text-slate-500">
              Approve verified images into the training pool or reject poor quality uploads
            </p>
          </div>
          <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            {pendingImages.length} awaiting
          </span>
        </div>

        {pendingImages.length === 0 ? (
          <div className="text-center py-10 text-slate-400">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-600">All uploaded images are reviewed!</p>
            <p className="text-[11px] text-slate-400 mt-0.5">When users correct predictions on the AI Scan page, they appear here.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {pendingImages.map((img) => (
              <div
                key={img.id}
                className="p-3 rounded-xl border border-slate-200 bg-slate-50 space-y-2.5 flex flex-col justify-between"
              >
                <div>
                  <img
                    src={img.path}
                    alt="Upload"
                    className="w-full h-32 object-cover rounded-lg bg-white mb-2"
                  />
                  <div className="text-xs">
                    <p className="font-bold text-slate-900">
                      Label: {img.verified_label || img.predicted_label}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Stage: <strong className="text-emerald-700">{img.verified_freshness || img.predicted_freshness}</strong>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-slate-200/60">
                  <button
                    onClick={() => handleVerify(img.id, 'approve')}
                    className="flex-1 py-1.5 rounded-lg bg-emerald-600 text-white font-bold text-xs hover:bg-emerald-700 transition-colors flex items-center justify-center gap-1 shadow-xs"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" /> Approve
                  </button>
                  <button
                    onClick={() => handleVerify(img.id, 'reject')}
                    className="flex-1 py-1.5 rounded-lg bg-white border border-slate-200 text-rose-600 font-semibold text-xs hover:bg-rose-50 transition-colors flex items-center justify-center gap-1"
                  >
                    <XCircle className="w-3.5 h-3.5" /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Target Classes & Architecture Overview */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
        <h3 className="text-sm font-bold text-slate-800 mb-2">9 Supported Produce Items & 4 Freshness Stages</h3>
        <p className="text-xs text-slate-500 mb-4">
          Transfer learning architecture: PyTorch MobileNetV2 with 36 compound classes (Item × Freshness).
        </p>
        <div className="flex flex-wrap gap-2">
          {['Apple', 'Strawberry', 'Lychee', 'Banana', 'Capsicum', 'Green Chilli', 'Coriander', 'Tomato', 'Carrot'].map((item) => (
            <span key={item} className="px-3 py-1 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold">
              {item}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
