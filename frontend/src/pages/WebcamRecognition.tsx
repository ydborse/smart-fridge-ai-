
import { useEffect, useRef, useState } from 'react';
import {
  Camera,
  CheckCircle2,
  CircleAlert,
  LoaderCircle,
  RefreshCw,
  ScanSearch,
  Video,
  VideoOff,
} from 'lucide-react';
import { aiApi } from '../services/api';
import type { PredictionResponse } from '../types';

export default function WebcamRecognition() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [cameraActive, setCameraActive] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraActive(false);
  }

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    return () => {
      if (capturedImage) {
        URL.revokeObjectURL(capturedImage);
      }
    };
  }, [capturedImage]);

  async function startCamera() {
    setError(null);
    setPrediction(null);

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          'Camera access is unavailable. Open the app on localhost or through HTTPS.',
        );
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;

      if (!videoRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        throw new Error('The camera preview could not be initialized.');
      }

      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      setCameraActive(true);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Unable to open your camera.';
      setError(
        message.includes('Permission') || message.includes('NotAllowed')
          ? 'Camera permission was denied. Allow camera access in your browser settings and try again.'
          : message,
      );
    }
  }

  function captureImage() {
    const video = videoRef.current;

    if (!video || !video.videoWidth || !video.videoHeight) {
      setError('Wait until the camera preview is ready, then capture again.');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');

    if (!context) {
      setError('Could not capture the image. Please try again.');
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError('Could not create an image from the camera.');
          return;
        }

        const file = new File([blob], `webcam-${Date.now()}.jpg`, {
          type: 'image/jpeg',
        });

        setCapturedFile(file);
        setCapturedImage(URL.createObjectURL(blob));
        setPrediction(null);
        setError(null);
        stopCamera();
      },
      'image/jpeg',
      0.92,
    );
  }

  function retakePhoto() {
    setCapturedImage(null);
    setCapturedFile(null);
    setPrediction(null);
    setError(null);
  }

  async function analyzeImage() {
    if (!capturedFile) {
      setError('Capture an image before running the analysis.');
      return;
    }

    setLoading(true);
    setError(null);
    setPrediction(null);

    try {
      const result = await aiApi.predictFreshness(capturedFile);
      setPrediction(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Prediction failed. Check that the backend is running and you are logged in.',
      );
    } finally {
      setLoading(false);
    }
  }

  const result = prediction?.top_prediction;

  const percentage = (value?: number) =>
    typeof value === 'number' ? `${Math.round(value * 100)}%` : '—';

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 md:p-8">
      <header>
        <div className="flex items-center gap-2 text-emerald-700">
          <Camera className="h-5 w-5" />
          <span className="text-sm font-semibold uppercase tracking-wide">
            AI food recognition
          </span>
        </div>

        <h1 className="mt-2 text-2xl font-bold text-slate-900 md:text-3xl">
          Webcam Recognition
        </h1>

        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          Capture a fruit or vegetable and analyze it using your existing Smart
          Fridge AI prediction service.
        </p>
      </header>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 p-4">
          <div>
            <h2 className="font-semibold text-slate-900">Camera preview</h2>
            <p className="mt-1 text-xs text-slate-500">
              Place one item in view with good lighting.
            </p>
          </div>

          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              cameraActive
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-slate-100 text-slate-600'
            }`}
          >
            {cameraActive ? 'Camera on' : 'Camera off'}
          </span>
        </div>

        <div className="relative aspect-video min-h-64 overflow-hidden bg-slate-950">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`absolute inset-0 h-full w-full object-contain ${
              capturedImage ? 'hidden' : ''
            }`}
          />

          {capturedImage && (
            <img
              src={capturedImage}
              alt="Captured food for AI analysis"
              className="absolute inset-0 h-full w-full object-contain"
            />
          )}

          {!cameraActive && !capturedImage && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center text-white">
              <VideoOff className="h-12 w-12 text-slate-400" />
              <p className="font-medium">Camera preview is not active</p>
              <p className="text-sm text-slate-400">
                Start the camera when you're ready to capture an item.
              </p>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-3 p-4">
          {!cameraActive && !capturedImage && (
            <button
              type="button"
              onClick={startCamera}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              <Video className="h-4 w-4" />
              Start camera
            </button>
          )}

          {cameraActive && (
            <>
              <button
                type="button"
                onClick={captureImage}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-700"
              >
                <Camera className="h-4 w-4" />
                Capture image
              </button>

              <button
                type="button"
                onClick={stopCamera}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Stop camera
              </button>
            </>
          )}

          {capturedImage && (
            <>
              <button
                type="button"
                onClick={analyzeImage}
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <ScanSearch className="h-4 w-4" />
                )}
                {loading ? 'Analyzing image…' : 'Analyze with AI'}
              </button>

              <button
                type="button"
                onClick={retakePhoto}
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                <RefreshCw className="h-4 w-4" />
                Retake
              </button>
            </>
          )}
        </div>
      </section>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          <CircleAlert className="mt-0.5 h-5 w-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {prediction && result && (
        <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <h2 className="text-lg font-bold text-slate-900">Prediction result</h2>
          </div>

          {prediction.is_demo_mode && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              The backend reports demo mode. Verify that the trained food model
              loaded successfully before relying on predictions.
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl bg-emerald-50 p-4">
              <p className="text-sm text-emerald-800">Predicted food</p>
              <p className="mt-1 text-xl font-bold capitalize text-emerald-950">
                {result.item_name.replaceAll('_', ' ')}
              </p>
              <p className="mt-2 text-sm text-emerald-800">
                Food confidence: {percentage(result.confidence)}
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-sm text-slate-600">Freshness status</p>
              <p className="mt-1 text-xl font-bold text-slate-900">
                {result.freshness_class}
              </p>
              {typeof result.freshness_confidence === 'number' && (
                <p className="mt-2 text-sm text-slate-600">
                  Freshness confidence: {percentage(result.freshness_confidence)}
                </p>
              )}
            </div>

            <div className="rounded-xl border border-slate-100 p-4">
              <p className="text-sm text-slate-500">Suggested storage zone</p>
              <p className="mt-1 font-semibold text-slate-900">
                {result.suggested_zone_name || 'Not available'}
              </p>
            </div>

            <div className="rounded-xl border border-slate-100 p-4">
              <p className="text-sm text-slate-500">Typical shelf life</p>
              <p className="mt-1 font-semibold text-slate-900">
                {result.typical_shelf_life_days} day(s)
              </p>
            </div>
          </div>

          {result.condition_notes && (
            <div className="rounded-xl border border-slate-200 p-4">
              <h3 className="font-semibold text-slate-900">Condition notes</h3>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                {result.condition_notes}
              </p>
            </div>
          )}

          {result.needs_manual_check && (
            <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
              Manual verification is recommended for this image.
            </p>
          )}

          <p className="text-xs leading-5 text-slate-500">
            {prediction.disclaimer}
          </p>
        </section>
      )}
    </main>
  );
}
