import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Milk,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Layers,
  Calendar,
  RotateCcw,
  PlusCircle,
  Info,
  ShieldCheck,
  PackageCheck
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { aiApi, foodsApi, zonesApi } from '../services/api';
import { DairyPredictionResponse, Zone } from '../types';
import { useNotification } from '../context/NotificationContext';

export const DairyRecognition: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<DairyPredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [addingToFridge, setAddingToFridge] = useState<boolean>(false);
  const [selectedZoneId, setSelectedZoneId] = useState<number>(1);
  const [quantity, setQuantity] = useState<number>(1);
  const [unit, setUnit] = useState<string>('pack');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useNotification();
  const navigate = useNavigate();

  useEffect(() => {
    zonesApi.getAll().then((data) => {
      setZones(data);
      if (data.length > 0) {
        setSelectedZoneId(data[0].id);
      }
    }).catch(() => {});
  }, []);

  const handleFileSelect = (selectedFile: File) => {
    // Validate format
    const validExtensions = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validExtensions.includes(selectedFile.type)) {
      setError('Please select a valid image file (JPEG, PNG, or WebP).');
      return;
    }

    if (selectedFile.size > 15 * 1024 * 1024) {
      setError('Image file size must be less than 15MB.');
      return;
    }

    setError(null);
    setResult(null);
    setFile(selectedFile);

    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(selectedFile);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleClassify = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const data = await aiApi.predictDairy(file);
      setResult(data);
      setSelectedZoneId(data.suggested_zone_id || 1);

      if (data.needs_manual_check) {
        showToast('warning', `Uncertain identification (${Math.round(data.confidence * 100)}%). Please upload a clearer image or verify category.`);
      } else {
        if (data.confidence >= 0.70) {
          confetti({
            particleCount: 50,
            spread: 60,
            origin: { y: 0.7 }
          });
        }
        showToast('success', `Recognized packaging: ${data.display_name}`);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Image processing failed. Please try again.';
      setError(msg);
      showToast('error', msg);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAddToFridge = async () => {
    if (!result) return;
    setAddingToFridge(true);

    try {
      await foodsApi.create({
        name: result.display_name,
        category: 'Dairy',
        item_type: 'packaged',
        zone_id: selectedZoneId,
        quantity: quantity,
        unit: unit,
        expiry_date: result.suggested_expiry_date,
        freshness_status: 'Fresh',
        image_path: result.image_url,
        source: 'manual',
        estimated_cost: 0,
        notes: `Recognized via MobileNetV2 Dairy AI (${Math.round(result.confidence * 100)}% conf). ${result.storage_tips}`
      });

      showToast('success', `Added ${result.display_name} to refrigerator inventory!`);
      navigate('/foods');
    } catch (err: any) {
      showToast('error', 'Failed to save dairy item to refrigerator.');
    } finally {
      setAddingToFridge(false);
    }
  };

  const getCategoryBadgeColor = (category: string) => {
    switch (category.toLowerCase()) {
      case 'milk':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'yogurt':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'paneer':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'cheese':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
              Transfer Learning MobileNetV2
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
              500-Image Retail Dataset
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight mt-2 flex items-center gap-3">
            <Milk className="w-8 h-8 text-emerald-600" />
            Dairy Packaging Recognition
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Classifies retail photographs of packaged dairy products (Milk, Yogurt, Paneer, Cheese) and provides storage recommendations.
          </p>
        </div>

        {file && (
          <button
            onClick={handleReset}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
        )}
      </div>

      {/* Freshness Separation Notice */}
      <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200/80 flex items-start gap-3">
        <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs sm:text-sm text-amber-900 leading-relaxed">
          <strong>Category Recognition vs Freshness:</strong> This AI model identifies the dairy product <strong>packaging type</strong> from photographs (cartons, bottles, tubs, vacuum blocks). It does not grade chemical freshness or spoilage through packaging. Expiration tracking is based on manufacturer package stamps or standard shelf life defaults.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Upload & Preview Column */}
        <div className="lg:col-span-6 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs">
            <h2 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-emerald-600" />
              Upload Packaging Photo
            </h2>

            {!preview ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-200 hover:border-emerald-500 rounded-2xl p-8 text-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-emerald-50/30 flex flex-col items-center justify-center min-h-[260px]"
              >
                <div className="w-16 h-16 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-4 shadow-xs">
                  <Milk className="w-8 h-8" />
                </div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Click to upload or drag & drop packaging image
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Supports milk bottles/cartons, yogurt tubs, packaged paneer, or cheese packs (JPEG, PNG, WebP up to 15MB)
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="relative rounded-2xl overflow-hidden bg-slate-900 border border-slate-200 flex items-center justify-center max-h-[360px]">
                  <img
                    src={preview}
                    alt="Selected dairy packaging"
                    className="max-h-[360px] w-auto object-contain"
                  />
                  <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-md px-3 py-1 rounded-full text-xs text-white font-medium">
                    {file?.name}
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex-1 py-2.5 px-4 rounded-xl text-sm font-medium border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    Change Photo
                  </button>
                  <button
                    onClick={handleClassify}
                    disabled={loading}
                    className="flex-1 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors shadow-sm shadow-emerald-600/20 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Classifying...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        <span>Identify Product</span>
                      </>
                    )}
                  </button>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                />
              </div>
            )}

            {error && (
              <div className="mt-4 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                <p className="text-xs text-rose-700">{error}</p>
              </div>
            )}
          </div>
        </div>

        {/* Prediction Results Column */}
        <div className="lg:col-span-6 space-y-6">
          {result ? (
            <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-6 animate-fadeIn">
              <div className="flex items-start justify-between">
                <div>
                  <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${getCategoryBadgeColor(result.category)} uppercase tracking-wider`}>
                    {result.category}
                  </span>
                  <h3 className="text-2xl font-bold text-slate-900 mt-2">
                    {result.display_name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Verified MobileNetV2 Packaging Model
                  </p>
                </div>

                <div className="text-right">
                  <div className={`text-2xl font-black ${result.needs_manual_check ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {Math.round(result.confidence * 100)}%
                  </div>
                  <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                    Confidence
                  </div>
                </div>
              </div>

              {/* Confidence Progress Bar */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-medium text-slate-600">
                  <span>Classification Confidence</span>
                  <span>{(result.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`${result.needs_manual_check ? 'bg-amber-500' : 'bg-emerald-500'} h-2.5 rounded-full transition-all duration-500`}
                    style={{ width: `${Math.min(100, Math.round(result.confidence * 100))}%` }}
                  />
                </div>
              </div>

              {/* Low Confidence Guidance Card */}
              {result.needs_manual_check && (
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-200/80 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div className="text-xs text-amber-900 space-y-1">
                    <div className="font-semibold text-amber-950">Unable to identify confidently</div>
                    <p>
                      The model is uncertain ({(result.confidence * 100).toFixed(1)}% confidence). Please ensure good lighting and upload a clearer image with the packaging label and bottle/carton shape clearly visible, or select the category manually below.
                    </p>
                  </div>
                </div>
              )}

              {/* Class Probability Distribution */}
              {result.all_scores && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/60 space-y-3">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Category Probability Breakdown
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(result.all_scores).map(([cls, score]) => (
                      <div key={cls} className="bg-white p-2.5 rounded-lg border border-slate-200/60 text-xs">
                        <div className="flex justify-between font-medium capitalize text-slate-700">
                          <span>{cls}</span>
                          <span className="font-semibold text-slate-900">{(score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1.5 mt-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full ${cls === result.category ? 'bg-emerald-500' : 'bg-slate-300'}`}
                            style={{ width: `${Math.round(score * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommended Storage & Shelf Life */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-blue-50/60 border border-blue-100 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-semibold text-blue-700 uppercase tracking-wider">
                    <Layers className="w-4 h-4" />
                    Recommended Zone
                  </div>
                  <div className="text-base font-bold text-slate-900">
                    {result.suggested_shelf}
                  </div>
                  <div className="text-xs text-slate-500">
                    Target compartment for dairy
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-purple-50/60 border border-purple-100 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-semibold text-purple-700 uppercase tracking-wider">
                    <Calendar className="w-4 h-4" />
                    Default Shelf Life
                  </div>
                  <div className="text-base font-bold text-slate-900">
                    {result.typical_shelf_life_days} Days
                  </div>
                  <div className="text-xs text-slate-500">
                    Expires ~{new Date(result.suggested_expiry_date).toLocaleDateString()}
                  </div>
                </div>
              </div>

              {/* Storage Tip */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 space-y-1">
                <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Preservation Guideline
                </div>
                <p>{result.storage_tips}</p>
              </div>

              {/* Save to Inventory Section */}
              <div className="pt-4 border-t border-slate-100 space-y-4">
                <h4 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <PlusCircle className="w-4 h-4 text-emerald-600" />
                  Add to Refrigerator Inventory
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Compartment
                    </label>
                    <select
                      value={selectedZoneId}
                      onChange={(e) => setSelectedZoneId(Number(e.target.value))}
                      className="w-full text-xs rounded-xl border border-slate-200 px-3 py-2 bg-white focus:outline-emerald-500"
                    >
                      {zones.map((z) => (
                        <option key={z.id} value={z.id}>
                          {z.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Quantity
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={quantity}
                      onChange={(e) => setQuantity(Number(e.target.value))}
                      className="w-full text-xs rounded-xl border border-slate-200 px-3 py-2 bg-white focus:outline-emerald-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Unit
                    </label>
                    <select
                      value={unit}
                      onChange={(e) => setUnit(e.target.value)}
                      className="w-full text-xs rounded-xl border border-slate-200 px-3 py-2 bg-white focus:outline-emerald-500"
                    >
                      <option value="pack">pack</option>
                      <option value="bottle">bottle</option>
                      <option value="carton">carton</option>
                      <option value="cup">cup</option>
                      <option value="block">block</option>
                      <option value="pcs">pcs</option>
                    </select>
                  </div>
                </div>

                <button
                  onClick={handleAddToFridge}
                  disabled={addingToFridge}
                  className="w-full py-3 rounded-xl font-semibold text-sm bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors shadow-sm shadow-emerald-600/20 flex items-center justify-center gap-2"
                >
                  <PackageCheck className="w-5 h-5" />
                  {addingToFridge ? 'Saving...' : 'Add Product to Fridge'}
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200/80 p-8 shadow-xs flex flex-col items-center justify-center text-center min-h-[380px] space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center">
                <Sparkles className="w-8 h-8" />
              </div>
              <h3 className="text-base font-semibold text-slate-800">
                Awaiting Product Image
              </h3>
              <p className="text-xs text-slate-500 max-w-sm">
                Upload or drop a dairy product image on the left, then click <strong>Identify Product</strong> to analyze the packaging using MobileNetV2.
              </p>
              <div className="pt-4 border-t border-slate-100 w-full max-w-xs grid grid-cols-2 gap-2 text-left text-xs text-slate-600">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  Milk Cartons / Bottles
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-purple-500" />
                  Yogurt / Curd Tubs
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-amber-500" />
                  Packaged Paneer Blocks
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
                  Cheese Slices / Packs
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
