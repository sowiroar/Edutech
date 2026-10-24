'use client';

import { type RefObject, useCallback, useEffect, useRef, useState } from 'react';
import { type PreviewAudioMeasurement, createPreviewAudio } from './preview-audio';
import { type MouthPose, REST_MOUTH, type SpeechMotionStyle } from './speech-motion';

export function PreviewAudioControls({
  speech,
  sampleAvailable,
  onMeasurement,
}: {
  speech: RefObject<() => MouthPose>;
  sampleAvailable: boolean;
  onMeasurement: (value: PreviewAudioMeasurement | null) => void;
}) {
  const file = useRef<File | null>(null);
  const player = useRef<ReturnType<typeof createPreviewAudio> | null>(null);
  const generation = useRef(0);
  const [style, setStyle] = useState<SpeechMotionStyle>('smooth');
  const [selected, setSelected] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [status, setStatus] = useState('Elige un audio para comprobar labios y pausas.');
  const [metrics, setMetrics] = useState<ReturnType<
    ReturnType<typeof createPreviewAudio>['snapshot']
  > | null>(null);
  const report = (value: PreviewAudioMeasurement | null) => {
    setMetrics(value);
    onMeasurement(value);
  };
  const stop = useCallback(() => {
    generation.current++;
    player.current?.dispose();
    player.current = null;
    speech.current = () => REST_MOUTH;
  }, [speech]);
  useEffect(() => () => stop(), [stop]);
  const play = async () => {
    stop();
    if (!file.current) return;
    const id = generation.current;
    setPlaying(true);
    report(null);
    setStatus('Preparando audio…');
    try {
      const current = createPreviewAudio(
        file.current,
        () => {
          if (id !== generation.current) return;
          report(current.snapshot());
          stop();
          setPlaying(false);
          setStatus('Audio terminado; boca en reposo.');
        },
        () => {
          if (id !== generation.current) return;
          stop();
          setPlaying(false);
          setStatus('No se pudo reproducir este archivo.');
        },
        style
      );
      player.current = current;
      speech.current = current.read;
      await current.play();
      if (id === generation.current)
        setStatus(
          style === 'smooth'
            ? 'Reproduciendo con suavizado sutil de labios.'
            : 'Reproduciendo la referencia original de Santiago.'
        );
    } catch {
      if (id !== generation.current) return;
      stop();
      setPlaying(false);
      setStatus('No se pudo iniciar el audio. Elige otro archivo o vuelve a intentar.');
    }
  };
  return (
    <section
      aria-label="Prueba de labios con audio"
      className="w-full space-y-3 rounded border p-4"
    >
      <h2 className="font-semibold">Probar con audio</h2>
      <p className="text-sm">
        Usa una frase de prueba sin datos personales. Se reproduce solo aquí; no se sube, no se
        guarda y no activa el micrófono.
      </p>
      <label className="grid gap-2 text-sm">
        Movimiento de labios
        <select
          value={style}
          className="bg-background rounded border p-2"
          onChange={(event) => {
            stop();
            setPlaying(false);
            report(null);
            setStyle(event.target.value as SpeechMotionStyle);
            setStatus('Método cambiado. Reproduce la misma frase para comparar.');
          }}
        >
          <option value="smooth">Suavizado sutil</option>
          <option value="santiago">Referencia de Santiago</option>
        </select>
      </label>
      <label className="grid gap-2 text-sm">
        Audio de prueba
        <input
          type="file"
          accept="audio/*"
          onChange={(event) => {
            stop();
            setPlaying(false);
            report(null);
            file.current = event.target.files?.[0] ?? null;
            setSelected(!!file.current);
            setStatus(file.current ? 'Audio preparado.' : 'Elige un audio de prueba.');
          }}
        />
      </label>
      {sampleAvailable && (
        <button
          className="rounded border px-4 py-2"
          onClick={async () => {
            stop();
            setPlaying(false);
            report(null);
            setSelected(false);
            file.current = null;
            const id = generation.current;
            try {
              const response = await fetch('/avatars/articulation-sample.wav');
              if (!response.ok) throw new Error('Missing fixture');
              const blob = await response.blob();
              if (id !== generation.current) return;
              file.current = new File([blob], 'ejemplo-sintetico.wav', { type: 'audio/wav' });
              setSelected(true);
              setStatus('Ejemplo sintético en español preparado.');
            } catch {
              if (id === generation.current) setStatus('No se encuentra el ejemplo local.');
            }
          }}
        >
          Cargar ejemplo sintético local
        </button>
      )}
      <div className="flex gap-3">
        <button
          className="rounded border px-4 py-2 disabled:opacity-40"
          disabled={!selected || playing}
          onClick={() => void play()}
        >
          Reproducir audio
        </button>
        <button
          className="rounded border px-4 py-2 disabled:opacity-40"
          disabled={!playing}
          onClick={() => {
            report(player.current?.snapshot() ?? null);
            stop();
            setPlaying(false);
            setStatus('Detenido; boca en reposo.');
          }}
        >
          Detener audio
        </button>
      </div>
      <p role="status" className="text-sm">
        {status}
      </p>
      {metrics && (
        <p className="text-sm">
          Pausas observadas: {metrics.close_observations}. Máximo desde silencio detectado hasta
          pose de reposo:{' '}
          {metrics.silence_to_rest_max_ms === null
            ? 'sin dato'
            : `${Math.round(metrics.silence_to_rest_max_ms)} ms`}
          . Mide respuesta acústica; no correspondencia de fonemas ni retardo del altavoz.
        </p>
      )}
    </section>
  );
}
