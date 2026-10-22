'use client';

import { type ReactNode, createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { BrowserAvatar } from '@/lib/browser-avatar';

type Mode = 'voice' | 'avatar';
interface AvatarState {
  mode: Mode;
  setMode: (mode: Mode) => void;
  availability: 'offline' | 'available';
  assets: BrowserAvatar[];
  availableCharacters: BrowserAvatar['character'][];
  activate: (assets: BrowserAvatar[]) => void;
  release: () => void;
  ready: boolean;
  markReady: () => void;
  resetPlayback: () => void;
  failed: boolean;
  fail: () => void;
}
const AvatarContext = createContext<AvatarState | null>(null);
// Name retained for existing callers; this loads local WebGL assets, not video.
export function AvatarStreamProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>('voice');
  const [availability, setAvailability] = useState<AvatarState['availability']>('offline');
  const [assets, setAssets] = useState<BrowserAvatar[]>([]);
  const [availableCharacters, setAvailableCharacters] = useState<BrowserAvatar['character'][]>([]);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const activate = useCallback((value: BrowserAvatar[]) => {
    setAssets(value);
    setReady(false);
    setFailed(false);
  }, []);
  const release = useCallback(() => {
    setAssets([]);
    setReady(false);
    setFailed(false);
  }, []);
  const fail = useCallback(() => {
    setReady(false);
    setFailed(true);
  }, []);
  const markReady = useCallback(() => setReady(true), []);
  const resetPlayback = useCallback(() => {
    setReady(false);
    setFailed(false);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/avatar', { cache: 'no-store', signal: controller.signal })
      .then((r) => r.json())
      .then((data) => {
        if (!controller.signal.aborted) {
          setAvailability(data.availability === 'available' ? 'available' : 'offline');
          setAvailableCharacters((data.assets || []).map((item: BrowserAvatar) => item.character));
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setAvailability('offline');
      });
    return () => controller.abort();
  }, [mode]);
  return (
    <AvatarContext.Provider
      value={{
        mode,
        setMode,
        availability,
        assets,
        availableCharacters,
        activate,
        release,
        ready,
        markReady,
        resetPlayback,
        failed,
        fail,
      }}
    >
      {children}
    </AvatarContext.Provider>
  );
}
export function useAvatarStream() {
  const value = useContext(AvatarContext);
  if (!value) throw new Error('Missing AvatarStreamProvider');
  return value;
}
