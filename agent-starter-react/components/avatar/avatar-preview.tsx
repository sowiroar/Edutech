'use client';

import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { type BrowserAvatar, WEB_CHARACTERS } from '@/lib/browser-avatar';
import type { AvatarSample } from './browser-avatar-stage';
import type { PreviewAudioMeasurement } from './preview-audio';
import { PreviewAudioControls } from './preview-audio-controls';
import { type MouthPose, REST_MOUTH } from './speech-motion';

const Stage = dynamic(() => import('./browser-avatar-stage'), { ssr: false });

export default function AvatarPreview({
  assets,
  character: initialCharacter,
  sampleAvailable = false,
}: {
  assets: BrowserAvatar[];
  character: BrowserAvatar['character'];
  sampleAvailable?: boolean;
}) {
  const [character, setCharacter] = useState(initialCharacter);
  const asset = assets.find((item) => item.character === character) ?? null;
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [sample, setSample] = useState<AvatarSample | null>(null);
  const samples = useRef<AvatarSample[]>([]);
  const audioMeasurement = useRef<PreviewAudioMeasurement | null>(null);
  const speech = useRef<() => MouthPose>(() => REST_MOUTH);
  const [testingMouth, setTestingMouth] = useState(false);
  useEffect(() => {
    const start = performance.now();
    speech.current = testingMouth
      ? () => {
          const phase = Math.floor((performance.now() - start) / 1200) % 4;
          return [
            REST_MOUTH,
            { open: 0.65, round: 0, wide: 0 },
            { open: 0.35, round: 0.9, wide: 0 },
            { open: 0.35, round: 0, wide: 0.9 },
          ][phase];
        }
      : () => REST_MOUTH;
  }, [testingMouth]);
  const download = () => {
    const report = {
      capturedAt: new Date().toISOString(),
      scope: 'browser-preview',
      acousticMeasurement: audioMeasurement.current,
      acousticScope: 'local-file-preview-not-live-call',
      modelHash: asset?.sha256,
      samples: samples.current,
      note: 'JS heap belongs to the whole page, not total RAM. Submission time is not GPU time. No audio or conversations captured.',
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = `${character.toLowerCase()}-browser-measurement.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <main className="mx-auto flex min-h-svh max-w-5xl flex-col items-center justify-center gap-5 p-6">
      <h1 className="text-2xl font-semibold">Vista previa de {character}</h1>
      <p>Esta vista no inicia una llamada ni activa el micrófono.</p>
      <label className="flex flex-wrap items-center justify-center gap-3 text-sm">
        Personaje
        <select
          className="bg-background rounded border px-3 py-2"
          value={character}
          onChange={(event) => {
            setCharacter(event.target.value as BrowserAvatar['character']);
            setReady(false);
            setFailed(false);
            setSample(null);
            samples.current = [];
            audioMeasurement.current = null;
            speech.current = () => REST_MOUTH;
            setTestingMouth(false);
          }}
        >
          {WEB_CHARACTERS.map((name) => (
            <option key={name} value={name}>
              {name}
              {assets.some((item) => item.character === name) ? '' : ' — pendiente de GLB'}
            </option>
          ))}
        </select>
      </label>
      {!asset ? (
        <p role="status">El modelo de {character} aún no se ha exportado para la web.</p>
      ) : failed ? (
        <p role="alert">
          No se pudo mostrar el modelo en este navegador. La conversación por voz sigue disponible.
        </p>
      ) : (
        <Stage
          asset={asset}
          speech={speech}
          onReady={() => setReady(true)}
          onFailure={() => setFailed(true)}
          onSample={(value) => {
            setSample(value);
            samples.current.push(value);
            if (samples.current.length > 120) samples.current.shift();
          }}
        />
      )}
      {asset && !ready && !failed && <p role="status">Cargando modelo…</p>}
      {sample && (
        <div className="space-y-2 text-center text-sm">
          <p>
            {sample.fps.toFixed(1)} FPS · {(sample.modelBytes / 1048576).toFixed(1)} MiB de modelo ·{' '}
            {sample.triangles.toLocaleString()} triángulos
          </p>
          <p>
            Texturas estimadas: {(sample.textureBytesEstimate / 1048576).toFixed(1)} MiB ·
            geometría: {(sample.geometryDataBytes / 1048576).toFixed(1)} MiB. No mide la VRAM total.
          </p>
          <p>
            Memoria JavaScript de la página:{' '}
            {sample.pageJsHeapBytes === null
              ? 'no disponible'
              : `${(sample.pageJsHeapBytes / 1048576).toFixed(1)} MiB`}
            . No equivale a RAM total ni VRAM.
          </p>
          <button className="rounded border px-4 py-2" onClick={download}>
            Guardar medición de la vista previa
          </button>
          {sample.mouthAnimationAvailable && (
            <button
              className="ml-2 rounded border px-4 py-2"
              onClick={() => {
                setTestingMouth((active) => !active);
              }}
            >
              {testingMouth ? 'Detener prueba de boca' : 'Probar movimientos de labios'}
            </button>
          )}
          {testingMouth && <p>Movimiento de prueba, sin audio. No valida sincronización labial.</p>}
        </div>
      )}
      {ready && !failed && !testingMouth && (
        <PreviewAudioControls
          key={character}
          speech={speech}
          sampleAvailable={sampleAvailable}
          onMeasurement={(value) => {
            audioMeasurement.current = value;
          }}
        />
      )}
      <Link href="/" className="underline">
        Volver a la conversación
      </Link>
    </main>
  );
}
