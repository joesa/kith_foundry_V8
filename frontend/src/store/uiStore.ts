import { create } from 'zustand';

export type ToastVariant = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration?: number;
}

interface UiState {
  sidebarOpen: boolean;
  commandPaletteOpen: boolean;
  theme: 'dark' | 'light';
  toasts: Toast[];
  hideSidebarDuringBuild: boolean;
  activeProjectIdBeingBuilt: string | null;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleTheme: () => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  setHideSidebarDuringBuild: (hide: boolean) => void;
  setActiveProjectIdBeingBuilt: (projectId: string | null) => void;
}

// Helper to initialize theme from localStorage or system preference
const getInitialTheme = (): 'dark' | 'light' => {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem('forge-theme');
    if (stored === 'light' || stored === 'dark') return stored;
    
    // Default to dark per Kinetic Monolith design, but respect system if needed
    // Actually our requested default behavior is dark
    return 'dark';
  }
  return 'dark';
};

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true, // Will be managed for responsive
  commandPaletteOpen: false,
  theme: getInitialTheme(),
  toasts: [],
  hideSidebarDuringBuild: false,
  activeProjectIdBeingBuilt: null,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setHideSidebarDuringBuild: (hide) => set({ hideSidebarDuringBuild: hide }),
  setActiveProjectIdBeingBuilt: (projectId) => set({ activeProjectIdBeingBuilt: projectId }),
  toggleTheme: () => set((state) => {
    const newTheme = state.theme === 'dark' ? 'light' : 'dark';
    if (typeof window !== 'undefined') {
      localStorage.setItem('forge-theme', newTheme);
    }
    return { theme: newTheme };
  }),
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2, 9);
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }));
  },
  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter(t => t.id !== id) }));
  }
}));
