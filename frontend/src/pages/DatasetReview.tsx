import React, { useState, useEffect } from 'react';
import {
  Database,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Cpu,
  Activity,
  Layers,
  ShieldCheck,
  Sparkles
} from 'lucide-react';
import { datasetApi } from '../services/api';
import { useNotification } from '../context/NotificationContext';

interface ModelBenchmark {
  name: string;
  file: string;
  architecture: string;
  size: string;
  classes: string;
  primaryMetricLabel: string;
  primaryMetricValue: number;
  secondaryMetrics: string;
  role: string;
}

const MODEL_BENCHMARKS: ModelBenchmark[] = [
  {
    name: 'Custom Object Detector',
    file: 'ten_class_food_v1/best.pt',
    architecture: 'YOLOv8n (30 epochs, 640×640)',
    size: '6.21 MB',
    classes: '10 Produce Classes',
    primaryMetricLabel: 'mAP@50',
    primaryMetricValue: 87.08,
    secondaryMetrics: 'Precision 82.62% · Recall 80.99% · mAP@50-95 67.96%',
    role: 'Real-time bounding boxes & auto-crop',
  },
  {
    name: 'Webcam Food Classifier',
    file: 'webcam_food_candidate.pth',
    architecture: 'PyTorch MobileNetV2',
    size: '8.77 MB',
    classes: '10 Produce Classes',
    primaryMetricLabel: 'Test Accuracy',
    primaryMetricValue: 96.56,
    secondaryMetrics: 'Top F1: Strawberry 99.5%, Banana 99.4%, Carrot 98.2%',
    role: 'High-accuracy live produce verification',
  },
  {
    name: 'Freshness & Spoilage Model',
    file: 'freshness_classifier.pth',
    architecture: 'PyTorch MobileNetV2',
    size: '8.73 MB',
    classes: '2 Classes (Fresh / Rotten)',
    primaryMetricLabel: 'Test Accuracy',
    primaryMetricValue: 92.46,
    secondaryMetrics: 'Trained on 21,036 split images (70/15/15)',
    role: 'Spoilage detection & shelf-life estimation',
  },
  {
    name: 'Multi-Class Food & Rejection',
    file: 'food_classifier.pth',
    architecture: 'PyTorch MobileNetV2',
    size: '8.79 MB',
    classes: '15 Classes (Produce + Dairy + Unknown)',
    primaryMetricLabel: 'Test Accuracy',
    primaryMetricValue: 86.17,
    secondaryMetrics: 'Rejects non-food boxes (< 0.35 conf or unknown)',
    role: 'Ensemble crop refinement & false-positive filter',
  },
  {
    name: 'Packaged Dairy Classifier',
    file: 'dairy_classifier.pth',
    architecture: 'PyTorch MobileNetV2 + OCR',
    size: '8.74 MB',
    classes: '4 Classes (Cheese, Milk, Paneer, Yogurt)',
    primaryMetricLabel: 'Test Accuracy',
    primaryMetricValue: 65.28,
    secondaryMetrics: 'Paired with printed EXP / MFG OCR extraction',
    role: 'Packaged dairy recognition & date parsing',
  },
];

const DATASET_SPLITS = [
  {
    name: 'freshness_webcam_splits',
    train: '14,724',
    val: '3,156',
    test: '3,156',
    total: '21,036',
    ratio: '70 / 15 / 15',
  },
  {
    name: 'webcam_food_splits',
    train: '8,233',
    val: '1,761',
    test: '1,774',
    total: '11,768',
    ratio: '70 / 15 / 15',
  },
  {
    name: 'fruits_vegetables_10class_yolo',
    train: '1,426',
    val: '178',
    test: '178',
    total: '1,782',
    ratio: '80 / 10 / 10',
  },
];

export const DatasetReview: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [pendingImages, setPendingImages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiLatencyMs, setApiLatencyMs] = useState<number | null>(null);
  const { showToast } = useNotification();

  const loadData = async () => {
    try {
      setLoading(true);
      const start = performance.now();
      const [st, p] = await Promise.all([datasetApi.getStats(), datasetApi.getPending()]);
      setApiLatencyMs(Math.round(performance.now() - start));
      setStats(st);
      setPendingImages(p);
    } catch (err) {
      console.error(err);
      setApiLatencyMs(null);
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
    } catch {
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
            AI Model Diagnostics & Active Learning
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Verified model benchmarks, dataset splits (66,484 curated images), and user feedback moderation
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-700">
            <Activity className="w-3.5 h-3.5" />
            {apiLatencyMs !== null ? `Inference API Live · ${apiLatencyMs} ms` : loading ? 'Checking API...' : 'API Offline'}
          </span>
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Top KPI Summary Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Active Split Images</span>
          <span className="text-3xl font-black text-slate-900 mt-1 block">34,586</span>
          <span className="text-[11px] text-slate-400">From 66,484 total corpus</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
          <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider block">Best Produce Acc.</span>
          <span className="text-3xl font-black text-emerald-600 mt-1 block">96.56%</span>
          <span className="text-[11px] text-emerald-600 font-medium">MobileNetV2 (10-class)</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">YOLOv8n mAP@50</span>
          <span className="text-3xl font-black text-slate-900 mt-1 block">87.08%</span>
          <span className="text-[11px] text-slate-400">Freshness Acc: 92.46%</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-amber-200 shadow-soft">
          <span className="text-xs font-bold text-amber-700 uppercase tracking-wider block">Pending Review</span>
          <span className="text-3xl font-black text-amber-600 mt-1 block">{stats?.pending_count ?? 0}</span>
          <span className="text-[11px] text-amber-600 font-medium">Active learning queue</span>
        </div>
      </div>

      {/* Production Ensemble Pipeline Banner */}
      <div className="bg-white p-5 rounded-2xl border border-emerald-200/80 shadow-soft flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-bold text-emerald-700 uppercase tracking-wider">
            <Sparkles className="w-4 h-4" />
            Active Inference Pipeline (Production Config)
          </div>
          <p className="text-xs sm:text-sm text-slate-700">
            <strong>Stage 1:</strong> Custom YOLOv8n auto-crop (<code>conf=0.46</code>, <code>iou=0.45</code>, <code>imgsz=416</code>, <code>agnostic_nms=True</code>) →{' '}
            <strong>Stage 2:</strong> Weighted ensemble (<code>0.55 × YOLO + 0.45 × MobileNetV2</code>) →{' '}
            <strong>Stage 3:</strong> Non-food rejection (<code>&lt; 0.35</code> or <code>unknown</code>) + Freshness scoring.
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold shrink-0">
          <ShieldCheck className="w-4 h-4" />
          5 Models Verified
        </span>
      </div>

      {/* 5 Trained Models Benchmark Grid */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-emerald-600" />
            <div>
              <h2 className="text-sm font-bold text-slate-800">Trained Deep Learning Models</h2>
              <p className="text-xs text-slate-500">Lightweight edge-ready weights (~6–9 MB each) evaluated on held-out test splits</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {MODEL_BENCHMARKS.map((m) => (
            <div
              key={m.file}
              className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{m.name}</h3>
                  <p className="text-[11px] font-mono text-slate-500">{m.file} · {m.size}</p>
                </div>
                <span className="text-xs font-black px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-800 shrink-0">
                  {m.primaryMetricLabel}: {m.primaryMetricValue}%
                </span>
              </div>

              <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald-600"
                  style={{ width: `${Math.min(100, m.primaryMetricValue)}%` }}
                />
              </div>

              <div className="text-xs text-slate-600 space-y-0.5">
                <p><strong>Architecture:</strong> {m.architecture} · {m.classes}</p>
                <p className="text-[11px] text-slate-500">{m.secondaryMetrics}</p>
                <p className="text-[11px] text-emerald-700 font-medium">Role: {m.role}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Dataset Splits Table */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <Layers className="w-5 h-5 text-emerald-600" />
          <div>
            <h2 className="text-sm font-bold text-slate-800">Verified Dataset Splits</h2>
            <p className="text-xs text-slate-500">Fixed test splits never used during training for unbiased evaluation</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 pr-4">Dataset Split</th>
                <th className="py-2.5 px-3">Train</th>
                <th className="py-2.5 px-3">Validation</th>
                <th className="py-2.5 px-3">Test (Fixed)</th>
                <th className="py-2.5 px-3">Total</th>
                <th className="py-2.5 pl-3">Ratio</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {DATASET_SPLITS.map((row) => (
                <tr key={row.name}>
                  <td className="py-2.5 pr-4 font-mono font-semibold text-slate-800">{row.name}</td>
                  <td className="py-2.5 px-3 text-slate-700">{row.train}</td>
                  <td className="py-2.5 px-3 text-slate-700">{row.val}</td>
                  <td className="py-2.5 px-3 font-semibold text-emerald-700">{row.test}</td>
                  <td className="py-2.5 px-3 font-bold text-slate-900">{row.total}</td>
                  <td className="py-2.5 pl-3 text-slate-500">{row.ratio}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending User Corrections Moderation Queue */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-800">
              Pending Corrections Review Queue (Human-in-the-Loop)
            </h3>
            <p className="text-xs text-slate-500">
              Approve user-corrected scans into the training split or reject poor quality uploads
            </p>
          </div>
          <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            {pendingImages.length} awaiting
          </span>
        </div>

        {pendingImages.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
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
    </div>
  );
};