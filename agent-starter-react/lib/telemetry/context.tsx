'use client';

import { createContext, useContext } from 'react';
import type { MediaTelemetry } from './client';

export const MediaTelemetryContext = createContext<MediaTelemetry | null>(null);
export const useMediaTelemetry = () => useContext(MediaTelemetryContext);
