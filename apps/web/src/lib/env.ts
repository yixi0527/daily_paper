export const appMode = import.meta.env.VITE_APP_MODE ?? 'live';
export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';
export const staticDataBase = import.meta.env.VITE_STATIC_DATA_BASE ?? '/data';

export const isStaticMode = appMode === 'static';

