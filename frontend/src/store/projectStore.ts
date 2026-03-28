import { create } from 'zustand';

interface Project {
  id: string;
  name: string;
  status: string;
  stage: string;
}

interface ProjectState {
  currentProject: Project | null;
  selectedArtifactId: string | null;
  selectedFileId: string | null;
  activeLifecycleStage: string;
  isLoading: boolean;
  setCurrentProject: (project: Project | null) => void;
  setSelectedArtifactId: (id: string | null) => void;
  setSelectedFileId: (id: string | null) => void;
  setActiveLifecycleStage: (stage: string) => void;
  setIsLoading: (loading: boolean) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  currentProject: null,
  selectedArtifactId: null,
  selectedFileId: null,
  activeLifecycleStage: 'idea',
  isLoading: false,
  setCurrentProject: (project) => set({ currentProject: project }),
  setSelectedArtifactId: (id) => set({ selectedArtifactId: id }),
  setSelectedFileId: (id) => set({ selectedFileId: id }),
  setActiveLifecycleStage: (stage) => set({ activeLifecycleStage: stage }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
