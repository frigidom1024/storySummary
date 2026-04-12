import { ref, computed, watch } from 'vue'

export type PageState = 'idle' | 'loading' | 'analyzing' | 'completed' | 'failed'
export type ViewMode = 'graph' | 'timeline'

export interface PageStateContext {
  state: PageState
  viewMode: ViewMode
  error: string | null
  progress: number
  progressMessage: string
  nodeCount: number
}

export function createPageStateMachine() {
  const state = ref<PageState>('idle')
  const viewMode = ref<ViewMode>('graph')
  const error = ref<string | null>(null)
  const progress = ref(0)
  const progressMessage = ref('')

  const isLoading = computed(() => state.value === 'loading')
  const isAnalyzing = computed(() => state.value === 'analyzing')
  const isCompleted = computed(() => state.value === 'completed')
  const isFailed = computed(() => state.value === 'failed')
  const isIdle = computed(() => state.value === 'idle')

  function setLoading() {
    state.value = 'loading'
    error.value = null
    progress.value = 0
    progressMessage.value = ''
  }

  function startAnalyze(message = '准备启动...') {
    state.value = 'analyzing'
    error.value = null
    progress.value = 0
    progressMessage.value = message
  }

  function updateProgress(p: number, message: string) {
    progress.value = p
    progressMessage.value = message
  }

  function complete() {
    state.value = 'completed'
    progress.value = 100
    progressMessage.value = '解析完成'
    viewMode.value = 'graph'
  }

  function fail(err: string) {
    state.value = 'failed'
    error.value = err
  }

  function reset() {
    state.value = 'idle'
    error.value = null
    progress.value = 0
    progressMessage.value = ''
    viewMode.value = 'graph'
  }

  function setViewMode(mode: ViewMode) {
    viewMode.value = mode
  }

  function clearError() {
    error.value = null
  }

  return {
    state,
    viewMode,
    error,
    progress,
    progressMessage,
    isLoading,
    isAnalyzing,
    isCompleted,
    isFailed,
    isIdle,
    setLoading,
    startAnalyze,
    updateProgress,
    complete,
    fail,
    reset,
    setViewMode,
    clearError,
  }
}

export type PageStateMachine = ReturnType<typeof createPageStateMachine>
