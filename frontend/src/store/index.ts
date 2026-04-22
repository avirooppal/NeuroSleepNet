import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ── Auth Store ─────────────────────────────────────────────────────────────────

interface AuthState {
  token: string | null;
  user: { id: string; email: string; name: string } | null;
  apiKey: string | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  setUser: (user: AuthState['user']) => void;
  setApiKey: (key: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      apiKey: null,
      isAuthenticated: false,
      setToken: (token) => set({ token, isAuthenticated: true }),
      setUser: (user) => set({ user }),
      setApiKey: (key) => set({ apiKey: key }),
      logout: () => set({ token: null, user: null, apiKey: null, isAuthenticated: false }),
    }),
    { name: 'nsn-auth' }
  )
);

// ── Onboarding Store ───────────────────────────────────────────────────────────

interface OnboardingState {
  step: 0 | 1 | 2 | 3;      // 0 = not started, 1-3 = wizard steps
  completed: boolean;
  apiKeyCopied: boolean;
  sdkInstalled: boolean;
  roundTripVerified: boolean;
  setStep: (step: OnboardingState['step']) => void;
  setApiKeyCopied: (v: boolean) => void;
  setSdkInstalled: (v: boolean) => void;
  setRoundTripVerified: (v: boolean) => void;
  complete: () => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      step: 0,
      completed: false,
      apiKeyCopied: false,
      sdkInstalled: false,
      roundTripVerified: false,
      setStep: (step) => set({ step }),
      setApiKeyCopied: (v) => set({ apiKeyCopied: v }),
      setSdkInstalled: (v) => set({ sdkInstalled: v }),
      setRoundTripVerified: (v) => set({ roundTripVerified: v }),
      complete: () => set({ completed: true, step: 3 }),
    }),
    { name: 'nsn-onboarding' }
  )
);

// ── Preferences Store ──────────────────────────────────────────────────────────

interface PreferencesState {
  activeProject: string | null;
  attentionWeights: { w1: number; w2: number; w3: number; w4: number };
  piiDetection: boolean;
  memoryTtlDays: number | null;
  setActiveProject: (id: string) => void;
  setAttentionWeights: (w: PreferencesState['attentionWeights']) => void;
  setPiiDetection: (v: boolean) => void;
  setMemoryTtlDays: (days: number | null) => void;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      activeProject: null,
      attentionWeights: { w1: 0.50, w2: 0.20, w3: 0.20, w4: 0.10 },
      piiDetection: true,
      memoryTtlDays: null,
      setActiveProject: (id) => set({ activeProject: id }),
      setAttentionWeights: (w) => set({ attentionWeights: w }),
      setPiiDetection: (v) => set({ piiDetection: v }),
      setMemoryTtlDays: (days) => set({ memoryTtlDays: days }),
    }),
    { name: 'nsn-preferences' }
  )
);
